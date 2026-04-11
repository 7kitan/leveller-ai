import json
import os
import logging
import asyncio
import uuid
import sys
from dotenv import load_dotenv
import openai

# 1. Cấu hình môi trường để kết nối từ Host tới Docker
os.environ["POSTGRES_HOST"] = "localhost"

# Thêm đường dẫn backend vào sys.path để import được shared
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from shared.database import SessionLocal, engine, Base
from shared.models import Job, Skill, JobSkillRequirement

# 2. Cấu hình Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv(dotenv_path="backend/.env")
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

async def parse_job_skills(text: str, title: str):
    prompt = f"Trích xuất danh sách các kỹ năng kỹ thuật (hard skills) từ yêu cầu công việc '{title}':\n{text}\n\nTrả về định dạng JSON: {{\"skills\": [\"tên_kỹ_năng\"], \"exp\": số_năm_kinh_nghiệm_hoặc_null}}"
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Lỗi AI cho job '{title}': {e}")
        return None

async def main():
    # 1. Khởi tạo Bảng và Extension
    logger.info("Đang kiểm tra extension và khởi tạo database tables...")
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    input_file = "dataset/jobs_dataset.json"
    
    if not os.path.exists(input_file):
        logger.error(f"Không tìm thấy file: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        jobs_data = json.load(f)

    # Giới hạn 3 jobs theo yêu cầu
    jobs_data = jobs_data[:3]

    logger.info(f"Bắt đầu xử lý thử nghiệm {len(jobs_data)} jobs từ dataset...")

    for job_data in jobs_data:
        try:
            # Kiểm tra xem job đã tồn tại chưa
            source_id = job_data.get("source_id")
            existing_job = db.query(Job).filter(Job.source_id == source_id).first()
            if existing_job:
                logger.info(f"Bỏ qua Job đã tồn tại: {job_data['title']}")
                continue

            # 1. Parse bằng AI
            logger.info(f"Đang phân tích AI cho: {job_data['title']}...")
            parsed = await parse_job_skills(job_data.get('yeu_cau_ung_vien', ''), job_data['title'])
            
            if not parsed:
                continue

            # 2. Lưu Job vào DB
            job = Job(
                source_id=source_id or str(uuid.uuid4()),
                title_raw=job_data['title'],
                company_name=job_data.get('company'),
                raw_text=job_data.get('mo_ta_cong_viec'),
                source_url=job_data.get('url'),
                status="active"
            )
            db.add(job)
            db.flush() # Để lấy job.id
            
            # 3. Lưu Skills và Requirements
            skills_count = 0
            for skill_name in parsed.get("skills", []):
                # Tìm hoặc tạo skill chuẩn
                skill = db.query(Skill).filter(Skill.name == skill_name).first()
                if not skill:
                    skill = Skill(name=skill_name)
                    db.add(skill)
                    db.flush()
                
                # Tạo liên kết requirement
                req = JobSkillRequirement(
                    job_id=job.id,
                    skill_id=skill.id,
                    importance_weight=3,
                    min_years_exp=parsed.get("exp")
                )
                db.add(req)
                skills_count += 1
            
            db.commit()
            logger.info(f" -> Đã lưu Job '{job_data['title']}' với {skills_count} kỹ năng.")
        except Exception as e:
            db.rollback()
            logger.error(f"Lỗi xử lý job '{job_data.get('title')}': {e}")

    db.close()
    logger.info("--- QUÁ TRÌNH NHẬP DỮ LIỆU HOÀN THÀNH ---")

if __name__ == "__main__":
    asyncio.run(main())
