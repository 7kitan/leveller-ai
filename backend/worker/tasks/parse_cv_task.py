from worker.celery_app import celery_app
from worker.langgraph_agents.graph import app_graph
from shared.database import SessionLocal
from shared.models import UserCV, UserSkillProfile, Skill, UserWorkExperience
import asyncio
import logging
import uuid

@celery_app.task(name="worker.tasks.parse_cv_task.parse_cv")
def parse_cv(user_id: str, cv_id: str, file_path: str):
    """
    Task xử lý CV: Trích xuất text -> AI Parsing -> Cập nhật Database
    """
    logging.warning(f"DEBUG: Worker starting parsing for CV ID: {cv_id}")

    # Chạy LangGraph pipeline
    initial_state = {
        "user_id": user_id,
        "cv_id": cv_id,
        "file_path": file_path,
        "raw_text": None,
        "is_ocr": False,
        "parsed_data": None,
        "error": None,
        "status": "started"
    }

    try:
        # LangGraph invoke
        result = asyncio.run(app_graph.ainvoke(initial_state))
        
        if result.get("status") == "completed" and result.get("parsed_data"):
            parsed_data = result["parsed_data"]
            skill_categories = result.get("skill_categories", {})
            logging.warning(f"Pipeline completed. Updating CV record in database...")

            db = SessionLocal()
            try:
                # 1. Tìm bản ghi CV hiện có
                cv_record = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
                if not cv_record:
                    logging.error(f"CV record {cv_id} not found in database!")
                    return {"status": "error", "error": "CV record not found"}

                # Cập nhật thông tin bóc tách
                cv_record.full_name = parsed_data.get("full_name")
                cv_record.summary = parsed_data.get("summary")
                cv_record.raw_text = result.get("raw_text") # Lưu bản thô
                cv_record.experience_years_total = parsed_data.get("experience_years_total", 0)
                cv_record.status = "completed"

                # 2. Xử lý Work History
                db.query(UserWorkExperience).filter(UserWorkExperience.cv_id == cv_record.id).delete()
                work_history = parsed_data.get("work_history", [])
                for job in work_history:
                    new_work = UserWorkExperience(
                        cv_id=cv_record.id,
                        position_name=job.get("position", "Unknown Position"),
                        company_name=job.get("company"),
                        duration_years=job.get("years", 0),
                        description=job.get("description"),
                        skills_context=job.get("skills", [])
                    )
                    db.add(new_work)

                # 3. Xử lý danh sách kỹ năng (Tránh trùng lặp kỹ năng cho cùng 1 CV)
                db.query(UserSkillProfile).filter(UserSkillProfile.cv_id == cv_record.id).delete()
                
                skills_list = parsed_data.get("skills", [])
                for skill_name in skills_list:
                    skill_name_clean = skill_name.strip()
                    db_skill = db.query(Skill).filter(Skill.name == skill_name_clean).first()
                    
                    if not db_skill:
                        category = skill_categories.get(skill_name_clean, "Technology")
                        db_skill = Skill(name=skill_name_clean, category=category)
                        db.add(db_skill)
                        db.flush()
                    
                    # Tìm số năm kinh nghiệm tốt nhất cho skill này từ work_history
                    inferred_years = 0
                    for job in work_history:
                        if any(skill_name_clean.lower() in s.lower() for s in job.get("skills", [])):
                            inferred_years += job.get("years", 0)

                    user_skill = UserSkillProfile(
                        user_id=uuid.UUID(user_id),
                        skill_id=db_skill.id,
                        cv_id=cv_record.id,
                        source="cv",
                        years_exp=inferred_years if inferred_years > 0 else 0
                    )
                    db.add(user_skill)
                
                db.commit()
                # Note: Automatic Gap Analysis is removed to prevent unrequested JD inference.
                # It should be triggered explicitly by the frontend/API when needed.
                
            except Exception as db_err:
                db.rollback()
                logging.error(f"Database update error: {db_err}")
            finally:
                db.close()

            return {
                "status": "success",
                "cv_id": cv_id,
                "parsed_data": parsed_data
            }
        else:
            error_msg = result.get("error", "Unknown error during parsing")
            logging.error(f"Pipeline failed: {error_msg}")
            
            # Cập nhật trạng thái failed vào DB kèm thông báo lỗi
            db = SessionLocal()
            cv_record = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
            if cv_record:
                cv_record.status = "failed"
                cv_record.error_message = error_msg
                db.commit()
            db.close()
            
            return {"status": "failed", "error": error_msg}

    except Exception as e:
        logging.error(f"Task parse_cv encountered exception: {e}")
        return {"status": "error", "error": str(e)}
