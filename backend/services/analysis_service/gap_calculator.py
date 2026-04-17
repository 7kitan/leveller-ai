from sqlalchemy.orm import Session
from shared.models import Skill, UserCV, UserWorkExperience, Job, UserSkillProfile
from shared.level_mapper import LevelMapper
from shared.neo4j_client import neo4j_client
from shared.taxonomy_service import taxonomy_service
import uuid
import logging
import json
from typing import List, Dict, Any, Optional

from .engine.retriever import RequirementRetriever
from .engine.matcher import SkillMatcher
from .engine.scorer import GapScorer
from .engine.advanced_gap_engine import AdvancedGapEngine

logger = logging.getLogger("gap_calculator")


class GapCalculator:
    def __init__(self, db: Session):
        self.db = db
        self.retriever = RequirementRetriever(db)
        self.matcher = SkillMatcher(db)
        self.scorer = GapScorer()
        self.advanced_engine = AdvancedGapEngine()

    async def extract_requirements_from_text(
        self, jd_text: str
    ) -> List[Dict[str, Any]]:
        """AI Trích xuất JD (Delegated to Retriever)."""
        return await self.retriever.extract(jd_text)

    def _normalize_name(self, name: str) -> str:
        return self.matcher._normalize_name(name)

    def _detect_user_role(self, cv_id: str) -> Optional[str]:
        """Xác định vai trò chuyên môn của ứng viên (Neo4j Disabled)."""
        # try:
        #     cv = self.db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
        #     if not cv or not cv.summary: return None
        #
        #     summary = cv.summary.lower()
        #     pos_list = neo4j_client.get_positions()
        #
        #     for pos_name in pos_list:
        #         if pos_name.lower() in summary: return pos_name
        #
        #     user_pos_skill = self.db.query(Skill.name).join(UserSkillProfile).filter(
        #         UserSkillProfile.cv_id == uuid.UUID(cv_id), Skill.name.in_(pos_list)
        #     ).first()
        #
        #     if user_pos_skill: return user_pos_skill.name
        #     return None
        # except Exception as e:
        #     self.db.rollback()
        #     logger.error(f"Error detecting user role: {e}")
        #     return None
        return None

    async def calculate_gap_v2(
        self, user_id: str, cv_id: str, requirements_source: Any
    ):
        logger.info(f"=== Starting Engine V7.0 (Advanced 3-Tier) CV: {cv_id} ===")

        # Reset any previously aborted transaction BEFORE any query
        try:
            self.db.rollback()
        except Exception:
            pass

        # 1. Lấy danh sách kỹ năng của User từ DB kèm Metadata (Vector, Level, Exp, Recency)
        # NOTE: Pass cv_id as native uuid.UUID — SQLAlchemy will handle the cast correctly.
        # Using uuid.UUID(str(...)) ensures it's a valid UUID object, avoiding ::UUID cast issues.
        try:
            cv_uuid = uuid.UUID(str(cv_id))
            user_skills_query = (
                self.db.query(UserSkillProfile, Skill.name)
                .join(Skill)
                .filter(UserSkillProfile.cv_id == cv_uuid)
                .all()
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"[calculate_gap_v2] Failed to query user skills: {e}")
            user_skills_query = []

        user_skills_data = []
        for profile, s_name in user_skills_query:
            user_skills_data.append(
                {
                    "name": s_name,
                    "vector": profile.vector,
                    "level": profile.level or "Junior",
                    "years_exp": profile.years_exp or 0,
                    "last_used_year": profile.last_used_year,
                }
            )

        # 2. Parse JD Requirements
        valid_requirements = []
        FILTER_KEYWORDS = [
            "technologies",
            "languages",
            "requirements",
            "tools",
            "stack",
            "category",
            "alternative",
            "development",
            "communication",
            "teamwork",
            "management",
            "problem solving",
        ]

        for r_src in requirements_source:
            req = self._parse_requirement(r_src)
            item_name = req.get("skill_name", "").lower()
            if (
                any(kw in item_name for kw in FILTER_KEYWORDS)
                and len(item_name.split()) < 4
            ):
                continue
            valid_requirements.append(req)

        # 3. Gọi Thuật toán Advanced Engine (Tầng 1 & Tầng 2 & Tầng 3)
        res = await self.advanced_engine.calculate_match(
            user_skills_data, valid_requirements
        )

        # 4. Map kết quả về định dạng cũ để Frontend không break
        results = {
            "overall_match_pct": res["overall_match_pct"],
            "breakdown": res["breakdown"],
            "recommendations": [],
            "notes": [
                f"Calculation Method: Advanced 3-Tier Algorithm ({len(valid_requirements)} items)"
            ],
        }

        # Tạo recommendations từ breakdown
        for it in res["breakdown"]["partial"]:
            results["recommendations"].append(
                {"skill": it["skill"], "type": "PARTIAL", "target_level": "Mid-level"}
            )
        for it in res["breakdown"]["gap"]:
            results["recommendations"].append(
                {"skill": it["skill"], "type": "MISSING", "target_level": "Mid-level"}
            )

        return results

    async def infer_market_requirements_for_cv(self, cv_id: str) -> list:
        """
        Fallback khi không có JD: LLM suy luận market standard requirements
        dựa trên primary role và skills của CV.
        """
        logger.info(f"Inferring market requirements for CV: {cv_id}")
        try:
            # Reset any aborted transaction before querying
            try:
                self.db.rollback()
            except Exception:
                pass

            # Lấy thông tin CV
            cv = (
                self.db.query(UserCV).filter(UserCV.id == uuid.UUID(str(cv_id))).first()
            )
            if not cv:
                return []

            # Lấy top skills
            skill_rows = (
                self.db.query(UserSkillProfile, Skill.name)
                .join(Skill)
                .filter(UserSkillProfile.cv_id == uuid.UUID(str(cv_id)))
                .order_by(UserSkillProfile.years_exp.desc())
                .limit(10)
                .all()
            )

            top_skills = [name for _, name in skill_rows]
            primary_role = cv.summary or "Software Developer"

            if not top_skills:
                return []

            from shared.llm_utils import get_chat_completion

            prompt = f"""Bạn là chuyên gia tuyển dụng kỹ thuật.
Một ứng viên có profile sau:
- Vai trò: {primary_role[:200]}
- Kỹ năng chính: {", ".join(top_skills)}

Hãy liệt kê 8-12 kỹ năng kỹ thuật mà một JD tiêu chuẩn cho vị trí này thường yêu cầu.

Trả về JSON:
{{"requirements": [
  {{"type": "skill", "skill": "Python", "target_level": "Mid-level", "years_required": 2, "is_primary": true, "importance_weight": 8}},
  ...
]}}

Chỉ trả về JSON hợp lệ."""

            raw = get_chat_completion(prompt, json_mode=True)
            if raw:
                import json

                data = json.loads(raw)
                reqs = data.get("requirements", [])
                logger.info(f"Inferred {len(reqs)} market requirements for CV {cv_id}")
                return reqs
        except Exception as e:
            logger.error(f"infer_market_requirements_for_cv error: {e}")
        return []

    # [COMMENTED OUT OLD V6.0 CALCULATION LOGIC]
    # async def calculate_gap_v2_legacy(self, user_id: str, cv_id: str, requirements_source: Any):
    #     logger.info(f"=== Starting Engine V6.0 (Modular & Seniority-Free) CV: {cv_id} ===")
    #
    #     user_skills_query = self.db.query(UserSkillProfile, Skill.name).join(Skill).filter(UserSkillProfile.cv_id == uuid.UUID(cv_id)).all()
    #     user_skill_map = {self._normalize_name(s_name): {"level": usp.level, "years": usp.years_exp} for usp, s_name in user_skills_query}
    #     user_skills_list = [s_name for _, s_name in user_skills_query]
    #
    #     results = {
    #         "overall_match_pct": 0,
    #         "breakdown": {"met": [], "gap": [], "partial": []},
    #         "recommendations": [],
    #         "notes": []
    #     }
    #
    #     if not requirements_source: return results
    #
    #     weighted_score_sum = 0.0
    #     total_weight_sum = 0.0
    #
    #     FILTER_KEYWORDS = ["technologies", "languages", "requirements", "tools", "stack", "category", "alternative",
    #                        "development", "communication", "teamwork", "management", "problem solving"]
    #
    #     valid_requirements = []
    #     for r_src in requirements_source:
    #         req = self._parse_requirement(r_src)
    #         item_name = req.get("skill_name", "").lower()
    #
    #         if any(kw in item_name for kw in FILTER_KEYWORDS) and len(item_name.split()) < 4:
    #             logger.info(f"FILTERING OUT GENERIC REPLACEMENT: {item_name}")
    #             continue
    #
    #         valid_requirements.append(req)
    #
    #     requirement_count = len(valid_requirements)
    #
    #     for req in valid_requirements:
    #         is_group = req.get("type") == "group" or "skills" in req
    #         is_mandatory = req.get("is_mandatory", True)
    #
    #         item_weight = 10.0 if is_mandatory else 3.0
    #
    #         if not is_group:
    #             eval_res = await self.matcher.match_skill(req, user_skill_map, user_skills_list)
    #             final_score = eval_res["score"]
    #             item_name = eval_res["skill"]
    #         else:
    #             ... [Old logic for groups] ...
    #
    #         total_weight_sum += item_weight
    #         weighted_score_sum += (final_score * item_weight)
    #
    #         if eval_res.get("match_found"):
    #             category = "met" if final_score >= 0.85 else "partial"
    #             results["breakdown"][category].append({**eval_res, "is_mandatory": is_mandatory, "score": round(final_score*100, 1)})
    #             if category == "partial":
    #                 results["recommendations"].append({"skill": eval_res["skill"], "type": "PARTIAL", "target_level": eval_res["details"].get("required_level", "Mid-level")})
    #         else:
    #             results["breakdown"]["gap"].append({"skill": item_name, "is_mandatory": is_mandatory, "gap_type": "MISSING", "score": 0})
    #             results["recommendations"].append({"skill": item_name, "type": "MISSING", "target_level": "Mid-level"})
    #
    #     results["overall_match_pct"] = self.scorer.calculate_overall_score(weighted_score_sum, total_weight_sum)
    #     results["notes"].append(f"Calculation Method: Strict Weighted Technical Match ({requirement_count} items)")
    #
    #     return results
    def _parse_requirement(self, r_src: Any) -> Dict[str, Any]:
        if hasattr(r_src, "__dict__") and not isinstance(r_src, dict):
            return {
                "type": getattr(r_src, "type", "skill"),
                "skill_name": r_src.skill.name
                if (hasattr(r_src, "skill") and r_src.skill)
                else "Unknown",
                "importance_weight": getattr(r_src, "importance_weight", 5),
                "required_level": getattr(r_src, "required_level", "intermediate"),
                "years_required": getattr(r_src, "min_years_exp", 0),
                "is_mandatory": getattr(r_src, "is_mandatory", True),
            }
        req = dict(r_src)
        if "skill_name" not in req:
            req["skill_name"] = req.get("skill") or req.get("group_name") or "Unknown"
        if "required_level" not in req:
            req["required_level"] = req.get("target_level", "intermediate")
        if "is_mandatory" not in req:
            # Default to True if neither is_mandatory nor is_primary exists or if is_primary is True
            req["is_mandatory"] = req.get("is_primary", True)
        if "importance_weight" not in req:
            req["importance_weight"] = 5
        return req
