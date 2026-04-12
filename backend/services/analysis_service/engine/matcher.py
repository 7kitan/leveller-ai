import os
import re
import logging
import httpx
from typing import List, Dict, Any, Optional
from shared.level_mapper import LevelMapper
from shared.neo4j_client import neo4j_client
from shared.taxonomy_service import taxonomy_service

logger = logging.getLogger("gap_calculator.matcher")

class SkillMatcher:
    def __init__(self, db):
        self.db = db
        # Configurable matching layers via .env, default to exact and graph
        layer_config = os.getenv("GAP_MATCHING_LAYERS", "exact,graph")
        self.active_layers = [layer.strip().lower() for layer in layer_config.split(",") if layer.strip()]
        self.bertscore_api_url = os.getenv("BERTSCORE_API_URL")
        self.bertscore_api_key = os.getenv("BERTSCORE_API_KEY", "")

    def _normalize_name(self, name: str) -> str:
        if not name: return ""
        n = name.lower().strip()
        n = re.sub(r'(\.js|js|programming|language|coding|stack|framework)$', '', n)
        n = re.sub(r'[^a-z0-9#+]', '', n)
        return n

    def _calculate_final_score(self, user_level_score: float, req_level_score: float, user_years: float, req_years: float, multiplier: float = 1.0) -> float:
        """
        Unified scoring logic:
        - If req_years == 0 (Skill-only): 1.0 if match found.
        - If req_years > 0 (Seniority-based): Proportional match (Level 50% + Years 50%).
        """
        if req_years <= 0:
            # Nếu không yêu cầu số năm -> Chỉ cần tìm thấy là Match 100% (bỏ qua level)
            return 1.0 * multiplier
        
        # Level Match
        level_match = 1.0 if user_level_score >= req_level_score else (user_level_score / req_level_score)
        
        # Years Match
        years_match = min(1.0, user_years / req_years) if req_years > 0 else 1.0
        
        # Total Weighted Match (50/50)
        final_score = (level_match * 0.5) + (years_match * 0.5)
        return final_score * multiplier

    def _execute_exact_match(self, req_level_score: float, req_level: str, req_years: float, s_name_raw: str, s_name_norm: str, user_skill_map: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        user_skill = user_skill_map.get(s_name_norm)
        
        # Canonical Alias Match
        if not user_skill:
             canonical = taxonomy_service.get_canonical_mapping().get(s_name_raw.lower().strip())
             if canonical:
                 user_skill = user_skill_map.get(self._normalize_name(canonical))

        if user_skill:
            user_level_str = user_skill.get("level", "Junior")
            user_level_score = LevelMapper.to_score(user_level_str)
            user_years = user_skill.get("years", 0)
            
            final_score = self._calculate_final_score(user_level_score, req_level_score, user_years, req_years)
            
            return {
                "match_found": True, 
                "score": final_score,
                "gap_type": "MET" if final_score >= 0.85 else "PARTIAL",
                "details": {
                    "your_level": user_level_str, 
                    "required_level": req_level,
                    "your_years": user_years,
                    "required_years": req_years,
                    "reason": "Khớp tên kỹ năng chuẩn."
                }
            }
        return None

    def _execute_graph_match(self, req_level_score: float, req_level: str, req_years: float, s_name_raw: str, user_skill_map: Dict[str, Any], user_skills_list: List[str]) -> Optional[Dict[str, Any]]:
        graph_res = neo4j_client.get_gap_classification(user_skills_list, s_name_raw)
        if graph_res["gap_type"] != "MISSING":
            gap_type = graph_res["gap_type"]
            matched_skill_name = graph_res["matched_by"]
            
            # Khôi phục Level của skill cũ để "kế thừa"
            inherited_skill = user_skill_map.get(self._normalize_name(matched_skill_name), {})\
            
            inherited_level_str = inherited_skill.get("level", "Junior")
            inherited_level_score = LevelMapper.to_score(inherited_level_str)
            inherited_years = inherited_skill.get("years", 0)
            
            # Hệ số suy giảm do lệch công nghệ (Framework gap = 80% sức mạnh, loại khác 60%)
            graph_multiplier = 0.8 if gap_type == "FRAMEWORK_GAP" else 0.6
            
            final_score = self._calculate_final_score(inherited_level_score, req_level_score, inherited_years, req_years, multiplier=graph_multiplier)

            # Nếu final_score nằm trong vùng [0.7, 0.85) thì hệ thống vẫn tính là Partial và recommend khóa học chuyển đổi công nghệ!
            classified_gap = "MET" if final_score >= 0.85 else "PARTIAL"
            
            return {
                "match_found": True, "gap_type": classified_gap, "score": final_score,
                "details": {
                    "matched_via_graph": True, 
                    "your_level": inherited_level_str,
                    "required_level": req_level, 
                    "your_years": inherited_years,
                    "required_years": req_years,
                    "matched_by": matched_skill_name, 
                    "reason": f"Kế thừa hệ sinh thái từ {matched_skill_name}. (Graph: {graph_res['reason']})"
                }
            }
        return None

    async def _execute_semantic_match(self, req_level: str, req_years: float, s_name_raw: str, user_skills_list: List[str]) -> Optional[Dict[str, Any]]:
        # Semantic Match uses AI to compare descriptions/names, usually doesn't have fine-grained level/years from CV easily
        # For now, it returns the score directly from BERTScore
        if not self.bertscore_api_url or not user_skills_list:
            return None
            
        try:
            payload = {
                "cv_skills": user_skills_list,
                "jd_skill": s_name_raw
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.bertscore_api_url,
                    json=payload,
                    headers={"X-AI-Key": self.bertscore_api_key} if self.bertscore_api_key else {}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status")
                    if status in ("PASS", "PARTIAL"):
                        score = float(data.get("score", 0))
                        # If AI says PASS but it's Semantic, we might still want to check if it's a "no years" case
                        # But Semantic service usually doesn't know about user_years.
                        # For simplicity, we trust the AI score but cap it if req_years > 0? No, let's keep AI result as is.
                        gap_type = "MET" if status == "PASS" else "PARTIAL"
                        return {
                            "match_found": True,
                            "gap_type": gap_type,
                            "score": score,
                            "details": {
                                "matched_via_graph": False,
                                "matched_via_ai": True,
                                "required_level": req_level,
                                "required_years": req_years,
                                "matched_by": data.get("best_match", ""),
                                "reason": f"AI Semantic Match (Score: {score})."
                            }
                        }
        except Exception as e:
            logger.error(f"Semantic match failed for {s_name_raw}: {e}")
            
        return None

    async def match_skill(self, req: Dict[str, Any], user_skill_map: Dict[str, Any], user_skills_list: List[str]) -> Dict[str, Any]:
        s_name_raw = req.get("skill_name") or req.get("skill") or "Unknown Skill"
        req_level = req.get("required_level") or req.get("target_level") or "intermediate"
        req_years = float(req.get("years_required") or req.get("min_years_exp") or 0)
        
        req_level_score = LevelMapper.to_score(req_level)
        s_name_norm = self._normalize_name(s_name_raw)
        
        # Default missing result
        result = {
            "skill": s_name_raw, "score": 0, "match_found": False, "gap_type": "MISSING", 
            "is_primary": req.get("is_primary", neo4j_client.is_primary_tech(s_name_raw)),
            "details": {"required_level": req_level, "required_years": req_years, "reason": "Kỹ năng này hiện chưa tìm thấy trong CV của bạn."}
        }

        # Evaluate through active layers (Short-circuit on first successful match to save compute)
        for layer in self.active_layers:
            match_res = None
            if layer == "exact":
                match_res = self._execute_exact_match(req_level_score, req_level, req_years, s_name_raw, s_name_norm, user_skill_map)
            elif layer == "graph":
                match_res = self._execute_graph_match(req_level_score, req_level, req_years, s_name_raw, user_skill_map, user_skills_list)
            elif layer == "semantic":
                match_res = await self._execute_semantic_match(req_level, req_years, s_name_raw, user_skills_list)
            
            if match_res and match_res["match_found"]:
                result.update(match_res)
                result["details"]["matching_layer"] = layer
                return result # Fallback chain complete

        return result
