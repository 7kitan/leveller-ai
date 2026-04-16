"""
gap_v3 Gap Analysis Nodes (Pipeline 2):
- load_cv_parsed_data_node
- extract_jd_node
- gap_analysis_llm_node
"""

import json
import hashlib
import logging
from typing import Dict, Any, Optional

from ..states import GapAnalysisStateV3, GapAnalysisResult
from ..utils.llm_helpers import llm_json_completion

logger = logging.getLogger("gap_analysis_v3")


# ─── Node 1: Load CV Parsed Data ─────────────────────────────────────────


async def load_cv_parsed_data_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    Load CV parsed data từ DB (từ cv_parsed_json column).
    → Không cần re-parse CV mỗi lần.
    """
    db = state["db"]
    cv_id_str = state["cv_id"]

    try:
        import uuid
        from shared.models import UserCV

        cv_uuid = uuid.UUID(cv_id_str)
        cv_record = db.query(UserCV).filter(UserCV.id == cv_uuid).first()

        if not cv_record:
            return {**state, "error": f"CV not found: {cv_id_str}", "status": "failed"}

        parsed = getattr(cv_record, "cv_parsed_json", None)

        if not parsed:
            # Fallback: gọi CV parsing pipeline
            logger.warning(
                f"No cv_parsed_json found for {cv_id_str}. Triggering re-parse..."
            )
            parsed = await _run_cv_parsing_fallback(cv_id_str, state["user_id"], db)

        if not parsed:
            return {
                **state,
                "error": "CV not parsed and re-parse failed",
                "status": "failed",
            }

        skill_count = len(parsed.get("skills", []))
        work_count = len(parsed.get("work_history", []))

        logger.info(
            f"  CV loaded from DB: {cv_id_str} | "
            f"skills={skill_count} | work_entries={work_count}"
        )

        return {**state, "cv_parsed": parsed, "status": "cv_loaded"}

    except Exception as e:
        logger.error(f"load_cv_parsed_data_node failed: {e}", exc_info=True)
        return {**state, "error": str(e), "status": "failed"}


async def _run_cv_parsing_fallback(cv_id: str, user_id: str, db) -> Optional[dict]:
    """Fallback: gọi CV parsing pipeline nếu chưa có parsed data."""
    try:
        from ..cv_parsing_graph import run_cv_parsing_pipeline

        result = await run_cv_parsing_pipeline(cv_id=cv_id, user_id=user_id, db=db)
        return result.get("cv_parsed")
    except Exception as e:
        logger.error(f"CV re-parse fallback failed: {e}")
        return None


# ─── Node 2: Extract JD Requirements ──────────────────────────────────────


async def extract_jd_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    Extract JD requirements bằng LLM.
    Cache kết quả vào Redis (1 giờ).
    """
    from shared.redis_client import result_cache
    from ..config import JD_EXTRACT_CACHE_TTL

    jd_text = state.get("jd_text") or ""

    if not jd_text or len(jd_text) < 50:
        return {**state, "error": "JD text too short or empty", "status": "failed"}

    # Check cache
    text_hash = hashlib.md5(jd_text.encode()).hexdigest()[:16]
    cache_key = f"jd_extracted:{text_hash}"

    cached = result_cache.get(cache_key)
    if cached:
        try:
            jd_parsed = json.loads(cached)
            logger.info(f"  JD extract CACHE HIT: {cache_key}")
            return {
                **state,
                "jd_parsed": jd_parsed,
                "jd_requirements": jd_parsed.get("requirements", []),
                "status": "jd_extracted",
            }
        except Exception:
            pass

    # Build job context
    jd_context = state.get("jd_context", "")

    prompt = f"""Trích xuất yêu cầu kỹ năng từ JD sau.

## Job Description:
{jd_text}

## Quy tắc:
1. Chỉ trích xuất kỹ năng KỸ THUẬT (lập trình, framework, tool, database, cloud, DevOps, etc.)
2. Không trích xuất soft skills (communication, teamwork, problem solving, etc.)
3. Với mỗi skill: target_level, years_required, is_mandatory, importance_weight
4. Nếu JD nói "hiểu Docker" → level=Junior, years=0
5. Nếu JD nói "3 năm Kubernetes" → level=Mid-level, years=3
6. Group (VD: "Java or Kotlin") → type=group, strategy=OR
7. Weight: bắt buộc=8-10, tùy chọn=3-5

## Output JSON:
{{
  "job_title": "<tên vị trí>",
  "company_context": "<mô tả ngắn công ty/ngành nếu có, null nếu không>",
  "requirements": [
    {{
      "skill": "<tên skill>",
      "target_level": "Junior | Mid-level | Senior | Expert",
      "years_required": <số năm, 0 nếu không nói>,
      "is_mandatory": true|false,
      "importance_weight": <1-10>,
      "type": "skill | group",
      "group_skills": [<nếu type=group>],
      "group_strategy": "AND | OR"
    }}
  ],
  "overall_requirements_count": <tổng số skills>
}}

CHỈ trả về JSON hợp lệ."""

    logger.info(
        f"  JD extract LLM call: {len(jd_text)} chars → extracting requirements"
    )
    result = await llm_json_completion(prompt, context=jd_context)

    if not result:
        return {**state, "error": "JD extraction returned empty", "status": "failed"}

    jd_parsed = {
        "job_title": result.get("job_title") or jd_context,
        "company_context": result.get("company_context") or "",
        "requirements": result.get("requirements") or [],
        "overall_requirements_count": result.get("overall_requirements_count", 0),
    }

    # Cache
    try:
        result_cache.setex(cache_key, JD_EXTRACT_CACHE_TTL, json.dumps(jd_parsed))
        logger.info(
            f"  JD extracted: {jd_parsed['overall_requirements_count']} requirements, cached"
        )
    except Exception as e:
        logger.warning(f"JD cache write failed: {e}")

    return {
        **state,
        "jd_parsed": jd_parsed,
        "jd_requirements": jd_parsed["requirements"],
        "status": "jd_extracted",
    }


# ─── Node 3: Gap Analysis LLM (HOLISTIC) ────────────────────────────────


def _format_cv_for_llm(cv_parsed: dict) -> str:
    """Format structured CV parsed data thành text cho LLM."""
    skills = cv_parsed.get("skills", [])
    work_history = cv_parsed.get("work_history", [])
    education = cv_parsed.get("education", [])
    certs = cv_parsed.get("certifications", [])

    # Skills
    skills_lines = []
    for s in skills:
        level = s.get("level", "Unknown")
        years = s.get("years_exp", 0)
        ctx = s.get("context", "")
        skills_lines.append(
            f"  - {s['name']} | {level} | {years:.1f} năm"
            + (f" | {ctx}" if ctx else "")
        )
    skills_text = "\n".join(skills_lines) or "  (Không có kỹ năng)"

    # Work history
    work_lines = []
    for w in work_history:
        dur = w.get("duration_years", 0)
        skills_used = ", ".join(w.get("skills_used", [])[:8])
        desc = w.get("description", "")[:200]
        work_lines.append(
            f"  - [{dur:.1f} năm] {w.get('position', 'N/A')} @ {w.get('company', 'N/A')}\n"
            f"    {desc}\n"
            f"    Technologies: {skills_used or 'N/A'}"
        )
    work_text = "\n".join(work_lines) or "  (Không có kinh nghiệm)"

    # Education
    edu_lines = []
    for e in education:
        edu_lines.append(
            f"  - {e.get('degree', '')} - {e.get('field', '')} @ {e.get('institution', '')} ({e.get('year', '')})"
        )
    edu_text = "\n".join(edu_lines) or "  (Không có thông tin)"

    # Certifications
    cert_text = ""
    if certs:
        cert_lines = [
            f"  - {c.get('name', '')} ({c.get('issuer', '')}, {c.get('year', '')})"
            for c in certs
        ]
        cert_text = "\n## CHỨNG CHỈ\n" + "\n".join(cert_lines)

    seniority = cv_parsed.get("seniority", "Unknown")
    exp_total = cv_parsed.get("experience_years_total", 0)

    return f"""## TỔNG QUAN
Seniority: {seniority} | Tổng kinh nghiệm: {exp_total:.1f} năm
{cv_parsed.get("summary", "")}

## KỸ NĂNG KỸ THUẬT
{skills_text}

## KINH NGHIỆM LÀM VIỆC
{work_text}

## HỌC VẤN
{edu_text}
{cert_text}"""


def _format_jd_for_llm(jd_requirements: list) -> str:
    """Format JD requirements thành text cho LLM."""
    if not jd_requirements:
        return "  (Không có yêu cầu cụ thể)"

    lines = []
    for req in jd_requirements:
        mandatory_tag = "🔴 BẮT BUỘC" if req.get("is_mandatory") else "⚪ TÙY CHỌN"
        level = req.get("target_level", "Mid-level")
        years = req.get("years_required", 0)
        weight = req.get("importance_weight", 5)
        skill_name = req.get("skill") or req.get("group_name", "Unknown")

        if req.get("type") == "group":
            group_skills = ", ".join(
                [s.get("skill", "?") for s in req.get("group_skills", [])]
            )
            strategy = (
                "OR (ít nhất 1)"
                if req.get("group_strategy") == "OR"
                else "AND (tất cả)"
            )
            lines.append(
                f"  {mandatory_tag} GROUP [{strategy}]: {skill_name}\n"
                f"    Options: {group_skills} | Weight: {weight}"
            )
        else:
            year_str = f" | {years} năm kinh nghiệm" if years else ""
            lines.append(
                f"  {mandatory_tag} {skill_name} | {level}{year_str} | Weight: {weight}"
            )

    return "\n".join(lines)


async def gap_analysis_llm_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    CORE — LLM tính gap TỔNG QUAN từ FULL context.

    Điểm khác biệt cốt lõi:
    → Không chia nhỏ từng skill
    → Đưa TOÀN BỘ CV + TOÀN BỘ JD vào 1 LLM call
    → LLM suy luận holistic về sự phù hợp tổng thể
    """
    logger.info("--- [GAP v3] HOLISTIC GAP ANALYSIS NODE ---")

    cv_parsed = state.get("cv_parsed")
    jd_requirements = state.get("jd_requirements", [])
    jd_context = state.get("jd_context") or (
        state.get("jd_parsed", {}).get("job_title") if state.get("jd_parsed") else ""
    )

    if not cv_parsed:
        return {**state, "error": "No CV parsed data", "status": "failed"}
    if not jd_requirements:
        return {**state, "error": "No JD requirements", "status": "failed"}

    # Format context
    cv_formatted = _format_cv_for_llm(cv_parsed)
    jd_formatted = _format_jd_for_llm(jd_requirements)

    system_prompt = """Bạn là chuyên gia phân tích sự phù hợp nghề nghiệp cấp cao.
Nguyên tắc:
1. Đánh giá DỰA TRÊN NGỮ CẢNH TOÀN CỤC — không chỉ liệt kê skill đơn lẻ
2. Nhận diện "transferable skills" một cách TỰ NHIÊN: VD: Python 5 năm → học FastAPI trong 2-4 tuần
3. Phân biệt GAP "thực sự" (cần học dài hạn) vs GAP "mềm" (có nền tảng, học nhanh)
4. Severity đánh theo: job impact × learning effort × market demand
5. Đưa ra learning path CỤ THỂ: tên tool/khóa học cụ thể
6. Nếu CV có is_ocr=True (OCR confidence thấp): thận trọng hơn với kết luận
7. Luôn viết bằng tiếng Việt."""

    user_prompt = f"""## ===== HỒ SƠ ỨNG VIÊN (PARSED) =====
{cv_formatted}

## ===== YÊU CẦU CÔNG VIỆC =====
{jd_formatted}

## ===== NHIỆM VỤ =====
Phân tích toàn diện sự phù hợp và đưa ra JSON:

{{
  "overall_match_pct": <0-100, đánh giá TỔNG THỂ dựa trên ngữ cảnh>,
  "overall_assessment": "<nhận xét tổng thể 2-3 câu, dựa trên ngữ cảnh thực tế, có con số cụ thể>",

  "strengths": [
    "<điểm mạnh cụ thể dựa trên work history + seniority, có bằng chứng>"
  ],
  "weaknesses": [
    "<điểm yếu cụ thể, có giải thích tại sao là yếu tố cản trở>"
  ],

  "skill_gaps": [
    {{
      "skill": "<tên skill>",
      "severity": "HIGH | MEDIUM | LOW",
      "is_critical": true|false,
      "status": "GAP | PARTIAL",
      "current_level": "<level hiện tại của user, null nếu không có>",
      "required_level": "<level JD yêu cầu>",
      "years_gap": <số năm thiếu, 0 nếu không có kinh nghiệm>,
      "bridge_from": "<skill đã có mà có thể chuyển đổi, null nếu không có>",
      "learning_effort": "EASY (<1 tháng) | MEDIUM (1-3 tháng) | HARD (3-6 tháng) | EXPERT (>6 tháng)",
      "estimated_months": <số tháng học realistic (float)>,
      "learning_path": "<lộ trình cụ thể, VD: Docker basics → K8s intro → K8s advanced>"
    }}
  ],

  "gap_summary": {{
    "total_gaps": <số>,
    "critical_gaps": <số severity HIGH>,
    "soft_gaps": <số severity MEDIUM/LOW có bridge skill>,
    "estimated_total_months": <tổng tháng học tất cả gaps (float)>,
    "blocking_skills": ["<skill nghiêm trọng nhất, không học thì không được nhận, null nếu không có>"]
  }},

  "transferable_insights": [
    "<điểm mạnh có thể chuyển đổi, ví dụ: '5 năm Python backend → học Go/FastAPI trong 2-4 tuần'>"
  ]
}}

QUAN TRỌNG:
- skill_gaps: sort theo severity: HIGH → MEDIUM → LOW
- bridge_from: chỉ ghi khi CÓ transferable skill tự nhiên
- learning_path: phải CỤ THỂ: tên tool/khóa học cụ thể
- CHỈ trả về JSON hợp lệ"""

    logger.info(
        f"  Calling LLM for holistic gap analysis: "
        f"{len(cv_formatted)} chars CV, {len(jd_formatted)} chars JD"
    )

    result = await llm_json_completion(
        prompt=user_prompt,
        context=f"Job: {jd_context}",
        system_prompt=system_prompt,
        temperature=0.1,
    )

    if not result:
        return {**state, "error": "LLM gap analysis returned empty", "status": "failed"}

    gap_analysis: GapAnalysisResult = {
        "overall_match_pct": float(result.get("overall_match_pct", 0)),
        "overall_assessment": result.get("overall_assessment", ""),
        "strengths": result.get("strengths") or [],
        "weaknesses": result.get("weaknesses") or [],
        "skill_gaps": result.get("skill_gaps") or [],
        "gap_summary": result.get("gap_summary") or {},
        "transferable_insights": result.get("transferable_insights") or [],
        "jd_context": jd_context,
    }

    logger.info(
        f"  Gap analysis DONE: {gap_analysis['overall_match_pct']}% match, "
        f"{len(gap_analysis['skill_gaps'])} gaps, "
        f"blocking: {gap_analysis['gap_summary'].get('blocking_skills', [])}"
    )

    return {**state, "gap_analysis": gap_analysis, "status": "gap_analyzed"}
