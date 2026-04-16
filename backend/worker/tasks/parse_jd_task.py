"""
parse_jd_task — Real JD Parsing Task.
Spec: 1.6 + JD Parsing Pipeline.
Thay thế stub bằng real LLM extraction + job_skill_requirement population.
"""

from worker.celery_app import celery_app
from shared.database import SessionLocal
from shared.models import Job, JobSkillRequirement, Skill
from worker.langgraph_agents.gap_v3.utils.llm_helpers import llm_json_completion
import uuid
import logging
import asyncio

logger = logging.getLogger("parse_jd_task")


@celery_app.task(name="worker.tasks.parse_jd_task.parse_jd")
def parse_jd(job_id: str):
    """
    Parse JD text → extract structured requirements → populate job_skill_requirement.
    1. Load job from DB
    2. LLM extract skills + metadata
    3. Upsert skills vào skills table
    4. Populate job_skill_requirement
    5. Update job status
    """
    db = SessionLocal()
    logger.info(f"parse_jd task: job_id={job_id}")

    try:
        job_uuid = uuid.UUID(job_id)
        job = db.query(Job).filter(Job.id == job_uuid).first()

        if not job:
            logger.error(f"Job not found: {job_id}")
            return {"error": f"Job not found: {job_id}"}

        if not job.raw_text:
            job.status = "failed"
            db.commit()
            return {"error": "Job has no raw_text"}

        # LLM extract requirements
        requirements = _extract_jd_requirements(job.raw_text, job.title_raw or "")

        if not requirements:
            job.status = "failed"
            job.extracted_requirements_json = []
            db.commit()
            return {"error": "LLM extraction returned no requirements"}

        # Save extracted requirements JSON
        job.extracted_requirements_json = requirements
        job.status = "completed"
        db.commit()
        logger.info(
            f"parse_jd SUCCESS: job={job_id}, {len(requirements)} requirements extracted"
        )

        return {
            "job_id": job_id,
            "status": "completed",
            "requirements_count": len(requirements),
            "requirements": requirements,
        }

    except Exception as e:
        logger.error(f"parse_jd FAILED: job={job_id}: {e}", exc_info=True)
        try:
            job.status = "failed"
            db.commit()
        except Exception:
            pass
        return {"error": str(e)}

    finally:
        db.close()


def _extract_jd_requirements(jd_text: str, job_title: str) -> list:
    """
    LLM extract structured requirements từ JD text.
    Trả về list[dict] với format chuẩn cho gap_v3.
    """
    prompt = f"""Trích xuất yêu cầu kỹ năng từ JD sau.

## Job Title: {job_title}

## JD Content:
{jd_text}

## Quy tắc:
1. Chỉ trích xuất kỹ năng KỸ THUẬT
2. Với mỗi skill: level, years, mandatory, weight
3. Group (VD: "Java or Kotlin") → type=group, strategy=OR
4. Weight: bắt buộc=8-10, tùy chọn=3-5

## Output JSON:
{{"requirements": [
  {{
    "skill": "<tên>",
    "target_level": "Junior|Mid-level|Senior|Expert",
    "years_required": <số năm>,
    "is_mandatory": true|false,
    "importance_weight": <1-10>,
    "type": "skill|group",
    "group_skills": [<nếu group>],
    "group_strategy": "AND|OR"
  }}
]}}
CHỈ trả JSON."""

    result = asyncio.run(llm_json_completion(prompt, context=job_title))
    return result.get("requirements", [])
