"""
gap_v3 nodes: CV Parsing Pipeline (Pipeline 1).
5 nodes: extract_text → llm_parse → normalize → pii_mask → persist.
"""

import uuid
import logging
from typing import Dict, Any

from ..states import CVParsingState, CVParsedData
from ..utils.pii_masker import mask_pii, mask_work_history
from ..utils.llm_helpers import llm_json_completion
from shared.models import UserCV, UserSkillProfile, Skill

logger = logging.getLogger("cv_parsing_v3")


# ─── Node 1: Text Extraction ─────────────────────────────────────────────


async def extract_text_node(state: CVParsingState) -> CVParsingState:
    """
    Extract raw text từ CV file.
    Ưu tiên dùng hybrid strategy đã có.
    """
    db = state["db"]
    cv_id_str = state["cv_id"]

    try:
        cv_uuid = uuid.UUID(cv_id_str)
    except ValueError:
        return {**state, "error": f"Invalid cv_id: {cv_id_str}", "status": "failed"}

    cv_record = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
    if not cv_record:
        return {**state, "error": f"CV not found: {cv_id_str}", "status": "failed"}

    # Nếu đã có raw_text trong DB → dùng lại
    if cv_record.raw_text and len(cv_record.raw_text) > 100:
        logger.info(
            f"Using cached raw_text for CV {cv_id_str}: {len(cv_record.raw_text)} chars"
        )
        return {
            **state,
            "raw_text": cv_record.raw_text,
            "is_ocr": getattr(cv_record, "is_ocr", False),
            "status": "text_extracted",
        }

    # Gọi hybrid extraction
    try:
        from worker.tasks.cv_parsing_utils import extract_cv_hybrid

        file_path = getattr(cv_record, "file_path", None)

        if not file_path:
            return {**state, "error": "No file_path on CV record", "status": "failed"}

        result = await extract_cv_hybrid(file_path)

        return {
            **state,
            "raw_text": result.get("raw_text", ""),
            "is_ocr": result.get("is_ocr", False),
            "status": "text_extracted",
        }
    except Exception as e:
        logger.error(f"Text extraction failed for {cv_id_str}: {e}")
        return {**state, "error": str(e), "status": "failed"}


# ─── Node 2: LLM Structured Parsing ────────────────────────────────────


async def llm_parse_cv_node(state: CVParsingState) -> CVParsingState:
    """
    CORE: Dùng LLM parse raw text → structured CVParsedData.
    Đây là bước quan trọng nhất — tạo structured data để reuse.
    """
    raw_text = state.get("raw_text", "")
    is_ocr = state.get("is_ocr", False)

    if not raw_text or len(raw_text) < 50:
        return {**state, "error": "Raw text too short or empty", "status": "failed"}

    # PII mask trước khi gửi LLM
    masked_text = mask_pii(raw_text)

    prompt = f"""Parse CV sau thành JSON có cấu trúc.

## CV (PII đã mask):
{masked_text}

## Nguyên tắc:
1. Trích xuất TẤT CẢ kỹ năng KỸ THUẬT (lập trình, framework, tool, database, cloud, etc.)
2. Với mỗi kỹ năng: ghi rõ level (Beginner/Intermediate/Advanced/Expert), số năm kinh nghiệm
3. Work history: ghi rõ technologies/tools dùng tại mỗi vị trí
4. Nếu CV từ OCR (flag is_ocr=True): giảm confidence, đánh dấu thấp
5. Seniority: đoán dựa trên tổng năm kinh nghiệm + mô tả công việc

## Output JSON:
{{
  "full_name": "<tên đầy đủ, hoặc 'Không xác định'>",
  "summary": "<tóm tắt chuyên nghiệp 2-3 câu, dựa trên work history và skills>",
  "seniority": "Junior | Mid-level | Senior | Expert | Unknown",
  "experience_years_total": <số năm kinh nghiệm tổng (float)>,
  "skills": [
    {{
      "name": "<tên kỹ năng>",
      "level": "Beginner | Intermediate | Advanced | Expert",
      "years_exp": <số năm (float)>,
      "last_used": <năm gần nhất dùng, null nếu không biết>,
      "context": "<mô tả ngắn cách dùng, ví dụ: 'Used in 3 production Django projects'>"
    }}
  ],
  "work_history": [
    {{
      "position": "<tên vị trí>",
      "company": "<công ty (đã mask)>",
      "duration_years": <số năm (float)>,
      "description": "<mô tả công việc, dự án, technologies dùng (đã mask)>",
      "skills_used": ["<skill1>", "<skill2>"]
    }}
  ],
  "education": [
    {{
      "degree": "<bằng cấp>",
      "institution": "<trường>",
      "year": <năm tốt nghiệp>,
      "field": "<ngành>"
    }}
  ],
  "certifications": [
    {{
      "name": "<tên chứng chỉ>",
      "issuer": "<tổ chức cấp>",
      "year": <năm>
    }}
  ],
  "ocr_confidence": <0.0-1.0, đánh giá độ chính xác>
}}

CHỈ trả về JSON hợp lệ. Nếu CV không có thông tin, dùng null hoặc []. Nếu is_ocr=True, đặt ocr_confidence <= 0.8."""

    logger.info(f"LLM parsing CV {state['cv_id']}: {len(raw_text)} chars input")
    result = await llm_json_completion(prompt, context=f"is_ocr={is_ocr}")

    if not result:
        return {
            **state,
            "error": "LLM parsing returned empty result",
            "status": "failed",
        }

    parsed: CVParsedData = {
        "full_name": result.get("full_name") or "Không xác định",
        "summary": result.get("summary") or "",
        "seniority": result.get("seniority") or "Unknown",
        "experience_years_total": float(result.get("experience_years_total") or 0),
        "skills": result.get("skills") or [],
        "work_history": result.get("work_history") or [],
        "education": result.get("education") or [],
        "certifications": result.get("certifications") or [],
        "is_ocr": is_ocr,
        "ocr_confidence": float(
            result.get("ocr_confidence") or (0.6 if is_ocr else 1.0)
        ),
        "raw_text_masked": masked_text,
    }

    skill_count = len(parsed.get("skills", []))
    work_count = len(parsed.get("work_history", []))

    logger.info(
        f"  CV parsed: {parsed['full_name']} | "
        f"seniority={parsed['seniority']} | "
        f"skills={skill_count} | work_entries={work_count} | "
        f"ocr_conf={parsed['ocr_confidence']:.2f}"
    )

    return {**state, "cv_parsed": parsed, "status": "parsed"}


# ─── Node 3: Normalize + Validate ───────────────────────────────────────


async def normalize_cv_node(state: CVParsingState) -> CVParsingState:
    """
    Normalize skill names (lowercase, strip whitespace).
    Validate và fill missing fields.
    """
    cv_parsed = state.get("cv_parsed")
    if not cv_parsed:
        return {**state, "status": "failed", "error": "No parsed CV data"}

    # Normalize skill names
    normalized_skills = []
    seen_names = set()

    for skill in cv_parsed.get("skills", []):
        name = (skill.get("name") or "").strip()
        if not name or name.lower() in seen_names:
            continue

        # Normalize level
        level_map = {
            "beginner": "Junior",
            "intermediate": "Mid-level",
            "mid": "Mid-level",
            "advanced": "Senior",
            "expert": "Expert",
            "senior": "Senior",
            "junior": "Junior",
        }
        raw_level = (skill.get("level") or "Junior").lower().strip()
        level = level_map.get(raw_level, "Junior")

        normalized_skills.append(
            {
                "name": name,
                "level": level,
                "years_exp": max(0.0, float(skill.get("years_exp") or 0)),
                "last_used": skill.get("last_used"),
                "context": skill.get("context") or "",
            }
        )
        seen_names.add(name.lower())

    cv_parsed["skills"] = normalized_skills

    # Normalize seniority
    seniority_map = {
        "junior": "Junior",
        "mid-level": "Mid-level",
        "senior": "Senior",
        "expert": "Expert",
    }
    raw_senior = (cv_parsed.get("seniority") or "Unknown").lower().strip()
    cv_parsed["seniority"] = seniority_map.get(raw_senior, raw_senior.title())

    # Ensure positive experience
    cv_parsed["experience_years_total"] = max(
        0.0, float(cv_parsed.get("experience_years_total") or 0)
    )

    logger.info(f"  CV normalized: {len(normalized_skills)} unique skills")

    return {**state, "cv_parsed": cv_parsed, "status": "normalized"}


# ─── Node 4: Persist to DB ──────────────────────────────────────────────


async def persist_cv_data_node(state: CVParsingState) -> CVParsingState:
    """
    Lưu cv_parsed vào DB:
    1. Update user_cvs.cv_parsed_json
    2. Upsert skills vào skills + user_skill_profile tables
    """
    db = state["db"]
    cv_id_str = state["cv_id"]
    cv_parsed: CVParsedData = state.get("cv_parsed")

    if not cv_parsed:
        return {**state, "status": "failed", "error": "No CV parsed data to persist"}

    try:
        cv_uuid = uuid.UUID(cv_id_str)
    except ValueError:
        return {**state, "status": "failed", "error": f"Invalid cv_id: {cv_id_str}"}

    try:
        cv_record = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
        if not cv_record:
            return {**state, "status": "failed", "error": "CV record not found in DB"}

        from datetime import datetime

        # Update CV record
        cv_record.cv_parsed_json = cv_parsed
        cv_record.cv_parsed_at = datetime.now()
        cv_record.experience_years_total = cv_parsed.get("experience_years_total", 0)
        cv_record.summary = cv_parsed.get("summary", "")
        cv_record.full_name = cv_parsed.get("full_name", "")
        cv_record.status = "completed"

        # Upsert skills
        skills_upserted = await _upsert_skills_from_cv(
            cv_parsed.get("skills", []), cv_id_str, db
        )

        db.commit()

        logger.info(
            f"  CV persisted: {cv_id_str} | "
            f"{skills_upserted} skills upserted | "
            f"experience={cv_parsed.get('experience_years_total')} years"
        )

        return {**state, "status": "persisted"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist CV {cv_id_str}: {e}", exc_info=True)
        return {**state, "status": "failed", "error": str(e)}


# ─── Helper: Upsert Skills ───────────────────────────────────────────────


async def _upsert_skills_from_cv(skills: list, cv_id: str, db) -> int:
    """
    Upsert skills từ parsed CV vào skills + user_skill_profile tables.
    Trả về số skills đã upsert.
    """
    from datetime import datetime
    from shared.models import Skill, UserSkillProfile

    upserted_count = 0
    cv_uuid = uuid.UUID(cv_id)

    for s in skills:
        skill_name = (s.get("name") or "").strip()
        if not skill_name:
            continue

        try:
            # Upsert Skill record
            skill_record = db.query(Skill).filter(Skill.name == skill_name).first()

            if not skill_record:
                skill_record = Skill(
                    id=uuid.uuid4(), name=skill_name, category="Technology"
                )
                db.add(skill_record)
                db.flush()

            # Upsert UserSkillProfile
            existing_profile = (
                db.query(UserSkillProfile)
                .filter(
                    UserSkillProfile.cv_id == cv_uuid,
                    UserSkillProfile.skill_id == skill_record.id,
                )
                .first()
            )

            profile_data = {
                "years_exp": max(0.0, float(s.get("years_exp") or 0)),
                "level": s.get("level", "Junior"),
                "last_used_year": s.get("last_used"),
                "skill_context": s.get("context"),
                "source": "cv_parsed_v3",
            }

            if existing_profile:
                for key, val in profile_data.items():
                    setattr(existing_profile, key, val)
            else:
                new_profile = UserSkillProfile(
                    id=uuid.uuid4(),
                    skill_id=skill_record.id,
                    cv_id=cv_uuid,
                    **profile_data,
                )
                db.add(new_profile)

            upserted_count += 1

        except Exception as e:
            logger.warning(f"Failed to upsert skill '{skill_name}': {e}")
            continue

    db.commit()
    return upserted_count
