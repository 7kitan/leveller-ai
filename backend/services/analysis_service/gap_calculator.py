from sqlalchemy.orm import Session
from shared.models import Skill, UserCV, UserWorkExperience, Job, UserSkillProfile
from shared.level_mapper import LevelMapper
from shared.neo4j_client import neo4j_client
from shared.taxonomy_service import taxonomy_service
from .recommender import CourseRecommender
import uuid
import logging
import json
from typing import List, Dict, Any, Optional

from .engine.retriever import RequirementRetriever
from .engine.matcher import SkillMatcher
from .engine.scorer import GapScorer

logger = logging.getLogger("gap_calculator")

class GapCalculator:
    def __init__(self, db: Session):
        self.db = db
        self.recommender = CourseRecommender(db)
        self.retriever = RequirementRetriever(db)
        self.matcher = SkillMatcher(db)
        self.scorer = GapScorer()

    async def extract_requirements_from_text(self, jd_text: str) -> List[Dict[str, Any]]:
        """AI Trích xuất JD (Delegated to Retriever)."""
        return await self.retriever.extract(jd_text)

    def _normalize_name(self, name: str) -> str:
        return self.matcher._normalize_name(name)

    def _detect_user_role(self, cv_id: str) -> Optional[str]:
        """Xác định vai trò chuyên môn của ứng viên từ Graph (Neo4j)."""
        try:
            cv = self.db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
            if not cv or not cv.summary: return None
            
            summary = cv.summary.lower()
            pos_list = neo4j_client.get_positions()
            
            for pos_name in pos_list:
                if pos_name.lower() in summary: return pos_name
            
            user_pos_skill = self.db.query(Skill.name).join(UserSkillProfile).filter(
                UserSkillProfile.cv_id == uuid.UUID(cv_id), Skill.name.in_(pos_list)
            ).first()
            
            if user_pos_skill: return user_pos_skill.name
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error detecting user role: {e}")
            return None

    async def calculate_gap_v2(self, user_id: str, cv_id: str, requirements_source: Any):
        logger.info(f"=== Starting Engine V6.0 (Modular & Seniority-Free) CV: {cv_id} ===")
        
        user_skills_query = self.db.query(UserSkillProfile, Skill.name).join(Skill).filter(UserSkillProfile.cv_id == uuid.UUID(cv_id)).all()
        user_skill_map = {self._normalize_name(s_name): {"level": usp.level, "years": usp.years_exp} for usp, s_name in user_skills_query}
        user_skills_list = [s_name for _, s_name in user_skills_query]
        
        results = {
            "overall_match_pct": 0,
            "breakdown": {"met": [], "gap": [], "partial": []}, 
            "recommendations": [], 
            "notes": []
        }

        if not requirements_source: return results

        weighted_score_sum = 0.0
        total_weight_sum = 0.0
        
        # BROAD CATEGORY BLACKLIST: Do not count these generic items in the score denominator
        FILTER_KEYWORDS = ["technologies", "languages", "requirements", "tools", "stack", "category", "alternative", 
                           "development", "communication", "teamwork", "management", "problem solving"]

        valid_requirements = []
        for r_src in requirements_source:
            req = self._parse_requirement(r_src)
            item_name = req.get("skill_name", "").lower()
            
            # Skip requirements that are clearly generic or non-technical
            if any(kw in item_name for kw in FILTER_KEYWORDS) and len(item_name.split()) < 4:
                # If it's a generic word and short, it's likely a container we should skip counting
                logger.info(f"FILTERING OUT GENERIC REPLACEMENT: {item_name}")
                continue
            
            valid_requirements.append(req)

        requirement_count = len(valid_requirements)

        for req in valid_requirements:
            is_group = req.get("type") == "group" or "skills" in req
            is_mandatory = req.get("is_mandatory", True)
            
            # WEIGHTING: Mandatory = 10, Optional = 3
            item_weight = 10.0 if is_mandatory else 3.0
            
            if not is_group:
                eval_res = await self.matcher.match_skill(req, user_skill_map, user_skills_list)
                final_score = eval_res["score"]
                item_name = eval_res["skill"]
            else:
                sub_skills = req.get("skills", [])
                strategy = req.get("group_strategy", "exclusive")
                item_name = req.get("group_name") or "Group"
                
                sub_results = []
                for s in sub_skills:
                    sub_results.append(await self.matcher.match_skill(s, user_skill_map, user_skills_list))
                
                if strategy == "inclusive": # AND
                    final_score = sum(s["score"] for s in sub_results) / len(sub_results) if sub_results else 0
                    gaps = [s["skill"] for s in sub_results if s["score"] < 0.7]
                    eval_res = {
                        "skill": item_name, 
                        "score": final_score, 
                        "match_found": final_score > 0, 
                        "details": {
                            "reason": f"(AND) Match. Missing/Partial: {', '.join(gaps)}" if gaps else "(AND) Full Match",
                            "sub_results": sub_results
                        }
                    }
                else: # OR
                    best_sub = max(sub_results, key=lambda x: x["score"]) if sub_results else {"score": 0}
                    final_score = best_sub["score"]
                    eval_res = {
                        **best_sub, 
                        "skill": item_name, 
                        "details": {
                            **best_sub.get("details", {}),
                            "reason": f"(OR) Best via {best_sub.get('skill')}",
                            "sub_results": sub_results
                        }
                    }

            total_weight_sum += item_weight
            weighted_score_sum += (final_score * item_weight)

            if eval_res.get("match_found"):
                category = "met" if final_score >= 0.85 else "partial"
                results["breakdown"][category].append({**eval_res, "is_mandatory": is_mandatory, "score": round(final_score*100, 1)})
                if category == "partial":
                    recs = self.recommender.recommend_for_gap(eval_res["skill"], target_level_score=LevelMapper.to_score(eval_res["details"].get("required_level", "Mid-level")), gap_type="PARTIAL", limit=1)
                    results["recommendations"].extend(recs)
            else:
                results["breakdown"]["gap"].append({"skill": item_name, "is_mandatory": is_mandatory, "gap_type": "MISSING", "score": 0})
                recs = self.recommender.recommend_for_gap(item_name, target_level_score=60, gap_type="MISSING", limit=2)
                results["recommendations"].extend(recs)

        results["overall_match_pct"] = self.scorer.calculate_overall_score(weighted_score_sum, total_weight_sum)
        results["notes"].append(f"Calculation Method: Strict Weighted Technical Match ({requirement_count} items)")
        
        # Cleanup recommendations
        seen = set()
        results["recommendations"] = [r for r in results["recommendations"] if not (r["id"] in seen or seen.add(r["id"]))][:5]
        
        return results

    def _parse_requirement(self, r_src: Any) -> Dict[str, Any]:
        if hasattr(r_src, "__dict__") and not isinstance(r_src, dict):
            return {
                "type": "skill", 
                "skill_name": r_src.skill.name if (hasattr(r_src, "skill") and r_src.skill) else "Unknown", 
                "importance_weight": r_src.importance_weight, 
                "required_level": r_src.required_level, 
                "is_mandatory": r_src.is_mandatory
            }
        req = dict(r_src)
        if "skill_name" not in req: req["skill_name"] = req.get("skill") or req.get("group_name") or "Unknown"
        if "required_level" not in req: req["required_level"] = req.get("target_level", "intermediate")
        if "is_mandatory" not in req: 
            # Default to True if neither is_mandatory nor is_primary exists or if is_primary is True
            req["is_mandatory"] = req.get("is_primary", True)
        if "importance_weight" not in req: req["importance_weight"] = 5
        return req
