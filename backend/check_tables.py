import os
from dotenv import load_dotenv

load_dotenv()
from sqlalchemy import create_engine, text

eng = create_engine(
    "postgresql://"
    + os.getenv("POSTGRES_USER")
    + ":"
    + os.getenv("POSTGRES_PASSWORD")
    + "@"
    + os.getenv("POSTGRES_HOST")
    + ":5432/"
    + os.getenv("POSTGRES_DB")
)
print("DB:", os.getenv("POSTGRES_DB"))
print("HOST:", os.getenv("POSTGRES_HOST"))
with eng.connect() as conn:
    # Test ORM-style UUID filter
    from shared.database import SessionLocal
    from shared.models import UserSkillProfile, Skill

    db = SessionLocal()
    cv_id = "286eb429-3c2c-4859-8013-9155736d097c"
    try:
        result = (
            db.query(UserSkillProfile, Skill.name)
            .join(Skill)
            .filter(UserSkillProfile.cv_id == cv_id)
            .limit(3)
            .all()
        )
        print("ORM query OK, rows:", len(result))
        for profile, name in result:
            print(" -", name, "| years:", profile.years_exp)
    except Exception as e:
        print("ORM ERROR:", type(e).__name__, e)
    db.close()
