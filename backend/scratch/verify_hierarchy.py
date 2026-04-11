
import asyncio
import os
import sys
import uuid
import json

sys.path.append("/app")

from shared.database import SessionLocal
from services.analysis_service.gap_calculator import GapCalculator
from shared.models import UserSkillProfile, Skill

async def verify_pure_graph_logic():
    db = SessionLocal()
    calculator = GapCalculator(db)
    
    cv_id = "e4b68195-8bc9-424d-bda2-cf3a378a86fa"
    
    # 1. Xóa mọi kỹ năng có tên "Nodejs" hoặc "Node.js" khỏi CV này để test Graph
    node_skills = db.query(Skill).filter(Skill.name.ilike("%Node%")).all()
    node_ids = [s.id for s in node_skills]
    db.query(UserSkillProfile).filter(
        UserSkillProfile.cv_id == uuid.UUID(cv_id),
        UserSkillProfile.skill_id.in_(node_ids)
    ).delete(synchronize_session=False)
    db.commit()

    # 2. Đảm bảo CV có Express.js với 2 năm kinh nghiệm
    express_skill = db.query(Skill).filter(Skill.name.ilike("Express.js")).first()
    if not express_skill:
        express_skill = Skill(id=uuid.uuid4(), name="Express.js")
        db.add(express_skill)
        db.commit()
    
    db.add(UserSkillProfile(
        id=uuid.uuid4(),
        cv_id=uuid.UUID(cv_id),
        skill_id=express_skill.id,
        years_exp=2.0
    ))
    db.commit()

    # 3. Chạy phân tích Gap cho Node.js (Vốn đã bị xóa khỏi CV)
    jd_reqs = [{"skill_name": "Node.js", "importance_weight": 10, "min_years_exp": 3, "is_mandatory": True}]

    print(f"--- [VERIFY] Pure Graph: User has ONLY Express.js -> JD needs Node.js ---")
    try:
        report = await calculator.calculate_gap_v2("dummy", cv_id, jd_reqs)
        print(f"Analysis Result: {json.dumps(report, indent=2)}")
        
        # Kiểm tra xem có khớp qua Graph không
        partial_matches = report["breakdown"]["partial"]
        found_graph = any(m["type"] == "graph" and m["matched_by"] == "Express.js" for m in partial_matches)
        
        if found_graph:
            print("✅ SUCCESS: Neo4j and AI now understand Express.js is a key component of Node.js!")
        else:
            print("❌ FAILURE: Knowledge Graph connection not found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_pure_graph_logic())
