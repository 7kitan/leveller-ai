
import asyncio
import os
import sys
import uuid
import json

# Thêm đường dẫn để import được shared và services
sys.path.append("/app")

from shared.database import SessionLocal
from services.analysis_service.gap_calculator import GapCalculator

async def debug():
    db = SessionLocal()
    calculator = GapCalculator(db)
    
    user_id = "b3adeade-b83d-422a-862e-98664488b694"
    cv_id = "e4b68195-8bc9-424d-bda2-cf3a378a86fa"
    jd_text = "Chúng tôi cần tìm một chuyên gia Node.js có kinh nghiệm làm việc với Redis và PostgreSQL. Yêu cầu ít nhất 3 năm kinh nghiệm."
    
    print(f"--- [DEBUG] Starting Test Analysis ---")
    try:
        # 1. Test LLM Extraction
        print(f"1. Testing JD Extraction...")
        reqs = await calculator.extract_requirements_from_text(jd_text)
        print(f"Extracted Requirements: {json.dumps(reqs, indent=2)}")
        
        # 2. Test Gap Calculation
        print(f"2. Testing Gap Calculation...")
        report = await calculator.calculate_gap_v2(user_id, cv_id, reqs)
        print(f"Final Report: {json.dumps(report, indent=2)}")
        
    except Exception as e:
        import traceback
        print(f"!!! Error during analysis: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug())
