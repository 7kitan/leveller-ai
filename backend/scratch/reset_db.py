import os
import sys
from sqlalchemy import create_engine
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.models import Base
from shared.database import engine

def clear_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables with new schema...")
    Base.metadata.create_all(bind=engine)
    print("Done.")

if __name__ == "__main__":
    load_dotenv()
    clear_db()
