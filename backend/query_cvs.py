import os
from dotenv import load_dotenv

load_dotenv()
from sqlalchemy import create_engine, text, inspect

engine = create_engine(
    "postgresql://"
    + os.getenv("POSTGRES_USER")
    + ":"
    + os.getenv("POSTGRES_PASSWORD")
    + "@"
    + os.getenv("POSTGRES_HOST")
    + ":5432/"
    + os.getenv("POSTGRES_DB")
)
with engine.connect() as conn:
    # Check tables
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("Tables:", tables)
    if "user_cvs" in tables:
        r = conn.execute(
            text(
                "SELECT id, user_id, status, created_at FROM user_cvs ORDER BY created_at DESC LIMIT 5"
            )
        )
        rows = r.fetchall()
        print("Total CVs found:", len(rows))
        for row in rows:
            print("id:", row[0], "| status:", row[2], "| created:", row[3])
    else:
        print("user_cvs table NOT FOUND")
