import os
import re
import logging
import math
from typing import List, Dict, Any, Optional
from datetime import datetime
from shared.llm_utils import get_embeddings_batch, build_jd_skill_context
from shared.config_utils import config_manager

logger = logging.getLogger("gap_calculator.advanced_engine")

class AdvancedGapEngine:
    def __init__(self):
        # Configuration
        # Configuration - Ưu tiên DB > .env
        layer_config = config_manager.get_setting("GAP_MATCHING_LAYERS") or os.getenv("GAP_MATCHING_LAYERS", "exact,vector")
        self.active_layers = [layer.strip().lower() for layer in layer_config.split(",") if layer.strip()]
        
        pure_vec_val = config_manager.get_setting("GAP_VECTOR_PURE_SCORING")
        if pure_vec_val is not None:
            self.pure_vector_mode = str(pure_vec_val).lower() == "true"
        else:
            self.pure_vector_mode = os.getenv("GAP_VECTOR_PURE_SCORING", "false").lower() == "true"
        
        
        # Tier 1: Alias Dictionary
        self.alias_map = {
            "nodejs": "node_js",
            "node": "node_js",
            "reactjs": "react",
            "react": "react",
            "vuejs": "vue",
            "vue": "vue",
            "golang": "go",
            "go": "go",
            "typescript": "ts",
            "typescriptjs": "ts",
            "javascript": "js",
            "js": "js",
            "mongodb": "mongo",
            "postgresql": "postgres",
            "postgres": "postgres",
            "mssql": "sqlserver",
            "aws": "amazon_web_services",
            "gcp": "google_cloud_platform",
        }

    def _normalize(self, text: str) -> str:
        """Chuẩn hóa: lowercase và xóa ký tự đặc biệt thừa."""
        if not text:
            return ""
        # Lowercase
        text = text.lower()
        # Xóa các ký tự đặc biệt thừa (., -, khoảng trắng)
        text = re.sub(r'[^a-zA-Z0-9]', '', text)
        return text

    def _get_canonical_name(self, name: str) -> str:
        """Chuyển đổi tên sang tên chuẩn thông qua Alias Dictionary."""
        norm = self._normalize(name)
        return self.alias_map.get(norm, norm)

    def _match_tier1(self, req_name: str, cv_norm_names: List[str]) -> float:
        """Tầng 1: Exact Match & Alias Match (Khớp tuyệt đối)."""
        req_canonical = self._get_canonical_name(req_name)
        if req_canonical in cv_norm_names:
            return 1.0
        return 0.0

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if v1 is None or v2 is None: return 0.0
        dot = sum(a*b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a*a for a in v1))
        norm2 = math.sqrt(sum(b*b for b in v2))
        if norm1 == 0 or norm2 == 0: return 0.0
        return float(dot / (norm1 * norm2))

    def _calculate_multiplier(self, user_level: str, req_level: str, user_years: float, req_years: float, last_used: int = None) -> float:
        """
        Calculates match multiplier based on Seniority, Experience, and Recency.
        """
        LEVEL_WEIGHTS = {"Junior": 0.25, "Mid-level": 0.50, "Senior": 0.75, "Expert": 1.0}
        
        # 1. Level Factor
        u_l = LEVEL_WEIGHTS.get(user_level, 0.25)
        r_l = LEVEL_WEIGHTS.get(req_level, 0.50)
        level_factor = min(1.0, u_l / r_l) if r_l > 0 else 1.0
        
        # 2. Experience Factor
        exp_factor = min(1.0, user_years / req_years) if req_years > 0 else 1.0
        
        # 3. Recency Factor (Decay)
        recency_factor = 1.0
        if last_used:
            current_year = datetime.now().year
            years_stale = max(0, current_year - last_used)
            # Decay 8% per year, min 50%
            recency_factor = max(0.5, 1.0 - (years_stale * 0.08))
            
        return float(level_factor * exp_factor * recency_factor)

    async def _match_tier2_vector(self, jd_vector: List[float], user_skills_data: List[Dict[str, Any]], req_level: str, req_years: float) -> Dict[str, Any]:
        """ Tầng 2: Vector Similarity Match với Metadata Multipliers. """
        if jd_vector is None:
            return {"score": 0.0, "reason": "No vector for requirement."}
        best_match = {"score": 0.0, "skill": None, "details": {}}
        
        for u_skill in user_skills_data:
            cv_vector = u_skill.get("vector")
            if cv_vector is None: continue
            
            sim = self._cosine_similarity(jd_vector, cv_vector)
            
            # Semantic gate: Phải có độ tương đồng tối thiểu
            if sim < 0.55: continue
            
            multiplier = 1.0
            if not self.pure_vector_mode:
                multiplier = self._calculate_multiplier(
                    u_skill.get("level", "Junior"),
                    req_level,
                    u_skill.get("years_exp", 0),
                    req_years,
                    u_skill.get("last_used_year")
                )
            
            final_score = float(sim * multiplier)
            
            if final_score > best_match["score"]:
                best_match = {
                    "score": final_score,
                    "skill": u_skill.get("name"),
                    "details": {
                        "cosine_sim": round(float(sim), 3),
                        "multiplier": round(float(multiplier), 3),
                        "user_level": u_skill.get("level"),
                        "user_years": float(u_skill.get("years_exp") or 0),
                        "semantic_match": round(float(sim) * 100, 1),
                        "seniority_match": round(float(multiplier) * 100, 1)
                    }
                }
        
        return best_match

    def resolve_group_score(self, group_req: Dict[str, Any], skill_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """ 
        Tầng 3: Xử lý Group Logic.
        Strategies:
        - "any_one": User needs ANY ONE skill from alternatives (OR logic)
        - "at_least_n": User needs at least N skills from alternatives
        - "all": User needs ALL skills from alternatives (AND logic)
        """
        strategy = group_req.get("group_strategy", "any_one")
        min_required = group_req.get("min_required", 1)
        
        if not skill_results:
            return {"score": 0.0, "status": "GAP", "match_found": False}
        
        # Count how many skills matched (score > 0)
        matched_skills = [s for s in skill_results if s.get("score", 0) > 0]
        matched_count = len(matched_skills)
        
        if strategy == "any_one":
            # User needs ANY ONE skill from alternatives
            if matched_count >= 1:
                best = max(matched_skills, key=lambda x: x["score"])
                return {
                    "score": best["score"],
                    "skill": best.get("skill"),
                    "match_found": True,
                    "strategy": "any_one (OR)",
                    "matched_count": matched_count,
                    "details": best.get("details", {})
                }
            else:
                return {"score": 0.0, "status": "GAP", "match_found": False, "strategy": "any_one (OR)"}
        
        elif strategy == "at_least_n":
            # User needs at least N skills from alternatives
            if matched_count >= min_required:
                # Take average of top N matched skills
                top_matches = sorted(matched_skills, key=lambda x: x["score"], reverse=True)[:min_required]
                avg_score = sum(s["score"] for s in top_matches) / len(top_matches)
                return {
                    "score": avg_score,
                    "match_found": True,
                    "strategy": f"at_least_{min_required}",
                    "matched_count": matched_count,
                    "required_count": min_required
                }
            else:
                # Partial match: user has some but not enough
                if matched_count > 0:
                    partial_score = matched_count / min_required * 0.5  # 50% penalty for incomplete
                    return {
                        "score": partial_score,
                        "match_found": False,
                        "strategy": f"at_least_{min_required}",
                        "matched_count": matched_count,
                        "required_count": min_required
                    }
                else:
                    return {"score": 0.0, "status": "GAP", "match_found": False, "strategy": f"at_least_{min_required}"}
        
        elif strategy == "all":
            # User needs ALL skills from alternatives (AND logic)
            total_count = len(skill_results)
            if matched_count == total_count:
                # All skills matched
                avg_score = sum(s["score"] for s in matched_skills) / total_count
                return {
                    "score": avg_score,
                    "match_found": True,
                    "strategy": "all (AND)",
                    "matched_count": matched_count,
                    "required_count": total_count
                }
            else:
                # Partial match with penalty
                missing_count = total_count - matched_count
                avg_score = sum(s["score"] for s in skill_results) / total_count
                penalty = (missing_count / total_count) * 0.5
                final_score = float(avg_score * (1 - penalty))
                return {
                    "score": final_score,
                    "match_found": final_score > 0.5,
                    "strategy": "all (AND)",
                    "matched_count": matched_count,
                    "required_count": total_count,
                    "missing_count": missing_count
                }
        
        else:
            # Fallback: treat as "any_one"
            if matched_count >= 1:
                best = max(matched_skills, key=lambda x: x["score"])
                return {
                    "score": best["score"],
                    "skill": best.get("skill"),
                    "match_found": True,
                    "strategy": "fallback (OR)"
                }
            else:
                return {"score": 0.0, "status": "GAP", "match_found": False}

    async def calculate_match(self, user_skills_data: List[Dict[str, Any]], jd_requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Unified Matching Pipeline:
        1. Batch Embed JD Reqs
        2. Tier 1 (Exact)
        3. Tier 2 (Vector + Multipliers)
        4. Tier 3 (Group Logic)
        
        Supports new skill group schema:
        - Groups have "is_group": true
        - "alternative_skills": ["Blender", "Maya", "3ds Max"]
        - "group_strategy": "any_one" | "at_least_n" | "all"
        """
        cv_norm_names = [self._get_canonical_name(s.get("name", "")) for s in user_skills_data]
        
        # 1. Batch Embed JD Reqs (Chỉ embed những cái chưa có vector cache)
        jd_contexts = []
        req_mapping = []
        for req in jd_requirements:
            # Check for new schema (is_group) or old schema (type == "group")
            is_group = req.get("is_group", False) or req.get("type") == "group"
            
            if is_group:
                # New schema: alternative_skills is array of strings
                alternative_skills = req.get("alternative_skills", [])
                if alternative_skills:
                    # Create individual requirement objects for each alternative
                    for skill_name in alternative_skills:
                        ctx = build_jd_skill_context(
                            skill_name, 
                            req.get("target_level") or req.get("required_level", "Junior"), 
                            req.get("years_required") or req.get("min_years_exp", 0)
                        )
                        jd_contexts.append(ctx)
                        # Create a sub-requirement object
                        sub_req = {
                            "skill": skill_name,
                            "skill_name": skill_name,
                            "target_level": req.get("target_level") or req.get("required_level", "Junior"),
                            "years_required": req.get("years_required") or req.get("min_years_exp", 0)
                        }
                        req_mapping.append(sub_req)
                else:
                    # Old schema fallback: skills array with objects
                    for s in req.get("skills", []):
                        ctx = build_jd_skill_context(s.get("skill"), s.get("target_level"), s.get("years_required"))
                        jd_contexts.append(ctx)
                        req_mapping.append(s)
            else:
                # Individual skill (not a group)
                skill_name = req.get("skill_name") or req.get("skill")
                ctx = build_jd_skill_context(
                    skill_name, 
                    req.get("target_level") or req.get("required_level", "Junior"), 
                    req.get("years_required") or req.get("min_years_exp", 0)
                )
                jd_contexts.append(ctx)
                req_mapping.append(req)
        
        if len(jd_contexts) > 0:
            vectors = get_embeddings_batch(jd_contexts)
            for i, vec in enumerate(vectors):
                req_mapping[i]["vector"] = vec

        must_have_results = []
        nice_to_have_results = []
        processed_breakdown = {"met": [], "gap": [], "partial": []}
        
        # 2. Process Requirements
        req_index = 0  # Track position in req_mapping for groups
        for req in jd_requirements:
            is_mandatory = req.get("is_mandatory", True)
            is_group = req.get("is_group", False) or req.get("type") == "group"
            
            if is_group:
                # Match each alternative skill in the group
                alternative_skills = req.get("alternative_skills", [])
                if not alternative_skills:
                    # Old schema fallback
                    alternative_skills = [s.get("skill") for s in req.get("skills", [])]
                
                member_results = []
                for skill_name in alternative_skills:
                    # Get the corresponding sub_req from req_mapping
                    if req_index < len(req_mapping):
                        sub_req = req_mapping[req_index]
                        req_index += 1
                        res = await self._process_individual_req(sub_req, user_skills_data, cv_norm_names)
                        member_results.append(res)
                
                # Resolve group using new strategy
                match_res = self.resolve_group_score(req, member_results)
                match_res["skill"] = req.get("skill") or req.get("group_name") or req.get("skill_name") or "Requirement Group"
            else:
                # Individual skill
                if req_index < len(req_mapping):
                    mapped_req = req_mapping[req_index]
                    req_index += 1
                    match_res = await self._process_individual_req(mapped_req, user_skills_data, cv_norm_names)
                else:
                    match_res = await self._process_individual_req(req, user_skills_data, cv_norm_names)

            match_res["is_mandatory"] = is_mandatory
            score = match_res.get("score", 0)
            
            if is_mandatory:
                must_have_results.append(match_res)
            else:
                nice_to_have_results.append(match_res)
                
            # Breakdown classification
            if score >= 0.80:
                processed_breakdown["met"].append({**match_res, "score": round(score * 100, 1)})
            elif score > 0.15:
                processed_breakdown["partial"].append({**match_res, "score": round(score * 100, 1)})
            else:
                processed_breakdown["gap"].append({**match_res, "score": 0})

        # 3. Final Scoring
        must_count = len(must_have_results)
        nice_count = len(nice_to_have_results)
        
        must_match_ratio = float(sum(r.get("score", 0) for r in must_have_results) / must_count) if must_count > 0 else 1.0
        nice_match_ratio = float(sum(r.get("score", 0) for r in nice_to_have_results) / nice_count) if nice_count > 0 else 1.0
        
        if must_count > 0 and nice_count > 0:
            overall_match_pct = (must_match_ratio * 0.7 + nice_match_ratio * 0.3) * 100
        elif must_count > 0:
            overall_match_pct = must_match_ratio * 100
        elif nice_count > 0:
            overall_match_pct = nice_match_ratio * 100
        else:
            overall_match_pct = 0
            
        # 4. Generate Cross-Similarity Matrix for UI
        cross_matrix = self._generate_cross_similarity_matrix(user_skills_data, jd_requirements)
            
        return {
            "overall_match_pct": round(overall_match_pct, 1),
            "breakdown": processed_breakdown,
            "must_have_score": round(must_match_ratio * 100, 1),
            "nice_to_have_score": round(nice_match_ratio * 100, 1),
            "cross_matrix": cross_matrix
        }

    def _generate_cross_similarity_matrix(self, user_skills: List[Dict[str, Any]], jd_reqs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """ Tạo 1 ma trận bảng so sánh chéo giữa JD và CV (Dành cho UI Heatmap Matrix). """
        jd_labels = []
        for req in jd_reqs:
            if req.get("type") == "group":
                jd_labels.append(req.get("group_name", "Group"))
            else:
                jd_labels.append(req.get("skill_name") or req.get("skill", "Unknown"))
        
        # Chỉ lấy top 12 skills của user để matrix không quá bị loãng trên UI
        cv_skills = sorted(user_skills, key=lambda x: x.get("years_exp", 0), reverse=True)[:12]
        cv_labels = [s.get("name", "Unknown") for s in cv_skills]
        
        scores = []
        for req in jd_reqs:
            row = []
            # Nếu là group, lấy vector của group (thường là vector của member đầu tiên hoặc null)
            # Ở đây ta lấy vector chung đã gán ở bước 1 trong calculate_match
            req_vec = req.get("vector")
            
            for u_skill in cv_skills:
                u_vec = u_skill.get("vector")
                if req_vec is not None and u_vec is not None:
                    sim = self._cosine_similarity(req_vec, u_vec)
                    # Gate similarity (chỉ show nếu > 0.3 để heatmap sạch)
                    row.append(round(float(sim), 3) if sim > 0.3 else 0.0)
                else:
                    row.append(0.0)
            scores.append(row)
            
        return {
            "jd_labels": jd_labels,
            "cv_labels": cv_labels,
            "scores": scores
        }

    async def _process_individual_req(self, req: Dict[str, Any], user_skills_data: List[Dict[str, Any]], cv_norm_names: List[str]) -> Dict[str, Any]:
        req_name = req.get("skill_name") or req.get("skill")
        # Support both field names: "target_level" (from AI JSON) and "required_level" (from ORM via _parse_requirement)
        req_level = req.get("target_level") or req.get("required_level") or "Mid-level"
        req_years = float(req.get("years_required") or 0)
        req_vector = req.get("vector")

        # Tier 1
        score = 0.0
        tier_used = 0
        details = {"reason": "Searching for match..."}

        if "exact" in self.active_layers:
            score = self._match_tier1(req_name, cv_norm_names)
            if score > 0:
                tier_used = 1
                details = {"reason": "Exact / Alias match found."}

        # Tier 2
        if score < 1.0 and req_vector is not None and "vector" in self.active_layers:
            vec_res = await self._match_tier2_vector(req_vector, user_skills_data, req_level, req_years)
            if vec_res["score"] > score:
                score = vec_res["score"]
                tier_used = 2
                details = vec_res.get("details", {})
                if self.pure_vector_mode:
                    details["reason"] = f"Pure Vector Match (Sim: {details.get('cosine_sim')})"
                else:
                    details["reason"] = f"Semantic Vector Match (Sim: {details.get('cosine_sim')})"

        return {
            "skill": req_name,
            "score": score,
            "tier": tier_used,
            "match_found": score > 0,
            "details": details
        }
