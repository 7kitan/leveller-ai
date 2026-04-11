import sys
import os

# Thêm thư mục hiện tại vào path để import được shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from shared.database import engine, SQLALCHEMY_DATABASE_URL
from shared.models import Base

def sync():
    print("Syncing database schema...")
    try:
        # Thử với engine mặc định trước
        Base.metadata.create_all(bind=engine)
        print("Done! Database tables created/verified via default engine.")
    except Exception as e:
        if "could not translate host name" in str(e) or "connection refused" in str(e).lower():
            print("Default host unreachable. Attempting connection via localhost...")
            try:
                # Force localhost for local development outside Docker
                local_url = SQLALCHEMY_DATABASE_URL.replace("@advisor_db:", "@localhost:")
                local_engine = create_engine(local_url)
                Base.metadata.create_all(bind=local_engine)
                print("Done! Database tables created/verified via localhost.")
            except Exception as local_e:
                print(f"Failed to connect via localhost as well: {local_e}")
        else:
            print(f"Error: {e}")

if __name__ == "__main__":
    sync()
