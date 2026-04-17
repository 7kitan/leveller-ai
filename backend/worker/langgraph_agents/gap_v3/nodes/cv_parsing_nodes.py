"""
gap_v3 nodes: CV Parsing Pipeline (Pipeline 1).
5 nodes: extract_text → llm_parse → normalize → pii_mask → persist.
"""

import uuid
import os
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
    STEP 1: Extract raw text từ CV file.
    Strategy:
      1. Nếu DB đã có raw_text (> 100 chars) → dùng cache, skip extraction
      2. Dùng pymupdf đọc text thuần từ PDF
      3. Nếu text < 200 chars → OCR fallback via pdf2image
    """
    cv_id_str = state["cv_id"]
    db = state["db"]

    logger.info(
        f"\n{'─' * 50}\n"
        f"[STEP 1] extract_text_node | cv_id={cv_id_str}\n"
        f"  DB session : {db}"
    )

    # ── Validate cv_id ───────────────────────────────────────────────────────
    try:
        cv_uuid = uuid.UUID(cv_id_str)
        logger.info(f"[STEP 1] cv_id valid UUID: {cv_uuid}")
    except ValueError as e:
        logger.error(f"[STEP 1] INVALID cv_id={cv_id_str}: {e}")
        return {**state, "error": f"Invalid cv_id: {cv_id_str}", "status": "failed"}

    # ── Load CV record ───────────────────────────────────────────────────────
    cv_record = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
    if not cv_record:
        logger.error(f"[STEP 1] CV record NOT FOUND in DB: cv_id={cv_id_str}")
        return {**state, "error": f"CV not found: {cv_id_str}", "status": "failed"}
    logger.info(
        f"[STEP 1] CV record found | file_id={cv_record.file_id} | "
        f"file_hash={cv_record.file_hash[:8] if cv_record.file_hash else 'N/A'}... | "
        f"existing raw_text len={len(cv_record.raw_text or '')}"
    )

    # ── Cache hit: raw_text đã có trong DB ──────────────────────────────────
    if cv_record.raw_text and len(cv_record.raw_text) > 100:
        logger.info(
            f"[STEP 1] ✓ CACHE HIT — using existing raw_text "
            f"({len(cv_record.raw_text)} chars) | is_ocr={getattr(cv_record, 'is_ocr', False)}"
        )
        return {
            **state,
            "raw_text": cv_record.raw_text,
            "is_ocr": getattr(cv_record, "is_ocr", False),
            "status": "text_extracted",
        }

    logger.info("[STEP 1] CACHE MISS — extracting text from file...")

    # ── Locate CV file on disk ───────────────────────────────────────────────
    try:
        import fitz  # pymupdf

        file_id = getattr(cv_record, "file_id", None) or cv_id_str
        file_ext = getattr(cv_record, "file_ext", None) or "pdf"
        upload_dir = os.getenv("CV_UPLOAD_DIR", "/app/data/cv_uploads")
        file_path = os.path.join(upload_dir, f"{file_id}.{file_ext}")

        logger.info(
            f"[STEP 1] Resolving file path:\n"
            f"  upload_dir={upload_dir}\n"
            f"  file_id={file_id} | file_ext={file_ext}\n"
            f"  resolved_path={file_path}"
        )

        if not os.path.exists(file_path):
            logger.error(f"[STEP 1] FILE NOT FOUND on disk: {file_path}")
            # Fallback: try original cv_id as filename
            fallback_path = os.path.join(upload_dir, f"{cv_id_str}.pdf")
            if os.path.exists(fallback_path):
                file_path = fallback_path
                logger.info(f"[STEP 1] ✓ Found via fallback path: {file_path}")
            else:
                logger.error(f"[STEP 1] FALLBACK ALSO MISSING: {fallback_path}")
                return {
                    **state,
                    "error": f"CV file not found at {file_path} (fallback also missing)",
                    "status": "failed",
                }

        file_size = os.path.getsize(file_path)
        logger.info(f"[STEP 1] File found | size={file_size:,} bytes")

    except ImportError as ie:
        logger.error(f"[STEP 1] pymupdf (fitz) not installed: {ie}")
        return {
            **state,
            "error": f"Dependency missing: pymupdf — {ie}",
            "status": "failed",
        }
    except Exception as e:
        logger.error(f"[STEP 1] Error locating file: {e}", exc_info=True)
        return {**state, "error": f"Error locating CV file: {e}", "status": "failed"}

    # ── Extract text via pymupdf ──────────────────────────────────────────────
    try:
        doc = fitz.open(file_path)
        num_pages = len(doc)
        logger.info(f"[STEP 1] Opening PDF with pymupdf | pages={num_pages}")

        text_pages = []
        for page_num in range(num_pages):
            page = doc[page_num]
            text = page.get_text("text")
            text_len = len(text.strip()) if text else 0
            logger.info(
                f"  page {page_num + 1}/{num_pages}: {text_len} chars extracted"
            )
            if text and text_len > 50:
                text_pages.append(text)

        doc.close()
        raw_text = "\n\n".join(text_pages)

        logger.info(
            f"[STEP 1] Text extraction complete:\n"
            f"  pages with text  : {len(text_pages)}/{num_pages}\n"
            f"  total raw_text   : {len(raw_text)} chars\n"
            f"  first 120 chars  : {repr(raw_text[:120])}"
        )

    except Exception as e:
        logger.error(f"[STEP 1] pymupdf extraction error: {e}", exc_info=True)
        return {**state, "error": f"pymupdf extraction failed: {e}", "status": "failed"}

    # ── OCR fallback: text too short → scan pages ────────────────────────────
    is_ocr = False
    if len(raw_text.strip()) < 200:
        logger.warning(
            f"[STEP 1] ⚠ LOW TEXT YIELD ({len(raw_text)} chars < 200) — "
            f"attempting OCR fallback..."
        )
        try:
            import pdf2image

            dpi = int(os.getenv("OCR_DPI", "200"))
            logger.info(f"[STEP 1] pdf2image converting at dpi={dpi} ...")

            images = pdf2image.convert_from_path(file_path, dpi=dpi)
            logger.info(f"[STEP 1] Converted {len(images)} images from PDF pages")

            ocr_parts = []
            for idx, img in enumerate(images, 1):
                ocr_parts.append(f"[OCR PAGE {idx}: size={img.size}]")
                logger.info(f"  page {idx}: {img.size[0]}x{img.size[1]} px")

            raw_text = "\n\n".join(ocr_parts) + "\n\n" + raw_text
            is_ocr = True
            logger.info(
                f"[STEP 1] OCR fallback applied | is_ocr=True | "
                f"final text length={len(raw_text)} chars"
            )

        except ImportError:
            logger.warning("[STEP 1] pdf2image not installed — skipping OCR fallback")
        except Exception as ocr_err:
            logger.warning(
                f"[STEP 1] OCR fallback failed (continuing with partial text): {ocr_err}"
            )

    # ── Validate result ───────────────────────────────────────────────────────
    if not raw_text.strip():
        logger.error(f"[STEP 1] ✗ FAIL — CV file is empty or unreadable: {file_path}")
        return {
            **state,
            "error": f"CV file is empty or unreadable: {file_path}",
            "status": "failed",
        }

    logger.info(
        f"[STEP 1] ✓ SUCCESS | is_ocr={is_ocr} | "
        f"extracted={len(raw_text)} chars | cv_id={cv_id_str}\n"
        f"{'─' * 50}"
    )
    return {
        **state,
        "raw_text": raw_text,
        "is_ocr": is_ocr,
        "status": "text_extracted",
    }


# ─── Node 2: LLM Structured Parsing ────────────────────────────────────


async def llm_parse_cv_node(state: CVParsingState) -> CVParsingState:
    """
    STEP 2: LLM Structured Parsing.
    Dùng OpenAI GPT parse raw_text → structured CVParsedData.
    PII được mask trước khi gửi LLM.
    """
    cv_id_str = state["cv_id"]
    raw_text = state.get("raw_text", "")
    is_ocr = state.get("is_ocr", False)

    logger.info(
        f"\n{'─' * 50}\n"
        f"[STEP 2] llm_parse_cv_node | cv_id={cv_id_str}\n"
        f"  raw_text length : {len(raw_text)} chars\n"
        f"  is_ocr          : {is_ocr}\n"
        f"  text preview    : {repr(raw_text[:200])}"
    )

    if not raw_text or len(raw_text) < 50:
        logger.error(
            f"[STEP 2] ✗ FAIL — raw_text too short ({len(raw_text)} chars < 50)"
        )
        return {**state, "error": "Raw text too short or empty", "status": "failed"}

    # ── PII Masking ───────────────────────────────────────────────────────────
    logger.info("[STEP 2] Masking PII before sending to LLM...")
    masked_text = mask_pii(raw_text)
    logger.info(
        f"[STEP 2] PII masked | before={len(raw_text)} chars | "
        f"after={len(masked_text)} chars"
    )

    # ── Build prompt ──────────────────────────────────────────────────────────
    prompt = f"""
    Parse the CV text below into a structured JSON format. Translate all summaries and descriptions into English.

    ## CV TEXT:
    {masked_text}

    ## RULES:
    1. EXHAUSTIVE: Extract all work history, skills, and education.
    2. ENGLISH: All descriptions and summaries must be in English.
    3. SKILLS: Extract skill name, category, and total years of experience. Do not perform deep level analysis.
    4. EXPERIENCE: Calculate total years of experience accurately.

    ## OUTPUT SCHEMA:
    {{
      "full_name": "Full Name",
      "summary": "Professional summary in English",
      "seniority": "Junior | Mid-level | Senior | Lead",
      "experience_years_total": 0.0,
      "skills": [
        {{
          "name": "Skill Name",
          "category": "Technology | Tool | etc.",
          "experience_years": 0.0
        }}
      ],
      "work_history": [
        {{
          "position": "Title",
          "company": "Company Name",
          "duration_years": 0.0,
          "description": "Short description in English",
          "skills_used": ["Skill A", "Skill B"]
        }}
      ],
      "education": [
        {{
          "degree": "...",
          "institution": "...",
          "year": 2024
        }}
      ],
      "certifications": ["Cert A", "Cert B"],
      "ocr_confidence": 0.0
    }}

    IMPORTANT: Return ONLY valid JSON.
    """

    # ── LLM call ───────────────────────────────────────────────────────────────
    from ..utils.llm_helpers import LLM_MODEL

    logger.info(
        f"[STEP 2] Calling LLM: model={LLM_MODEL} | "
        f"input chars={len(prompt)} | is_ocr={is_ocr}"
    )
    t_llm = __import__("time").monotonic()
    result = await llm_json_completion(prompt, context=f"is_ocr={is_ocr}")
    elapsed_llm = __import__("time").monotonic() - t_llm
    logger.info(
        f"[STEP 2] LLM returned in {elapsed_llm:.1f}s | result keys={list(result.keys()) if result else 'EMPTY'}"
    )

    if not result:
        logger.error(
            f"[STEP 2] ✗ FAIL — LLM returned empty result after {elapsed_llm:.1f}s\n"
            f"  is_ocr={is_ocr} | raw_text chars={len(raw_text)}"
        )
        return {
            **state,
            "error": f"LLM parsing returned empty result (took {elapsed_llm:.1f}s)",
            "status": "failed",
        }

    # ── Build CVParsedData ────────────────────────────────────────────────────
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
    edu_count = len(parsed.get("education", []))
    cert_count = len(parsed.get("certifications", []))

    logger.info(
        f"[STEP 2] ✓ SUCCESS\n"
        f"  full_name       : {parsed['full_name']}\n"
        f"  seniority       : {parsed['seniority']}\n"
        f"  experience_yrs  : {parsed['experience_years_total']}\n"
        f"  skills          : {skill_count} entries\n"
        f"  work_history    : {work_count} entries\n"
        f"  education       : {edu_count} entries\n"
        f"  certifications  : {cert_count} entries\n"
        f"  is_ocr          : {is_ocr}\n"
        f"  ocr_confidence  : {parsed['ocr_confidence']:.2f}\n"
        f"  LLM elapsed     : {elapsed_llm:.1f}s\n"
        f"{'─' * 50}"
    )

    return {**state, "cv_parsed": parsed, "status": "parsed"}


# ─── Node 3: Normalize + Validate ───────────────────────────────────────


async def normalize_cv_node(state: CVParsingState) -> CVParsingState:
    """
    STEP 3: Normalize + Validate parsed CV data.
    - Deduplicate skill names
    - Normalize skill levels
    - Normalize seniority labels
    - Clamp experience years to non-negative
    """
    cv_id_str = state["cv_id"]
    cv_parsed = state.get("cv_parsed")

    logger.info(
        f"\n{'─' * 50}\n"
        f"[STEP 3] normalize_cv_node | cv_id={cv_id_str}\n"
        f"  cv_parsed keys : {list(cv_parsed.keys()) if cv_parsed else 'None'}"
    )

    if not cv_parsed:
        logger.error(f"[STEP 3] ✗ FAIL — cv_parsed is None/empty")
        return {**state, "status": "failed", "error": "No parsed CV data"}

    # ── Normalize Skills ──────────────────────────────────────────────────────
    level_map = {
        "beginner": "Junior",
        "intermediate": "Mid-level",
        "mid": "Mid-level",
        "advanced": "Senior",
        "expert": "Expert",
        "senior": "Senior",
        "junior": "Junior",
    }
    seniority_map = {
        "junior": "Junior",
        "mid": "Mid-level",
        "mid-level": "Mid-level",
        "senior": "Senior",
        "expert": "Expert",
    }

    normalized_skills = []
    seen_names: set = set()
    skill_dedup_count = 0

    for idx, skill in enumerate(cv_parsed.get("skills", [])):
        raw_name = (skill.get("name") or "").strip()
        if not raw_name:
            logger.debug(f"  skill[{idx}] skipped: empty name")
            continue

        name_lower = raw_name.lower()
        if name_lower in seen_names:
            skill_dedup_count += 1
            logger.debug(f"  skill[{idx}] deduplicated: '{raw_name}'")
            continue

        raw_level = (skill.get("level") or "Junior").lower().strip()
        normalized = level_map.get(raw_level, "Junior")

        normalized_skills.append(
            {
                "name": raw_name,
                "category": skill.get("category") or "Technology",
                "experience_years": max(0.0, float(skill.get("experience_years") or 0)),
                "level": normalized,
            }
        )
        seen_names.add(name_lower)
        logger.debug(
            f"  skill[{idx}] kept: name='{raw_name}' | "
            f"level='{skill.get('level')}' → '{normalized}' | "
            f"yrs_exp={skill.get('experience_years', 0)}"
        )

    cv_parsed["skills"] = normalized_skills

    # ── Normalize Seniority ───────────────────────────────────────────────────
    raw_senior = (cv_parsed.get("seniority") or "Unknown").lower().strip()
    final_senior = seniority_map.get(raw_senior, raw_senior.title())
    cv_parsed["seniority"] = final_senior
    logger.info(f"[STEP 3] Seniority: '{raw_senior}' → '{final_senior}'")

    # ── Clamp Experience Years ────────────────────────────────────────────────
    raw_exp = float(cv_parsed.get("experience_years_total") or 0)
    cv_parsed["experience_years_total"] = max(0.0, raw_exp)

    # ── Log Summary ──────────────────────────────────────────────────────────
    logger.info(
        f"[STEP 3] ✓ COMPLETE\n"
        f"  skills before dedup : {len(state['cv_parsed'].get('skills', []))}\n"
        f"  skills deduplicated : {skill_dedup_count}\n"
        f"  skills after norm   : {len(normalized_skills)}\n"
        f"  seniority           : {final_senior}\n"
        f"  experience_yrs      : {cv_parsed['experience_years_total']}\n"
        f"{'─' * 50}"
    )

    return {**state, "cv_parsed": cv_parsed, "status": "normalized"}


# ─── Node 4: Persist to DB ──────────────────────────────────────────────


async def persist_cv_data_node(state: CVParsingState) -> CVParsingState:
    """
    STEP 4: Persist parsed CV data to DB.
    - Update user_cvs: cv_parsed_json, full_name, summary, experience_years_total, status=completed
    - Upsert skills → skills + user_skill_profile tables
    """
    cv_id_str = state["cv_id"]
    cv_parsed: CVParsedData = state.get("cv_parsed")
    db = state["db"]

    logger.info(
        f"\n{'─' * 50}\n"
        f"[STEP 4] persist_cv_data_node | cv_id={cv_id_str}\n"
        f"  cv_parsed available: {bool(cv_parsed)}"
    )

    if not cv_parsed:
        logger.error(f"[STEP 4] ✗ FAIL — cv_parsed is None")
        return {**state, "status": "failed", "error": "No CV parsed data to persist"}

    # ── Validate cv_id ───────────────────────────────────────────────────────
    try:
        cv_uuid = uuid.UUID(cv_id_str)
    except ValueError as e:
        logger.error(f"[STEP 4] ✗ FAIL — invalid cv_id: {e}")
        return {**state, "status": "failed", "error": f"Invalid cv_id: {cv_id_str}"}

    # ── Load CV record ───────────────────────────────────────────────────────
    try:
        cv_record = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
        if not cv_record:
            logger.error(f"[STEP 4] ✗ FAIL — CV record not found in DB for {cv_id_str}")
            return {**state, "status": "failed", "error": "CV record not found in DB"}
        logger.info(
            f"[STEP 4] CV record loaded | current status={cv_record.status} | "
            f"user_id={cv_record.user_id}"
        )
    except Exception as e:
        logger.error(f"[STEP 4] DB query failed: {e}", exc_info=True)
        return {**state, "status": "failed", "error": f"DB query failed: {e}"}

    from datetime import datetime

    try:
        # ── Update CV fields ──────────────────────────────────────────────────
        logger.info(
            f"[STEP 4] Updating UserCV fields:\n"
            f"  full_name           : {cv_parsed.get('full_name', '')[:50]}\n"
            f"  summary             : {(cv_parsed.get('summary') or '')[:80]}...\n"
            f"  experience_yrs      : {cv_parsed.get('experience_years_total')}\n"
            f"  seniority           : {cv_parsed.get('seniority')}\n"
            f"  skills count        : {len(cv_parsed.get('skills', []))}\n"
            f"  work_history count  : {len(cv_parsed.get('work_history', []))}\n"
            f"  education count     : {len(cv_parsed.get('education', []))}\n"
            f"  certifications      : {len(cv_parsed.get('certifications', []))}\n"
            f"  is_ocr              : {cv_parsed.get('is_ocr')}\n"
            f"  ocr_confidence      : {cv_parsed.get('ocr_confidence', 0):.2f}"
        )

        cv_record.cv_parsed_json = cv_parsed
        cv_record.cv_parsed_at = datetime.now()
        cv_record.experience_years_total = cv_parsed.get("experience_years_total", 0)
        cv_record.summary = cv_parsed.get("summary", "")
        cv_record.full_name = cv_parsed.get("full_name", "")
        cv_record.status = "completed"

        # Persist raw_text back to DB for cache hit on future parses
        if state.get("raw_text"):
            cv_record.raw_text = state["raw_text"]
            logger.info(
                f"[STEP 4] Cached raw_text ({len(state['raw_text'])} chars) in DB"
            )

        # ── Upsert Skills ────────────────────────────────────────────────────
        skills_upserted = await _upsert_skills_from_cv(
            cv_parsed.get("skills", []), cv_id_str, db
        )

        # ── Commit ───────────────────────────────────────────────────────────
        db.commit()
        logger.info(
            f"[STEP 4] ✓ DB COMMIT successful | cv_id={cv_id_str}\n"
            f"  skills upserted : {skills_upserted}\n"
            f"  status          : 'completed'\n"
            f"{'─' * 50}"
        )

        return {**state, "status": "persisted"}

    except Exception as e:
        db.rollback()
        logger.error(
            f"[STEP 4] ✗ FAIL — commit failed, rolled back: {e}", exc_info=True
        )
        return {**state, "status": "failed", "error": str(e)}


# ─── Helper: Upsert Skills ───────────────────────────────────────────────


async def _upsert_skills_from_cv(skills: list, cv_id: str, db) -> int:
    """
    Upsert skills từ parsed CV vào skills + user_skill_profile tables.
    Trả về số skills đã upsert.
    """
    from shared.models import Skill, UserSkillProfile

    upserted_count = 0
    skipped_count = 0
    error_count = 0
    cv_uuid = uuid.UUID(cv_id)

    logger.info(
        f"[STEP 4/SKILLS] Starting skill upsert | cv_id={cv_id} | "
        f"incoming skills={len(skills)}"
    )

    for idx, s in enumerate(skills):
        skill_name = (s.get("name") or "").strip()
        if not skill_name:
            skipped_count += 1
            logger.debug(f"  skill[{idx}] SKIPPED — empty name")
            continue

        # ── Upsert Skill record ──────────────────────────────────────────
        skill_record = db.query(Skill).filter(Skill.name == skill_name).first()

        if not skill_record:
            skill_record = Skill(
                id=uuid.uuid4(), name=skill_name, category="Technology"
            )
            db.add(skill_record)
            db.flush()
            logger.debug(
                f"  skill[{idx}] CREATED new Skill: id={skill_record.id} name='{skill_name}'"
            )
        else:
            logger.debug(
                f"  skill[{idx}] REUSED existing Skill: id={skill_record.id} name='{skill_name}'"
            )

        # ── Upsert UserSkillProfile ───────────────────────────────────────
        existing_profile = (
            db.query(UserSkillProfile)
            .filter(
                UserSkillProfile.cv_id == cv_uuid,
                UserSkillProfile.skill_id == skill_record.id,
            )
            .first()
        )

        profile_data = {
            "years_exp": max(0.0, float(s.get("experience_years") or 0)),
            "level": s.get("level", "Mid-level"),
            "source": "cv_parsed_v3",
        }

        if existing_profile:
            for key, val in profile_data.items():
                setattr(existing_profile, key, val)
            logger.debug(
                f"  skill[{idx}] UPDATED UserSkillProfile: "
                f"years_exp={profile_data['years_exp']} level={profile_data['level']}"
            )
        else:
            new_profile = UserSkillProfile(
                id=uuid.uuid4(),
                skill_id=skill_record.id,
                cv_id=cv_uuid,
                **profile_data,
            )
            db.add(new_profile)
            logger.debug(
                f"  skill[{idx}] INSERTED UserSkillProfile: "
                f"years_exp={profile_data['years_exp']} level={profile_data['level']}"
            )

        upserted_count += 1
        logger.debug(f"  skill[{idx}] ✓ upserted: name='{skill_name}'")

    logger.info(
        f"[STEP 4/SKILLS] Skill upsert complete | cv_id={cv_id}\n"
        f"  total incoming : {len(skills)}\n"
        f"  upserted       : {upserted_count}\n"
        f"  skipped (empty): {skipped_count}"
    )

    return upserted_count
