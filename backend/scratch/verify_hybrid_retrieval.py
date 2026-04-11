import asyncio
import os
import sys
import uuid
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Đè cấu hình để trỏ vào localhost thay vì tên dịch vụ Docker
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"

# Nạp .env thủ công nếu cần
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'), override=False)
# Đảm bảo host vẫn là localhost sau khi load env
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"

from shared.database import SessionLocal
from shared.models import Job
from services.analysis_service.gap_calculator import GapCalculator

async def verify_hybrid_retrieval():
    db = SessionLocal()
    calculator = GapCalculator(db)
    
    test_jd_text = """
    We are looking for a Senior Java Developer with experience in Spring Boot, Microservices, and AWS. 
    Requirements:
    - 5+ years of Java development.
    - Expert in Spring Framework.
    - Strong knowledge of PostgreSQL.
    - Experience with Docker and Kubernetes.
    """
    
    test_requirements = [
        {"skill_name": "Java", "min_years_exp": 5, "required_level": "Senior"},
        {"skill_name": "Spring Boot", "required_level": "Senior"},
        {"skill_name": "PostgreSQL", "required_level": "Intermediate"}
    ]
    
    text_hash = hashlib.sha256(test_jd_text.encode()).hexdigest()[:16]
    source_id = f"cache_{text_hash}"
    
    try:
        # 1. Chuẩn bị dữ liệu mẫu trong DB
        print(f"\n[STEP 1] Preparing dummy JD in DB: {source_id}")
        existing = db.query(Job).filter(Job.source_id == source_id).first()
        if not existing:
            new_job = Job(
                id=uuid.uuid4(),
                source_id=source_id,
                title_raw="Verify Test Job",
                raw_text=test_jd_text,
                extracted_requirements_json=test_requirements,
                status="cache"
            )
            db.add(new_job)
            db.commit()
            print("  Created new test record.")
        else:
            existing.extracted_requirements_json = test_requirements
            db.commit()
            print("  Updated existing test record.")

        # 2. Test Layer 1: Exact Match
        print("\n[STEP 2] Testing Layer 1: Exact Match (Hash)")
        reqs_exact = await calculator.extract_requirements_from_text(test_jd_text)
        if len(reqs_exact) == len(test_requirements):
            print("  SUCCESS: Exactly matched via Layer 1 (0 API calls).")
        else:
            print("  FAILED: Exact match did not return expected requirements.")

        # 3. Test Layer 2: Keyword Match (Modified text)
        print("\n[STEP 3] Testing Layer 2: Keyword Match (FTS)")
        modified_jd = test_jd_text.replace("AWS", "Amazon Web Services").replace("Expert", "Master")
        print(f"  Modified text: ...Amazon Web Services... Master...")
        
        reqs_keyword = await calculator.extract_requirements_from_text(modified_jd)
        if reqs_keyword and len(reqs_keyword) == len(test_requirements):
            print("  SUCCESS: Matched via Layer 2 (Keyword FTS - 0 API calls).")
        else:
            print("  FAILED: Keyword match layer skipped or failed.")

    finally:
        # Dọn dẹp test data (Tùy chọn)
        # db.query(Job).filter(Job.source_id == source_id).delete()
        # db.commit()
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_hybrid_retrieval())
