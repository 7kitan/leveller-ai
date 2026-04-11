from sqlalchemy.orm import Session, joinedload
from shared.models import UserSkillProfile, JobSkillRequirement, Job, Skill, UserCV, Course, UserWorkExperience
from shared.database import SessionLocal
from shared.neo4j_client import neo4j_client
from shared.level_mapper import LevelMapper
from shared.taxonomy_service import taxonomy_service
from .recommender import CourseRecommender
from sqlalchemy import text
import numpy as np
import json
import os
import uuid
import logging
import re
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

# Cấu hình logging
logger = logging.getLogger("gap_calculator")

from shared.llm_utils import get_embedding, openai_client, LLM_PROVIDER, LLM_MODEL

class GapCalculator:
    def __init__(self, db: Session):
        self.db = db
        self.recommender = CourseRecommender(db)

    def _normalize_name(self, name: str) -> str:
        """Chuẩn hóa tên skill để so khớp chính xác hơn."""
        if not name: return ""
        n = name.lower().strip()
        n = re.sub(r'(\.js|js|programming|language|coding|stack|framework)$', '', n)
        n = re.sub(r'[^a-z0-9#+]', '', n)
        return n

    def _detect_user_role(self, cv_id: str) -> Optional[str]:
        """Xác định vai trò chuyên môn của ứng viên từ Graph (Neo4j)."""
        try:
            cv = self.db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
            if not cv or not cv.summary: return None
            
            summary = cv.summary.lower()
            pos_list = neo4j_client.get_positions()
            
            if not pos_list:
                return None

            for pos_name in pos_list:
                if pos_name.lower() in summary: return pos_name
            
            user_pos_skill = self.db.query(Skill.name).join(UserSkillProfile).filter(
                UserSkillProfile.cv_id == uuid.UUID(cv_id), Skill.name.in_(pos_list)
            ).first()
            
            if user_pos_skill: return user_pos_skill.name
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error detecting user role via graph: {e}")
            return None

    def _get_text_embedding(self, text_input: str) -> List[float]:
        """Tạo vector embedding cho văn bản sử dụng OpenAI."""
        try:
            response = openai_client.embeddings.create(input=text_input, model="text-embedding-3-small")
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def _find_keyword_cache(self, jd_text: str) -> Optional[List[Dict[str, Any]]]:
        """Layer 2: Tìm kiếm JD tương đồng 95%+ bằng Keyword (Postgres Full-text Search)."""
        if len(jd_text) < 50: return None
        try:
            # Sử dụng ts_rank_cd để đo độ tương đồng văn bản thuần túy
            query = text("""
                SELECT source_id, extracted_requirements_json, 
                       ts_rank_cd(to_tsvector('english', raw_text), plainto_tsquery('english', :text)) as rank
                FROM jobs
                WHERE to_tsvector('english', raw_text) @@ plainto_tsquery('english', :text)
                  AND extracted_requirements_json IS NOT NULL
                ORDER BY rank DESC
                LIMIT 1
            """)
            result = self.db.execute(query, {"text": jd_text}).first()
            
            if result and result.rank > 0.5: # Ngưỡng tin cậy cho keyword match
                logger.info(f"KEYWORD CACHE HIT: Matched via full-text search with rank {round(result.rank, 3)}")
                return result.extracted_requirements_json
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error checking keyword cache: {e}")
            return None

    def _find_semantic_cache(self, jd_text: str, embedding: List[float]) -> Optional[List[Dict[str, Any]]]:
        """Layer 3: Tìm kiếm JD tương đồng trong Cache (PGVector) với LOGGING CHI TIẾT."""
        if not embedding: return None
        try:
            query = text("""
                SELECT source_id, raw_text, extracted_requirements_json, 1 - (vector <=> :vec::vector) as similarity
                FROM jobs
                WHERE vector IS NOT NULL 
                ORDER BY similarity DESC
                LIMIT 5
            """)
            results = self.db.execute(query, {"vec": embedding}).all()
            
            if not results:
                logger.info("CACHE DEBUG: No vector jobs found.")
                return None

            best_match = None
            for idx, res in enumerate(results):
                if idx == 0 and res.similarity > 0.97 and res.extracted_requirements_json:
                    best_match = res.extracted_requirements_json
                    logger.info(f"CACHE HIT: Linked to {res.source_id} ({round(res.similarity*100, 2)}%).")
            
            return best_match
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error checking semantic cache: {e}")
            return None

    def _save_to_cache(self, jd_text: str, embedding: List[float], requirements: List[Dict[str, Any]]):
        """Lưu kết quả bóc tách vào Cache (Bảng Job) với Persistence nâng cao."""
        # SỬA: Cho phép lưu cả danh sách rỗng để tránh loop LLM khi JD không hợp lệ
        if requirements is None: return 
        
        try:
            text_hash = hashlib.sha256(jd_text.encode()).hexdigest()[:16]
            source_id = f"cache_{text_hash}"
            
            existing = self.db.query(Job).filter(Job.source_id == source_id).first()
            
            if existing:
                existing.extracted_requirements_json = requirements
                existing.last_analyzed_at = datetime.now()
                if embedding: existing.vector = embedding
                logger.info(f"Updating existing job cache: {source_id}")
            else:
                new_job = Job(
                    id=uuid.uuid4(),
                    source_id=source_id,
                    title_raw="Cached Analysis",
                    raw_text=jd_text,
                    vector=embedding,
                    extracted_requirements_json=requirements,
                    last_analyzed_at=datetime.now(),
                    status="cache"
                )
                self.db.add(new_job)
                logger.info(f"Creating new job cache record: {source_id}")
            
            self.db.commit()
            self.db.flush()
            logger.info(f"CACHE PERSISTED: source_id={source_id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"CRITICAL CACHE ERROR: Failed to save to DB: {e}")

    def _normalize_terms_in_text(self, text_input: str) -> str:
        """Sử dụng Graph Taxonomy để chuẩn hóa thuật ngữ trước khi xử lý (JD/CV)."""
        if not text_input: return ""
        mapping = taxonomy_service.get_canonical_mapping()
        if not mapping: return text_input
        
        normalized = text_input
        sorted_aliases = sorted(mapping.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            canonical = mapping[alias]
            pattern = re.compile(re.escape(alias), re.IGNORECASE)
            normalized = pattern.sub(f"{alias} [{canonical}]", normalized)
        return normalized

    async def extract_requirements_from_text(self, jd_text: str) -> List[Dict[str, Any]]:
        """AI Trích xuất JD với cơ chế 4-Layer Knowledge Retrieval (Hybrid)."""
        logger.info("-" * 20 + " HYBRID RETRIEVAL START " + "-" * 20)
        
        # CHUẨN HÓA TRƯỚC: Tránh việc dư khoảng trắng làm sai lệch Hash
        jd_text = jd_text.strip()
        
        # Layer 1: Exact Hit (Hash-based) - SIÊU NHANH, 0 API
        text_hash = hashlib.sha256(jd_text.encode()).hexdigest()[:16]
        exact_id = f"cache_{text_hash}"
        
        # SỬA: Dùng explicit check cho SQL
        query = self.db.query(Job).filter(Job.source_id == exact_id)
        exact_hit = query.first()
        
        if exact_hit and exact_hit.extracted_requirements_json:
            logger.info(f"LAYER 1 HIT: Exact hash match {text_hash}")
            return exact_hit.extracted_requirements_json

        # Layer 2: Keyword Hit (Postgres FTS) - NHANH, 0 API
        keyword_hit = self._find_keyword_cache(jd_text)
        if keyword_hit:
            logger.info("LAYER 2 HIT: Semantic match via Keywords")
            return keyword_hit

        # Layer 3: Semantic Hit (Vector Similarity) - 1 Embedding API call
        logger.info("No text-based hits. Transitioning to Semantic Search (Vector)...")
        jd_embedding = get_embedding(jd_text)
        cached_reqs = self._find_semantic_cache(jd_text, jd_embedding)
        if cached_reqs:
            logger.info("LAYER 3 HIT: Matched via Vector Similarity")
            return cached_reqs

        # Layer 4: AI Extraction (Chat Completion) - PHƯƠNG ÁN CUỐI
        logger.info("Knowledge Retrieval failed. Executing AI Extraction (GPT)...")

        # 3. Normalization (Multilingual Bridge)
        logger.info("Normalizing JD terms via Knowledge Graph...")
        normalized_jd = self._normalize_terms_in_text(jd_text)

        prompt = f"""
        BẠN LÀ MỘT CHUYÊN GIA TUYỂN DỤNG CÔNG NGHỆ CAO CẤP.
        Hãy trích xuất hoặc suy luận danh sách các kỹ năng yêu cầu từ mô tả công việc (JD) sau.

        JD CONTENT: 
        {normalized_jd}

        YÊU CẦU:
        1. Trích xuất tối thiểu 5-8 yêu cầu quan trọng nhất.
        2. Với mỗi yêu cầu, định dạng JSON như sau:
           - skill: Tên kỹ năng chuẩn (ví dụ: 'Python', 'React', 'Cloud Architecture')
           - target_level: Cấp độ mong muốn (Junior, Mid-level, Senior, Expert)
           - years_required: Số năm kinh nghiệm tối thiểu (số nguyên, mặc định 2 nếu không rõ)
           - is_primary: true nếu là bắt buộc/cốt lõi, false nếu là điểm cộng.

        LƯU Ý: Nếu JD quá ngắn, hãy dựa vào tiêu đề hoặc ngữ cảnh để ĐỀ XUẤT các kỹ năng tiêu chuẩn cho vị trí đó. Tuyệt đối không để trống.
        Trả về JSON với key duy nhất là "requirements".
        """
        try:
            if LLM_PROVIDER == "openai":
                response = openai_client.chat.completions.create(
                    model=LLM_MODEL, 
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                raw_content = response.choices[0].message.content
                raw = json.loads(raw_content)
                reqs = raw.get("requirements") or raw.get("skills") or raw.get("items") or []
                
                normalized_reqs = []
                for r in reqs:
                    s_name = r.get("skill") or r.get("skill_name") or r.get("name")
                    if not s_name: continue
                    
                    normalized_reqs.append({
                        "skill": self._clean_skill_name(s_name),
                        "target_level": r.get("target_level") or r.get("required_level") or r.get("level") or "Mid-level",
                        "years_required": r.get("years_required") or r.get("min_years_exp") or r.get("years") or 2,
                        "is_primary": r.get("is_primary") or r.get("is_mandatory") or False
                    })
                
                self._save_to_cache(jd_text, jd_embedding, normalized_reqs)
                return normalized_reqs
            return []
        except Exception as e:
            logger.error(f"Error extracting requirements with AI: {str(e)}")
            return []

    async def infer_market_requirements_for_cv(self, cv_id: str) -> List[Dict[str, Any]]:
        """Sử dụng AI để tự suy luận yêu cầu thị trường dựa trên hồ sơ CV."""
        cv = self.db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
        if not cv: return []
        
        prompt = f"""
        Dựa trên bản tóm tắt hồ sơ và kinh nghiệm của ứng viên, hãy xác định vai trò mục tiêu của họ.
        Sau đó, liệt kê 5-8 kỹ năng kỹ thuật bắt buộc và yêu cầu thâm niên cho vai trò đó trên thị trường hiện tại.
        
        Candidate Summary: {cv.summary}
        Total Experience: {cv.experience_years_total} years
        
        Trả về JSON với format:
        {{ "requirements": [
            {{ "skill": "Java", "target_level": "Senior", "years_required": 5, "is_primary": true }},
            ...
        ] }}
        """
        try:
            response = openai_client.chat.completions.create(
                model=LLM_MODEL, 
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            raw = json.loads(response.choices[0].message.content)
            reqs = raw.get("requirements") or []
            return reqs
        except Exception as e:
            logger.error(f"Error inferring market requirements: {e}")
            return []

    def _clean_skill_name(self, name: str) -> str:
        if not name: return ""
        noise = [
            r"^(understanding(\s+of)?|knowledge(\s+of)?|experience(\s+(with|in))?|familiarity(\s+with)?|ability(\s+to)?|deep|strong|expert)\s+",
            r"^(hiểu biết(\s+(về|sâu về))?|kinh nghiệm|thành thạo|có khả năng|biết)\s+",
            r"\s+(understanding|knowledge|experience|understanding)$"
        ]
        cleansed = name.strip()
        for pattern in noise: cleansed = re.sub(pattern, "", cleansed, flags=re.IGNORECASE)
        
        # Check against Graph for canonical translation if still Vietnamese
        canonical = taxonomy_service.get_canonical_mapping().get(cleansed.lower())
        if canonical: return canonical

        mapping = {
            "clean coding": "Clean Code", "designing apis": "API Design", "api design and implementation": "API Design", "ui complex experience": "Complex UI"
        }
        return mapping.get(cleansed.lower(), cleansed.strip())

    def _process_skill_logic(self, req: Dict[str, Any], user_skill_map_name: Dict[str, Any], user_skill_names_list: List[str], cv_id: str, user_max_years: float, user_role: Optional[str]) -> Dict[str, Any]:
        s_name_raw = req.get("skill_name", "Unknown Skill")
        req_level = req.get("required_level", "intermediate")
        req_level_score = LevelMapper.to_score(req_level)
        s_name_norm = self._normalize_name(s_name_raw)
        user_skill = user_skill_map_name.get(s_name_norm)
        
        result = {
            "skill": s_name_raw, "score": 0, "match_found": False, "gap_type": "MISSING", 
            "is_primary": req.get("is_primary", neo4j_client.is_primary_tech(s_name_raw)),
            "details": {"required_level": req_level, "reason": "Kỹ năng này hiện chưa tìm thấy trong CV của bạn."}
        }

        # Stage 0: Inference
        if not user_skill and neo4j_client.is_skill_implied_by_role(s_name_raw, user_role):
            inf_score = 0.8 if user_max_years >= 3 else 0.6
            result.update({"score": inf_score, "match_found": True, "gap_type": "INFERRED"})
            result["details"]["reason"] = f"Graph Inference: Kỹ năng ngầm định dựa trên vai trò '{user_role}' của bạn."
            return result

        if not user_skill and neo4j_client.is_foundational_standard(s_name_raw):
            inf_score = 0
            if user_max_years >= 5: inf_score = 0.9
            elif user_max_years >= 2: inf_score = 0.7
            if inf_score > 0:
                result.update({"score": inf_score, "match_found": True, "gap_type": "INFERRED"})
                result["details"]["reason"] = f"Seniority Inference: Tự động công nhận dựa trên {user_max_years} năm chuyên môn."
                return result

        # Stage 1: Exact Match
        if user_skill:
            user_level_score = LevelMapper.to_score(user_skill.get("level", "Junior"))
            level_gap = req_level_score - user_level_score
            final_score = 1.0 if level_gap <= 0 else max(1.0 - (level_gap * 0.25), 0.1)
            result.update({
                "match_found": True, "score": final_score,
                "details": {"your_level": user_skill.get("level", "Junior"), "required_level": req_level, "reason": "Khớp chính xác tên kỹ năng."}
            })
            return result

        # Stage 2: Semantic Match
        target_skill_obj = self.db.query(Skill).filter(Skill.name.ilike(s_name_raw)).first()
        if target_skill_obj and target_skill_obj.vector is not None:
            query = text("""
                SELECT usp.level, s.name, 1 - (s.vector <=> :target_vec::vector) as similarity
                FROM user_skill_profile usp JOIN skills s ON usp.skill_id = s.id
                WHERE usp.cv_id = :cv_id ORDER BY similarity DESC LIMIT 1
            """)
            sim_res = self.db.execute(query, {"target_vec": target_skill_obj.vector, "cv_id": cv_id}).first()
            if sim_res and sim_res.similarity > 0.88:
                user_level_score = LevelMapper.to_score(sim_res.level)
                level_gap = req_level_score - user_level_score
                sim_pct = round(float(sim_res.similarity) * 100, 1)
                result.update({
                    "match_found": True, "score": max(0.95 - (level_gap * 0.2), 0.1),
                    "gap_type": "SYNONYM", 
                    "details": {"matched_by": sim_res.name, "your_level": sim_res.level, "required_level": req_level, "similarity": sim_pct, "reason": f"Khớp qua tương đồng ({sim_pct}%) với '{sim_res.name}'."}
                })
                return result

        # Stage 3: Graph Match
        graph_res = neo4j_client.get_gap_classification(user_skill_names_list, s_name_raw)
        if graph_res["gap_type"] != "MISSING":
            gap_type = graph_res["gap_type"]
            g_score = 0.6 if gap_type == "TRANSITION" else 0.5
            result.update({
                "match_found": True, "gap_type": gap_type, "score": g_score,
                "details": {"matched_via_graph": True, "required_level": req_level, "matched_by": graph_res["matched_by"], "reason": f"Mối quan hệ Graph: {graph_res['reason']}."}
            })
            return result
        return result

    async def calculate_gap_v2(self, user_id: str, cv_id: str, requirements_source: Any):
        logger.info(f"=== Starting Engine V5.15 (Seniority-Aware) CV: {cv_id} ===")
        
        # 1. Thu thập dữ liệu thâm niên chuyên môn
        work_exp = self.db.query(UserWorkExperience).filter(UserWorkExperience.cv_id == uuid.UUID(cv_id)).all()
        
        user_skills_query = self.db.query(UserSkillProfile, Skill.name).join(Skill).filter(UserSkillProfile.cv_id == uuid.UUID(cv_id)).all()
        user_skill_map_name = {self._normalize_name(s_name): {"level": usp.level, "years": usp.years_exp} for usp, s_name in user_skills_query}
        user_skill_names_list = [s_name for _, s_name in user_skills_query]
        user_max_years = max([s["years"] for s in user_skill_map_name.values()] + [0])
        user_role = self._detect_user_role(cv_id)

        results = {
            "overall_match_pct": 0, 
            "breakdown": {"met": [], "gap": [], "partial": []}, 
            "recommendations": [], 
            "seniority_report": [],
            "notes": []
        }
        
        m_score, m_weight, o_score, o_weight = 0.0, 0.0, 0.0, 0.0
        any_mandatory_gap = False
        if not requirements_source: return results

        for r_src in requirements_source:
            if hasattr(r_src, "__dict__") and not isinstance(r_src, dict):
                req = {
                    "type": "skill", 
                    "skill_name": r_src.skill.name if (hasattr(r_src, "skill") and r_src.skill) else "Unknown", 
                    "importance_weight": r_src.importance_weight, 
                    "required_level": r_src.required_level, 
                    "is_mandatory": r_src.is_mandatory,
                    "min_years_exp": getattr(r_src, "min_years_exp", 0)
                }
            else: 
                req = dict(r_src)
                # Normalize AI output keys to match the expected format
                if "skill_name" not in req: req["skill_name"] = req.get("skill", "Unknown Skill")
                if "required_level" not in req: req["required_level"] = req.get("target_level", "intermediate")
                if "min_years_exp" not in req: req["min_years_exp"] = req.get("years_required", 0)
                if "is_mandatory" not in req: req["is_mandatory"] = req.get("is_primary", True)
                if "importance_weight" not in req: req["importance_weight"] = 5

            if "is_primary" not in req: req["is_primary"] = neo4j_client.is_primary_tech(req.get("skill_name", ""))
            is_group = req.get("type") == "group" or "skills" in req
            is_mandatory = req.get("is_mandatory", True)
            weight = float(req.get("importance_weight", 5))
            min_years_required = float(req.get("min_years_exp", 0))
            
            if not is_group:
                eval_res = self._process_skill_logic(req, user_skill_map_name, user_skill_names_list, cv_id, user_max_years, user_role)
                final_score = eval_res["score"]
                item_name = eval_res["skill"]
                
                # NÂNG CẤP SIÊU TRÍ TUỆ: Tìm bằng chứng thâm niên thông qua Semantic Matching thay vì string match
                specialty_years = 0
                relevant_jobs = []
                for job in work_exp:
                    # Dùng chính Engine so khớp để tìm kỹ năng trong context của từng task cũ
                    job_skills_context = [s for s in (job.skills_context or [])]
                    # Giả lập một mini-match cho context này
                    context_match = False
                    if any(item_name.lower() in s.lower() for s in job_skills_context):
                        context_match = True
                    else:
                        # Thử Graph/Synonym match nếu string match thất bại
                        for js in job_skills_context:
                            gs = neo4j_client.get_gap_classification([js], item_name)
                            if gs["gap_type"] in ["SYNONYM", "EXACT"]:
                                context_match = True
                                break
                    
                    if context_match:
                        specialty_years += job.duration_years
                        # Thêm trích dẫn ngữ cảnh (highlights) để chứng minh thâm niên
                        highlight = f"**{job.position_name}** tại *{job.company_name}* ({job.duration_years} năm)"
                        if job.description:
                            # Trích xuất 1 đoạn ngắn chứa keyword (nếu có)
                            pattern = re.compile(re.escape(item_name), re.IGNORECASE)
                            match = pattern.search(job.description)
                            if match:
                                start = max(0, match.start() - 40)
                                end = min(len(job.description), match.end() + 60)
                                highlight += f": \"...{job.description[start:end].strip()}...\""
                        relevant_jobs.append(highlight)
                
                if specialty_years > 0:
                    results["seniority_report"].append({
                        "skill": item_name,
                        "total_years": round(specialty_years, 1),
                        "highlights": relevant_jobs[:3] # Lấy tối đa 3 dẫn chứng tốt nhất
                    })

                if min_years_required > 0:
                    seniority_ratio = min(specialty_years / min_years_required, 1.0) if min_years_required > 0 else 1.0
                    # TĂNG TRỌNG SỐ THỰC CHIẾN: 30% Level, 70% Thâm niên thực tế trong context
                    final_score = (final_score * 0.3) + (seniority_ratio * 0.7)
                    eval_res["details"]["specialty_years"] = specialty_years
                    eval_res["details"]["reason"] += f" (Chứng minh thực chiến: {round(specialty_years, 1)}/{min_years_required} năm)"
            else:
                sub_skills = req.get("skills", [])
                item_name = " / ".join([s.get("skill_name", "???") for s in sub_skills])
                best_sub_res = None
                for sub_s in sub_skills:
                    sub_res = self._process_skill_logic(sub_s, user_skill_map_name, user_skill_names_list, cv_id, user_max_years, user_role)
                    if best_sub_res is None or sub_res["score"] > best_sub_res["score"]: best_sub_res = sub_res
                
                if best_sub_res["match_found"]:
                    final_score = 1.0
                    eval_res = {**best_sub_res, "skill": item_name, "score": 1.0, "match_found": True}
                    eval_res["details"]["reason"] = f"Đạt yêu cầu nhóm thông qua kỹ năng '{best_sub_res.get('skill')}'."
                else:
                    final_score = 0.0
                    eval_res = {**best_sub_res, "skill": item_name, "score": 0.0, "match_found": False}

            if is_mandatory: m_weight += weight; m_score += (final_score * weight)
            else: o_weight += weight; o_score += (final_score * weight)

            if eval_res["match_found"]:
                category = "met" if final_score >= 0.85 else "partial"
                results["breakdown"][category].append({**eval_res, "is_mandatory": is_mandatory, "score": round(final_score*100, 1)})
                
                if category == "partial":
                    # SỬA: Gọi đúng tên hàm recommend_for_gap
                    target_score = LevelMapper.to_score(eval_res.get("target_level", "Mid-level"))
                    recs = self.recommender.recommend_for_gap(eval_res["skill"], target_level_score=target_score, gap_type="PARTIAL", limit=1)
                    results["recommendations"].extend(recs)
            else:
                results["breakdown"]["gap"].append({"skill": item_name, "is_mandatory": is_mandatory, "gap_type": "MISSING", "score": 0, "is_primary": req.get("is_primary")})
                if is_mandatory: any_mandatory_gap = True
                
                # SỬA: Gọi đúng tên hàm recommend_for_gap
                recs = self.recommender.recommend_for_gap(item_name, target_level_score=60, gap_type="MISSING", limit=2)
                results["recommendations"].extend(recs)

        m_pct = (m_score / m_weight * 100) if m_weight > 0 else 0 
        o_pct = (o_score / o_weight * 100) if o_weight > 0 else 0
        
        # CÔNG THỨC MỚI: Không dùng Hard Cap 65% mà dùng Dynamic Penalty
        if m_weight == 0 and o_weight > 0: final_match = round(o_pct, 1)
        elif m_weight > 0: 
            # Điểm cơ sở
            final_match = (m_pct * 0.8) + (o_pct * 0.2)
            # Penalty nếu thiếu Mandatory: Trừ tối đa 20% tổng điểm thay vì khóa cứng
            if any_mandatory_gap:
                def is_m(r):
                    if isinstance(r, dict): return r.get("is_mandatory") or r.get("is_primary") or False
                    return getattr(r, "is_mandatory", False)
                
                num_mandatory = len([r for r in requirements_source if is_m(r)])
                num_missing = len(results["breakdown"]["gap"])
                penalty = (num_missing / num_mandatory * 20) if num_mandatory > 0 else 0
                final_match = max(final_match - penalty, 15.0) # Không bao giờ xuống dưới 15% nếu vẫn có kỹ năng khớp
            
            final_match = round(final_match, 1)
        else: final_match = 0.0
        
        results["overall_match_pct"] = final_match
        
        # Sắp xếp và làm sạch recommendations
        seen_courses = set()
        clean_recs = []
        for r in results["recommendations"][:10]: # Tăng pool trước khi lọc
            if r["id"] not in seen_courses:
                clean_recs.append(r)
                seen_courses.add(r["id"])
        results["recommendations"] = clean_recs[:5]
        
        return results
