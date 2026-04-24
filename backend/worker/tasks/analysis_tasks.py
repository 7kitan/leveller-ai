import os
import json as _json
import logging
import asyncio
import uuid
import time
from datetime import datetime
from worker.celery_app import celery_app
from shared.database import SessionLocal
from services.analysis_service.gap_calculator import GapCalculator
from shared.models import UserAnalysis, Job

logger = logging.getLogger("analysis_worker")


def _indent_data(text: str) -> str:
    """Indent each line for log readability."""
    return "\n".join("    " + line for line in text.split("\n"))


# Feature flag
USE_LLM_GAP_AGENT = os.getenv("USE_LLM_GAP_AGENT", "true").lower() == "true"


def _fallback_to_legacy(calculator, user_id, cv_id, requirements, loop):
    logger.warning("[ANALYSIS] Falling back to legacy AdvancedGapEngine...")
    report = loop.run_until_complete(
        calculator.calculate_gap_v2(user_id, cv_id, requirements)
    )
    
    # Map legacy keys to new structure for UI compatibility
    if "breakdown" in report and "gap" in report["breakdown"]:
        # Convert legacy gap format to match v3 structure if possible, 
        # or just ensure the key exists for the UI to pick up.
        report["skill_gaps"] = report["breakdown"]["gap"]
        
    if "recommendations" in report:
        report["recommended_courses"] = report["recommendations"]

    report["notes"] = report.get("notes", []) + ["[FALLBACK] Legacy Vector Engine used"]
    return report


@celery_app.task(bind=True, name="worker.tasks.analysis_tasks.run_gap_analysis")
def run_gap_analysis(self, user_id: str, cv_id: str, job_id: str = None, jd_text: str = None, force: bool = False, lang: str = "vi"):
    """
    Gap Analysis Celery Task.
    Flow:
      [STEP 1] Load + validate CV
      [STEP 2] Resolve job requirements (from job_id | jd_text | inference)
      [STEP 3] Run gap analysis (v3 or legacy)
      [STEP 4] Persist result to UserAnalysis table
    """
    self.update_state(state='PROGRESS', meta={'message': 'Đang khởi tạo engine phân tích...', 'percent': 5})
    t0 = time.monotonic()
    db = SessionLocal()
    calculator = GapCalculator(db)

    logger.info(
        "\n" + "=" * 60 + "\n"
        f"[ANALYSIS TASK] START | user_id={user_id} | cv_id={cv_id}\n"
        f"  job_id  : {job_id or 'None'}\n"
        f"  jd_text : {'provided' if jd_text else 'None'}\n"
        f"  v3 mode : {USE_LLM_GAP_AGENT}\n" + "=" * 60
    )

    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("event loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        # ── STEP 1: Validate CV ───────────────────────────────────────────────
        self.update_state(state='PROGRESS', meta={'message': 'Đang đọc và xác thực dữ liệu CV...', 'percent': 15})
        logger.info(f"[ANALYSIS STEP 1/4] Validate CV | cv_id={cv_id}")
        from shared.models import UserCV

        cv = (
            db.query(UserCV)
            .filter(
                UserCV.id == uuid.UUID(cv_id),
                UserCV.user_id == uuid.UUID(user_id),
            )
            .first()
        )

        if not cv:
            logger.error(
                f"[ANALYSIS STEP 1] CV not found — cv_id={cv_id} user_id={user_id}"
            )
            return {"error": f"CV {cv_id} not found or unauthorized"}

        if cv.status != "completed":
            logger.error(f"[ANALYSIS STEP 1] CV not ready — status={cv.status}")
            return {"error": f"CV status is '{cv.status}', expected 'completed'"}

        cv_name = cv.full_name or f"CV_{cv_id[:8]}"
        cv_parsed = cv.cv_parsed_json or {}
        logger.info(
            f"[ANALYSIS STEP 1] CV OK\n"
            f"  name       : {cv_name}\n"
            f"  status     : {cv.status}\n"
            f"  skills     : {len(cv_parsed.get('skills', []))}\n"
            f"  work_hist. : {len(cv_parsed.get('work_history', []))}\n"
            f"  education  : {len(cv_parsed.get('education', []))}\n"
            f"  certs      : {len(cv_parsed.get('certifications', []))}\n"
            f"  seniority  : {cv_parsed.get('seniority')}\n"
            f"  exp_yrs    : {cv_parsed.get('experience_years_total')}\n"
            f"  summary    : {str(cv_parsed.get('summary', ''))[:100]}"
        )

        # ── Log FULL CV parsed data ──────────────────────────────────────────
        logger.info(
            f"\n{'═' * 70}\n"
            f"[ANALYSIS DATA] ┌─── CV parsed JSON | cv_id={cv_id}\n"
            f"                │ cv_name    : {cv_name}\n"
            f"                │ skills     : {len(cv_parsed.get('skills', []))}\n"
            f"                │ work_hist  : {len(cv_parsed.get('work_history', []))}\n"
            f"                │ education  : {len(cv_parsed.get('education', []))}\n"
            f"                │ certs      : {len(cv_parsed.get('certifications', []))}\n"
            f"                │ seniority  : {cv_parsed.get('seniority')}\n"
            f"                │ exp_yrs    : {cv_parsed.get('experience_years_total')}\n"
            f"                └─────────\n"
            f"[ANALYSIS DATA] CV PARSED JSON (first 3000 chars):\n"
            f"{_indent_data(_json.dumps(cv_parsed, ensure_ascii=False, indent=2)[:3000])}\n"
            f"{'═' * 70}\n"
        )

        # ── STEP 2: Resolve job requirements ───────────────────────────────────
        self.update_state(state='PROGRESS', meta={'message': 'Đang bóc tách yêu cầu công việc (JD)...', 'percent': 30})
        logger.info(
            f"[ANALYSIS STEP 2/4] Resolve job requirements | mode={'job_id' if job_id else ('jd_text' if jd_text else 'inference')}"
        )
        requirements = []
        jd_context = "Portfolio self-analysis (no job specified)"

        if job_id:
            try:
                job_uuid = uuid.UUID(job_id)
                job = db.query(Job).filter(Job.id == job_uuid).first()
                if job:
                    logger.info(
                        f"[ANALYSIS STEP 2] Found job in DB — id={job_id} title='{job.title_raw}'"
                    )
                    
                    # ── OPTIMIZATION: Check for existing extraction first ──
                    if job.extracted_requirements_json:
                        requirements = job.extracted_requirements_json
                        logger.info(f"[ANALYSIS STEP 2] ✓ Using existing extracted_requirements_json from DB")
                    elif job.skills_required:
                        # Fallback to separate SkillRequirement table
                        assembled = []
                        for jsr in job.skills_required:
                            assembled.append({
                                "skill": jsr.skill.name if jsr.skill else "Unknown",
                                "target_level": jsr.required_level or "Junior",
                                "years_required": jsr.min_years_exp or 0,
                                "is_mandatory": jsr.is_mandatory
                            })
                        requirements = assembled
                        logger.info(f"[ANALYSIS STEP 2] ✓ Assembled {len(requirements)} requirements from DB skill table")
                    
                    if not requirements:
                        if job.raw_text:
                            logger.info(f"[ANALYSIS STEP 2] No extraction found. Triggering AI extraction...")
                            requirements = loop.run_until_complete(
                                calculator.extract_requirements_from_text(job.raw_text, job_id=job_id, user_id=user_id)
                            )
                            logger.info(f"[ANALYSIS STEP 2] Extracted {len(requirements)} requirements via AI")
                        else:
                            logger.warning(f"[ANALYSIS STEP 2] Job has no raw_text — id={job_id}")

                    jd_context = (
                        f"{job.title_raw or ''} @ {job.company_name or ''}".strip(
                            " @"
                        )
                    )
                    # ── Pass raw_text as jd_text so v3 orchestrator has it ──
                    jd_text = job.raw_text
                else:
                    logger.warning(
                        f"[ANALYSIS STEP 2] Job not found in DB — id={job_id}"
                    )
            except Exception as e:
                db.rollback()
                logger.warning(f"[ANALYSIS STEP 2] Failed to load job_id={job_id}: {e}")

        if not requirements and jd_text:
            logger.info(
                "[ANALYSIS STEP 2] Extracting requirements from provided jd_text..."
            )
            requirements = loop.run_until_complete(
                calculator.extract_requirements_from_text(jd_text, user_id=user_id)
            )
            jd_context = "Custom JD provided"
            logger.info(
                f"[ANALYSIS STEP 2] Extracted {len(requirements)} requirements from jd_text"
            )

        if not requirements:
            logger.info(
                "[ANALYSIS STEP 2] No JD provided — inferring market standard requirements from CV..."
            )
            requirements = loop.run_until_complete(
                calculator.infer_market_requirements_for_cv(cv_id, user_id=user_id)
            )
            jd_context = "Market standard requirements (inferred)"
            logger.info(f"[ANALYSIS STEP 2] Inferred {len(requirements)} requirements")

        if not requirements:
            logger.error(
                "[ANALYSIS STEP 2] No requirements could be resolved — ABORTING"
            )
            return {
                "error": "No job requirements found (no job_id, jd_text, or could not infer)."
            }

        logger.info(
            f"[ANALYSIS STEP 2] Requirements resolved: {len(requirements)}\n"
            f"  context: {jd_context}\n"
            f"  top 3  : {[r.get('skill_name', r.get('name', '?')) for r in requirements[:3]]}"
        )

        # ── Log FULL requirements data ──────────────────────────────────────
        logger.info(
            f"\n{'═' * 70}\n"
            f"[ANALYSIS DATA] ┌─── Job Requirements | mode={'job_id' if job_id else ('jd_text' if jd_text else 'inference')}\n"
            f"                │ count     : {len(requirements)}\n"
            f"                │ context   : {jd_context}\n"
            f"                └─────────\n"
            f"[ANALYSIS DATA] REQUIREMENTS JSON (first 3000 chars):\n"
            f"{_indent_data(_json.dumps(requirements, ensure_ascii=False, indent=2)[:3000])}\n"
            f"{'═' * 70}\n"
        )

        # ── STEP 3: Run gap analysis ─────────────────────────────────────────
        self.update_state(state='PROGRESS', meta={'message': 'AI đang phân tích khoảng cách kỹ năng...', 'percent': 50})
        logger.info(
            f"[ANALYSIS STEP 3/4] Run gap analysis | engine={'Gap v3 LLM' if USE_LLM_GAP_AGENT else 'Legacy Vector'}"
        )

        if USE_LLM_GAP_AGENT:
            try:
                from worker.langgraph_agents.gap_v3.orchestrator import (
                    run_gap_analysis_v3,
                )

                logger.info(
                    "[ANALYSIS STEP 3] Invoking run_gap_analysis_v3 orchestrator..."
                )
                t3 = time.monotonic()
                logger.info(
                    f"[ANALYSIS STEP 3] PAYLOAD to v3 orchestrator:\n"
                    f"  cv_id     : {cv_id}\n"
                    f"  user_id   : {user_id}\n"
                    f"  job_id    : {job_id}\n"
                    f"  jd_text   : {'<provided, ' + str(len(jd_text or '')) + ' chars>' if jd_text else '<NONE>'}\n"
                    f"  jd_text[:200]: {repr((jd_text or '')[:200])}\n"
                    f"  jd_context: {repr(jd_context)}"
                )
                async def on_step_update(partial_data):
                    # Cập nhật state của Celery task với dữ liệu bán thành phẩm
                    node_name = partial_data.get("node")
                    msg = f"Đang xử lý: {node_name}..."
                    if node_name == "gap_analysis":
                        msg = "✓ Đã hoàn thành phân tích Gap. Đang tìm khóa học..."
                    elif node_name == "course_agent":
                        msg = "✓ Đã tìm xong khóa học. Đang tổng hợp lộ trình..."
                    
                    self.update_state(
                        state='PROGRESS', 
                        meta={
                            'message': msg, 
                            'percent': 60 if node_name == "gap_analysis" else 80,
                            'partial_result': partial_data
                        }
                    )
                    logger.info(f"[ANALYSIS TASK] Progress update from node: {node_name}")

                report = loop.run_until_complete(
                    run_gap_analysis_v3(
                        cv_id=cv_id,
                        user_id=user_id,
                        jd_text=jd_text,
                        job_id=job_id,
                        db=db,
                        jd_context=jd_context,
                        force=force,
                        lang=lang,
                        on_update=on_step_update
                    )
                )
                elapsed_v3 = time.monotonic() - t3
                match_pct = report.get("overall_match_pct", "N/A")
                gaps = report.get("skill_gaps", [])
                courses = report.get("course_recommendations", [])
                roadmap = report.get("career_roadmap")
                logger.info(
                    f"[ANALYSIS STEP 3] Gap v3 completed in {elapsed_v3:.1f}s\n"
                    f"  overall_match_pct  : {match_pct}\n"
                    f"  skill_gaps         : {len(gaps)}\n"
                    f"  recommended_courses: {len(courses)}\n"
                    f"  career_roadmap     : {'present' if roadmap else 'missing'}"
                )
            except Exception as agent_err:
                db.rollback()
                logger.error(
                    f"[ANALYSIS STEP 3] Gap v3 failed: {agent_err}", exc_info=True
                )
                logger.info("[ANALYSIS STEP 3] Falling back to legacy engine...")
                report = _fallback_to_legacy(
                    calculator, user_id, cv_id, requirements, loop
                )
        else:
            logger.info("[ANALYSIS STEP 3] Running legacy AdvancedGapEngine...")
            report = loop.run_until_complete(
                calculator.calculate_gap_v2(user_id, cv_id, requirements)
            )
            logger.info(
                f"[ANALYSIS STEP 3] Legacy completed — match={report.get('overall_match_pct')}%"
            )

        # ── STEP 4: Persist to DB ──────────────────────────────────────────────
        self.update_state(state='PROGRESS', meta={'message': 'Đang tổng hợp lộ trình và lưu kết quả...', 'percent': 90})
        logger.info(f"[ANALYSIS STEP 4/4] Persist to UserAnalysis table")
        job_uuid = None
        if job_id:
            try:
                job_uuid = uuid.UUID(job_id)
            except (ValueError, TypeError):
                logger.warning(
                    f"[ANALYSIS STEP 4] Invalid job_id={job_id!r} — setting to NULL"
                )

        new_analysis = UserAnalysis(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            cv_id=uuid.UUID(cv_id),
            job_id=job_uuid,
            match_score=report.get("overall_match_pct", 0) or 0,
            result_json=report,
            created_at=datetime.now(),
        )
        db.add(new_analysis)
        db.flush()  # Force INSERT execution so the ID exists for the User relation

        # Update User's last_analysis_id for persistent state
        from shared.models import User
        from services.analysis_service.market_fit_service import update_user_market_fit

        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if user:
            user.last_analysis_id = new_analysis.id
            logger.info(f"[ANALYSIS STEP 4] Updated User {user_id} with last_analysis_id={new_analysis.id}")
            
            # ── TRIGGER MARKET FIT UPDATE ──────────────────────────────────────
            # Mỗi khi phân tích gap xong, tính lại market fit để Dashboard luôn mới
            try:
                # Chạy đồng bộ trong worker vì đây là background task rồi
                loop = asyncio.get_event_loop()
                loop.run_until_complete(update_user_market_fit(user.id, db))
                logger.info(f"[ANALYSIS STEP 4] ✓ Market Fit updated for user {user_id}")
            except Exception as mf_err:
                logger.error(f"[ANALYSIS STEP 4] Failed to update market fit: {mf_err}")

        db.commit()

        total_elapsed = time.monotonic() - t0
        logger.info(
            f"\n" + "=" * 60 + "\n"
            f"[ANALYSIS TASK] SUCCESS | cv_id={cv_id} | total={total_elapsed:.1f}s\n"
            f"  match_score  : {report.get('overall_match_pct')}%\n"
            f"  skill_gaps   : {len(report.get('skill_gaps', []))}\n"
            f"  courses      : {len(report.get('recommended_courses', []))}\n"
            f"  gap_context  : {jd_context}\n" + "=" * 60
        )
        # Ensure cv_id and job_id are in the report for frontend redirection
        if isinstance(report, dict):
            report["cv_id"] = str(cv_id)
            report["job_id"] = str(job_id) if job_id else None

        return report

    except Exception as e:
        db.rollback()
        total_elapsed = time.monotonic() - t0
        logger.error(
            f"\n" + "=" * 60 + "\n"
            f"[ANALYSIS TASK] CRITICAL ERROR | cv_id={cv_id} | elapsed={total_elapsed:.1f}s\n"
            f"  exc_type : {type(e).__name__}\n"
            f"  message  : {e}\n" + "=" * 60,
            exc_info=True,
        )
        return {"error": str(e)}

    finally:
        # ALWAYS rollback before close — prevents aborted transaction from
        # contaminating the connection pool and causing cascading failures.
        try:
            db.rollback()
        except Exception:
            pass
        db.close()
        logger.info(f"[ANALYSIS TASK] DB session closed | cv_id={cv_id}")
