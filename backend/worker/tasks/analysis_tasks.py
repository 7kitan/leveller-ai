import os
from worker.celery_app import celery_app
from shared.database import SessionLocal
from services.analysis_service.gap_calculator import GapCalculator
from shared.models import UserAnalysis, Job
import logging
import asyncio
import uuid
import json
from datetime import datetime

logger = logging.getLogger("analysis_worker")

# ─── Feature Flag ────────────────────────────────────────────────────────────
# USE_LLM_GAP_AGENT_V3=true  → Gap v3 Orchestrator (LLM holistic, single call)
# USE_LLM_GAP_AGENT_V3=false → Legacy pipeline (vector engine)
USE_LLM_GAP_AGENT_V3 = os.getenv("USE_LLM_GAP_AGENT_V3", "true").lower() == "true"


def _fallback_to_legacy(calculator, user_id, cv_id, requirements, loop):
    """Fallback sang legacy AdvancedGapEngine khi v3 fail."""
    logger.warning("Falling back to legacy AdvancedGapEngine...")
    report = loop.run_until_complete(
        calculator.calculate_gap_v2(user_id, cv_id, requirements)
    )
    report["notes"] = report.get("notes", []) + ["[FALLBACK] Legacy Vector Engine used"]
    return report


@celery_app.task(name="worker.tasks.analysis_tasks.run_gap_analysis")
def run_gap_analysis(user_id: str, cv_id: str, job_id: str = None, jd_text: str = None):
    db = SessionLocal()
    calculator = GapCalculator(db)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        logger.info(f"--- STARTING ANALYSIS TASK: User={user_id}, CV={cv_id} ---")
        logger.info(
            f"    Mode: {'Gap v3 (LLM-Centric Holistic)' if USE_LLM_GAP_AGENT_V3 else 'Legacy (Vector Engine)'}"
        )

        # ── 1. Xác định JD Requirements ───────────────────────────────────────
        requirements = []
        jd_context = "Vị trí chưa xác định"

        if job_id:
            job = db.query(Job).filter(Job.id == uuid.UUID(job_id)).first()
            if job and job.raw_text:
                logger.info(f"Extracting requirements for Job {job_id} from DB...")
                requirements = loop.run_until_complete(
                    calculator.extract_requirements_from_text(job.raw_text)
                )
                jd_context = f"{job.title_raw or ''} @ {job.company_name or ''}".strip(
                    " @"
                )

        if not requirements and jd_text:
            logger.info("Extracting requirements from provided JD text...")
            requirements = loop.run_until_complete(
                calculator.extract_requirements_from_text(jd_text)
            )
            logger.info(f"Extracted {len(requirements)} requirements")

        if not requirements:
            logger.info(
                "No JD provided. Inferring market standard requirements from CV..."
            )
            requirements = loop.run_until_complete(
                calculator.infer_market_requirements_for_cv(cv_id)
            )

        if not requirements:
            logger.warning("No requirements found. Aborting.")
            return {"error": "No requirements found"}

        logger.info(f"Working with {len(requirements)} requirements")

        # ── 2. Tính Gap ────────────────────────────────────────────────────────
        if USE_LLM_GAP_AGENT_V3:
            # Gap v3: LLM-centric holistic pipeline
            try:
                from worker.langgraph_agents.gap_v3.orchestrator import (
                    run_gap_analysis_v3,
                )

                logger.info("Running Gap v3 (LLM-Centric Holistic)...")
                report = loop.run_until_complete(
                    run_gap_analysis_v3(
                        cv_id=cv_id,
                        user_id=user_id,
                        jd_text=jd_text,
                        job_id=job_id,
                        db=db,
                        jd_context=jd_context,
                    )
                )
                logger.info(
                    f"Gap v3 completed: {report.get('overall_match_pct')}% match"
                )

            except Exception as agent_err:
                logger.error(
                    f"Gap v3 failed: {agent_err}. Falling back to legacy engine."
                )
                report = _fallback_to_legacy(
                    calculator, user_id, cv_id, requirements, loop
                )

        else:
            # Legacy: AdvancedGapEngine (vector cosine)
            logger.info("Running legacy AdvancedGapEngine (vector mode)...")
            report = loop.run_until_complete(
                calculator.calculate_gap_v2(user_id, cv_id, requirements)
            )

        # ── 3. Persist kết quả vào PostgreSQL ─────────────────────────────────
        new_analysis = UserAnalysis(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            cv_id=uuid.UUID(cv_id),
            job_id=uuid.UUID(job_id) if job_id else None,
            match_score=report.get("overall_match_pct", 0),
            result_json=report,
            created_at=datetime.now(),
        )
        db.add(new_analysis)
        db.commit()

        logger.info(
            f"TASK SUCCESS & PERSISTED: Match={report.get('overall_match_pct')}%"
        )
        return report

    except Exception as e:
        db.rollback()
        logger.error(f"CRITICAL WORKER ERROR: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()
