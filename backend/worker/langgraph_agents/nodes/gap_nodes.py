import os
import json
import logging
import uuid
from typing import Dict, Any, List, Optional

logger = logging.getLogger("gap_analysis_agent")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
GAP_LLM_MODEL = os.getenv("GAP_LLM_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))

if LLM_PROVIDER == "openai":
    import openai
    _openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
else:
    _openai_client = None


# ─────────────────────────────────────────────
# Helper formatters
# ─────────────────────────────────────────────

def _format_work_history(work_history_records: list) -> str:
    """Format UserWorkExperience records thành chuỗi ngắn gọn cho LLM."""
    if not work_history_records:
        return "  (Không có lịch sử làm việc cụ thể)"
    lines = []
    for w in work_history_records:
        duration = getattr(w, "duration_years", 0) or 0
        duration_str = f"{duration:.1f} năm" if duration else "thời gian ngắn"
        lines.append(f"- [{duration_str}] {getattr(w, 'position_name', 'N/A')} @ {getattr(w, 'company_name', 'N/A')}")
        desc = getattr(w, "description", None)
        if desc:
            # Giới hạn mỗi description 300 ký tự để tránh overflow token
            lines.append(f"  Mô tả: {desc[:300]}")
        skills_ctx = getattr(w, "skills_context", None)
        if skills_ctx:
            if isinstance(skills_ctx, list):
                lines.append(f"  Skills tại vị trí này: {', '.join(skills_ctx[:10])}")
            elif isinstance(skills_ctx, str):
                lines.append(f"  Skills tại vị trí này: {skills_ctx[:200]}")
    return "\n".join(lines)


def _format_skill_profiles(skill_profiles: list) -> str:
    """Format UserSkillProfile + Skill.name thành chuỗi cho LLM."""
    if not skill_profiles:
        return "  (Không có kỹ năng được ghi nhận)"
    lines = []
    for profile, skill_name in skill_profiles:
        level = getattr(profile, "level", "Unknown") or "Unknown"
        years = getattr(profile, "years_exp", 0) or 0
        last_used = getattr(profile, "last_used_year", None)
        context = getattr(profile, "skill_context", None)

        parts = [f"- {skill_name} | {level} | {years:.1f} năm"]
        if last_used:
            parts[0] += f" | dùng gần nhất: {last_used}"
        if context:
            parts.append(f"  ngữ cảnh: {context[:150]}")
        lines.append("\n".join(parts))
    return "\n".join(lines)


def _format_jd_requirements(jd_requirements: list) -> str:
    """Format JD requirements thành chuỗi ngắn gọn."""
    lines = []
    for req in jd_requirements:
        req_type = req.get("type", "skill")
        is_mandatory = req.get("is_mandatory", req.get("is_primary", True))
        level = req.get("target_level") or req.get("required_level") or "Không xác định"
        years = req.get("years_required", 0) or 0
        tag = "[BẮT BUỘC]" if is_mandatory else "[TÙY CHỌN]"

        if req_type == "group":
            strategy_label = "OR" if req.get("group_strategy") == "exclusive" else "AND"
            group_skills = req.get("skills", [])
            skill_names = " / ".join([s.get("skill", "?") for s in group_skills])
            lines.append(f"{tag} {req.get('group_name', 'Nhóm kỹ năng')} ({strategy_label}): {skill_names}")
        else:
            skill_name = req.get("skill_name") or req.get("skill") or "Unknown"
            year_str = f" | {years} năm kinh nghiệm" if years > 0 else ""
            lines.append(f"{tag} {skill_name} | {level}{year_str}")
    return "\n".join(lines) if lines else "  (Không có yêu cầu cụ thể)"


# ─────────────────────────────────────────────
# Node 1: prep_context_node
# ─────────────────────────────────────────────

async def prep_context_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load toàn bộ CV context từ DB:
    - summary, raw_text
    - work_history với descriptions, skills per role
    - skill profiles với level, years, context
    Format thành cv_profile_text để gửi cho LLM.
    """
    logger.info("--- [GAP AGENT] Node 1: prep_context_node ---")
    db = state.get("db")
    cv_id_str = state.get("cv_id")

    if not db or not cv_id_str:
        return {**state, "error": "Missing db session or cv_id", "status": "failed"}

    try:
        from shared.models import UserCV, UserWorkExperience, UserSkillProfile, Skill
        cv_uuid = uuid.UUID(cv_id_str) if isinstance(cv_id_str, str) else cv_id_str

        # 1. Load CV record
        cv = db.query(UserCV).filter(UserCV.id == cv_uuid).first()
        if not cv:
            return {**state, "error": f"CV not found: {cv_id_str}", "status": "failed"}

        # 2. Load work history
        work_history = db.query(UserWorkExperience)\
            .filter(UserWorkExperience.cv_id == cv_uuid)\
            .all()

        # 3. Load skill profiles với tên skill
        skill_profiles = db.query(UserSkillProfile, Skill.name)\
            .join(Skill, UserSkillProfile.skill_id == Skill.id)\
            .filter(UserSkillProfile.cv_id == cv_uuid)\
            .order_by(UserSkillProfile.years_exp.desc())\
            .all()

        # 4. Build CV profile text
        exp_total = cv.experience_years_total or 0
        summary_text = cv.summary or "(Không có tóm tắt chuyên nghiệp)"
        
        # Inferred seniority if not explicit
        seniority_level = "Unknown"
        if exp_total < 2: seniority_level = "Junior"
        elif exp_total < 5: seniority_level = "Mid-level"
        elif exp_total < 8: seniority_level = "Senior"
        else: seniority_level = "Expert"

        cv_profile_text = f"""## TỔNG QUAN ỨNG VIÊN
{summary_text}
Seniority (Ước tính): {seniority_level} | Tổng kinh nghiệm: {exp_total:.1f} năm

## LỊCH SỬ LÀM VIỆC (Chi tiết)
{_format_work_history(work_history)}

## KỸ NĂNG KỸ THUẬT (Có Metadata)
{_format_skill_profiles(skill_profiles)}"""

        # Fallback: nếu không có work_history, bổ sung raw_text CV (full text gốc)
        if not work_history and cv.raw_text:
            cv_profile_text += f"\n\n## NỘI DUNG CV GỐC\n{cv.raw_text[:3000]}"

        logger.info(f"  CV context built: {len(cv_profile_text)} chars, "
                    f"{len(work_history)} work entries, {len(skill_profiles)} skills")

        return {
            **state,
            "cv_profile_text": cv_profile_text,
            "status": "context_ready"
        }

    except Exception as e:
        logger.error(f"prep_context_node error: {e}", exc_info=True)
        return {**state, "error": str(e), "status": "failed"}


# ─────────────────────────────────────────────
# Node 2: llm_gap_analyze_node
# ─────────────────────────────────────────────

async def llm_gap_analyze_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gọi LLM với TOÀN BỘ CV context + JD requirements.
    LLM sẽ phân tích sâu: transferable skills, thực chất gap,
    điểm mạnh/yếu dựa trên work descriptions thực tế.
    """
    logger.info("--- [GAP AGENT] Node 2: llm_gap_analyze_node ---")

    if state.get("status") == "failed":
        return state

    cv_profile_text = state.get("cv_profile_text", "")
    jd_requirements = state.get("jd_requirements", [])
    jd_context = state.get("jd_context", "Vị trí chưa xác định")

    if not cv_profile_text:
        return {**state, "error": "cv_profile_text is empty", "status": "failed"}

    formatted_jd = _format_jd_requirements(jd_requirements)

    system_prompt = """Bạn là chuyên gia phân tích sự phù hợp nghề nghiệp (Career Fit Analyst) cấp cao.
Nhiệm vụ: Đọc kỹ TOÀN BỘ hồ sơ ứng viên và phân tích mức độ phù hợp với vị trí tuyển dụng.

NGUYÊN TẮC PHÂN TÍCH:
1. Đánh giá dựa trên KINH NGHIỆM THỰC TẾ (mô tả công việc, dự án) — không chỉ tên kỹ năng
2. Phát hiện "transferable skills": kỹ năng tương đương có thể chuyển đổi (ví dụ: Django → FastAPI)
3. Phân biệt gap "hard" (thực sự thiếu, không thể bù ngắn hạn) vs gap "soft" (có nền tảng, học được)
4. Viết nhận xét bằng tiếng Việt, ngắn gọn và có giá trị thực tế"""

    user_prompt = f"""## ===== HỒ SƠ ỨNG VIÊN (TOÀN BỘ NGỮ CẢNH) =====
{cv_profile_text}

## ===== YÊU CẦU CÔNG VIỆC =====
Vị trí: {jd_context}
{formatted_jd}

---
Dựa trên TOÀN BỘ ngữ cảnh hồ sơ trên, hãy phân tích và trả về JSON:

{{
  "overall_match_pct": <số thực 0-100, đánh giá tổng thể>,
  "overall_assessment": "<nhận xét tổng thể 2-3 câu bằng tiếng Việt, dựa trên kinh nghiệm thực tế>",
  
  "strengths": [
    "<điểm mạnh cụ thể dựa trên work history, không chỉ liệt kê skill>"
  ],
  "weaknesses": [
    "<điểm yếu/gap thực sự, có giải thích tại sao đây là gap>"
  ],
  
  "gap_matrix": [
    {{
      "jd_skill": "<tên kỹ năng JD yêu cầu>",
      "cv_skill": "<tên kỹ năng CV tương ứng, null nếu không có>",
      "status": "MET | PARTIAL | GAP",
      "score": <0-100>,
      "note": "<giải thích ngắn, ví dụ: 'Có Django 3 năm, FastAPI là async version tương tự, chuyển đổi ~2 tuần'>"
    }}
  ],
  
  "breakdown": {{
    "met":     [{{"skill": "<tên>", "score": <0-100>, "evidence": "<bằng chứng từ work history>"}}],
    "partial": [{{"skill": "<tên>", "score": <0-100>, "bridge_from": "<skill tương đương đã có>", "effort": "<ước tính thời gian để đạt>"}}],
    "gap":     [{{"skill": "<tên>", "score": 0, "is_mandatory": true|false, "severity": "HIGH|MEDIUM|LOW"}}]
  }},
  
  "skill_gaps": [
    {{
      "skill": "<tên kỹ năng bị thiếu>",
      "severity": "HIGH | MEDIUM | LOW",
      "priority": <1, 2, 3...>,
      "reason": "<tại sao đây là gap, có bridge skill không?>",
      "learning_path": "<lộ trình học ngắn gọn, ví dụ: Docker → K8s Basics → Helm>"
    }}
  ],
  
  "course_queries": [
    {{
      "skill": "<tên skill gap>",
      "query": "<từ khóa tìm kiếm khóa học phù hợp>",
      "priority": <1, 2, 3...>
    }}
  ]
}}

QUAN TRỌNG: Chỉ trả về JSON hợp lệ. Không thêm text bên ngoài JSON."""

    try:
        if not _openai_client:
            return {**state, "error": "LLM client not initialized", "status": "failed"}

        logger.info(f"  Calling {GAP_LLM_MODEL} for gap analysis...")
        response = _openai_client.chat.completions.create(
            model=GAP_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1  # Ít randomness để JSON ổn định
        )

        raw_content = response.choices[0].message.content
        logger.info(f"  LLM response received: {len(raw_content)} chars")

        llm_output = json.loads(raw_content)

        # Basic validation
        required_keys = ["overall_match_pct", "gap_matrix", "breakdown", "skill_gaps"]
        missing = [k for k in required_keys if k not in llm_output]
        if missing:
            logger.warning(f"  LLM output missing keys: {missing}")

        return {
            **state,
            "llm_raw_output": llm_output,
            "status": "analyzed"
        }

    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}")
        return {**state, "error": f"LLM JSON parse error: {e}", "status": "failed"}
    except Exception as e:
        logger.error(f"llm_gap_analyze_node error: {e}", exc_info=True)
        return {**state, "error": str(e), "status": "failed"}


# ─────────────────────────────────────────────
# Node 3: course_lookup_node
# ─────────────────────────────────────────────

async def course_lookup_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query bảng courses trong DB theo từng gap skill.
    Dùng text search (ILIKE) + fallback vector similarity nếu có embedding.
    """
    logger.info("--- [GAP AGENT] Node 3: course_lookup_node ---")

    if state.get("status") == "failed":
        return state

    llm_output = state.get("llm_raw_output", {})
    course_queries = llm_output.get("course_queries", [])
    db = state.get("db")

    if not db or not course_queries:
        logger.info("  No course queries or db. Skipping course lookup.")
        return {**state, "course_results": []}

    from sqlalchemy import text as sql_text

    course_results = []
    seen_course_ids = set()

    for cq in course_queries:
        skill_name = cq.get("skill", "")
        query_str = cq.get("query", skill_name)
        priority = cq.get("priority", 99)

        if not query_str:
            continue

        try:
            # Text search: tìm trong title + tags + description
            search_query = sql_text("""
                SELECT id, title, platform, url, level, is_certification,
                       provider, duration_hours, cost_usd, tags
                FROM courses
                WHERE title ILIKE :pattern
                   OR :skill_pattern = ANY(tags::text[])
                   OR tags::text ILIKE :pattern
                ORDER BY is_certification DESC, duration_hours ASC
                LIMIT 3
            """)

            results = db.execute(search_query, {
                "pattern": f"%{query_str}%",
                "skill_pattern": skill_name
            }).fetchall()

            # Nếu không tìm thấy, thử với tên skill gốc
            if not results and query_str != skill_name:
                results = db.execute(search_query, {
                    "pattern": f"%{skill_name}%",
                    "skill_pattern": skill_name
                }).fetchall()

            found_courses = []
            for r in results:
                course_id = str(r.id)
                if course_id not in seen_course_ids:
                    seen_course_ids.add(course_id)
                    found_courses.append({
                        "id": course_id,
                        "title": r.title,
                        "platform": r.platform,
                        "url": r.url,
                        "level": r.level,
                        "is_certification": bool(r.is_certification),
                        "provider": r.provider,
                        "duration_hours": r.duration_hours,
                        "cost_usd": r.cost_usd or 0
                    })

            course_results.append({
                "skill_gap": skill_name,
                "priority": priority,
                "courses": found_courses[:2]  # Top 2 courses per gap
            })

            logger.info(f"  Gap '{skill_name}': found {len(found_courses)} courses")

        except Exception as e:
            logger.error(f"  Course lookup error for '{skill_name}': {e}")
            db.rollback()
            course_results.append({"skill_gap": skill_name, "priority": priority, "courses": []})

    return {
        **state,
        "course_results": course_results,
        "status": "courses_found"
    }


# ─────────────────────────────────────────────
# Node 4: finalize_report_node
# ─────────────────────────────────────────────

async def finalize_report_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge LLM output + course_results thành final_report.
    Đảm bảo backward compatibility với frontend cũ.
    """
    logger.info("--- [GAP AGENT] Node 4: finalize_report_node ---")

    llm_output = state.get("llm_raw_output") or {}
    course_results = state.get("course_results") or []

    # Lấy các section từ LLM output
    overall_pct = float(llm_output.get("overall_match_pct", 0))
    breakdown = llm_output.get("breakdown", {"met": [], "partial": [], "gap": []})
    gap_matrix = llm_output.get("gap_matrix", [])
    skill_gaps = llm_output.get("skill_gaps", [])

    # Build course_recommendations: gắn reason từ skill_gaps vào course_results
    skill_gap_map = {sg["skill"]: sg for sg in skill_gaps}
    course_recommendations = []

    for cr in course_results:
        sg_info = skill_gap_map.get(cr["skill_gap"], {})
        course_recommendations.append({
            "skill_gap": cr["skill_gap"],
            "priority": cr["priority"],
            "severity": sg_info.get("severity", "MEDIUM"),
            "reason": sg_info.get("reason", f"Gap được phát hiện cho kỹ năng {cr['skill_gap']}"),
            "learning_path": sg_info.get("learning_path", ""),
            "courses": cr["courses"]
        })

    # Sắp xếp theo priority
    course_recommendations.sort(key=lambda x: x["priority"])

    # Build recommendations (backward compat format cho frontend cũ)
    recommendations = []
    for item in breakdown.get("partial", []):
        recommendations.append({
            "skill": item.get("skill", ""),
            "type": "PARTIAL",
            "target_level": "Mid-level",
            "bridge_from": item.get("bridge_from", ""),
            "effort": item.get("effort", "")
        })
    for item in breakdown.get("gap", []):
        recommendations.append({
            "skill": item.get("skill", ""),
            "type": "MISSING",
            "target_level": "Mid-level",
            "severity": item.get("severity", "MEDIUM"),
            "is_mandatory": item.get("is_mandatory", True)
        })

    final_report = {
        # Core metrics
        "overall_match_pct": round(overall_pct, 1),
        "overall_assessment": llm_output.get("overall_assessment", ""),

        # Strengths & Weaknesses
        "strengths": llm_output.get("strengths", []),
        "weaknesses": llm_output.get("weaknesses", []),

        # Breakdown (backward compat)
        "breakdown": breakdown,

        # New: detailed matrix
        "gap_matrix": gap_matrix,
        "skill_gaps": skill_gaps,

        # New: courses embedded trong response
        "course_recommendations": course_recommendations,

        # Backward compat
        "recommendations": recommendations,
        "notes": [
            f"Analysis Method: LLM Gap Agent (full CV context, {GAP_LLM_MODEL})",
            f"Courses found: {sum(len(cr['courses']) for cr in course_results)}"
        ]
    }

    logger.info(f"  Final report: {overall_pct:.1f}% match, "
                f"{len(gap_matrix)} matrix entries, "
                f"{len(course_recommendations)} course recommendation groups")

    return {
        **state,
        "final_report": final_report,
        "status": "completed"
    }
