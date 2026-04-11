from worker.celery_app import celery_app
from shared.database import SessionLocal
from services.analysis_service.gap_calculator import GapCalculator
from shared.models import JobSkillRequirement, UserAnalysis, Job
from sqlalchemy.orm import joinedload
import logging
import asyncio
import uuid
from datetime import datetime

# Cấu hình logging chuyên sâu cho Worker
logger = logging.getLogger("analysis_worker")

@celery_app.task(name="worker.tasks.analysis_tasks.run_gap_analysis")
def run_gap_analysis(user_id: str, cv_id: str, job_id: str = None, jd_text: str = None):
    db = SessionLocal()
    calculator = GapCalculator(db)
    
    # Đảm bảo có event loop cho các tác vụ async
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        logger.info(f"--- STARTING ANALYSIS TASK: User={user_id}, CV={cv_id} ---")
        
        # 1. Xác định Requirements (Kỹ năng yêu cầu)
        requirements = []
        if job_id:
            # Ưu tiên 1.1: Kiểm tra bảng chuẩn hóa JobSkillRequirement
            requirements = db.query(JobSkillRequirement)\
                .options(joinedload(JobSkillRequirement.skill))\
                .filter(JobSkillRequirement.job_id == uuid.UUID(job_id)).all()
            
            # Ưu tiên 1.2: Nếu bảng chuẩn hóa trống, kiểm tra Cache JSON trong bảng Job
            if not requirements:
                logger.info(f"Normalized requirements empty for job {job_id}. Checking Job Model Cache...")
                job = db.query(Job).filter(Job.id == uuid.UUID(job_id)).first()
                if job and job.extracted_requirements_json:
                    requirements = job.extracted_requirements_json
                    logger.info(f"LAYER 1.2 HIT: Loaded requirements from Job.extracted_requirements_json")
                elif job and job.raw_text:
                    # Ưu tiên 1.3: Nếu chỉ có text thô, tiến hành bóc tách Hybrid
                    logger.info(f"Job {job_id} has raw text but no parsed requirements. Extracting...")
                    requirements = loop.run_until_complete(calculator.extract_requirements_from_text(job.raw_text))

        # Ưu tiên 2: Nếu không có job_id hoặc các bước trên thất bại, bóc tách từ jd_text truyền lên
        if not requirements and jd_text:
            logger.info("Extracting requirements from provided raw JD text using 4-Layer Hybrid Retrieval...")
            requirements = loop.run_until_complete(calculator.extract_requirements_from_text(jd_text))
            logger.info(f"Hybrid Retrieval returned {len(requirements)} requirement items.")
        
        # NÂNG CẤP: Fallback nếu hoàn toàn không có JD (Phân tích dựa trên Market Standard)
        if not requirements:
            logger.info("No JD provided. Inferring market standard requirements based on CV profile...")
            requirements = loop.run_until_complete(calculator.infer_market_requirements_for_cv(cv_id))
            logger.info(f"AI Inferred {len(requirements)} market-standard requirements.")

        if not requirements:
            logger.warning("Still no requirements found after inference. Aborting.")
            return {"error": "No requirements found"}

        # 2. Tính toán Gap
        logger.info("Calculating gaps via Engine V5.15 (Seniority-Aware)...")
        report = loop.run_until_complete(calculator.calculate_gap_v2(user_id, cv_id, requirements))
        
        # 3. LƯU TRỮ KẾT QUẢ VÀO POSTGRES (Persistence)
        new_analysis = UserAnalysis(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            cv_id=uuid.UUID(cv_id),
            job_id=uuid.UUID(job_id) if job_id else None,
            match_score=report.get("overall_match_pct", 0),
            result_json=report,
            created_at=datetime.now()
        )
        db.add(new_analysis)
        db.commit()
        
        logger.info(f"TASK SUCCESS & PERSISTED: Match Score = {report.get('overall_match_pct')}%")
        return report
        
    except Exception as e:
        db.rollback()
        logger.error(f"CRITICAL WORKER ERROR: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()
