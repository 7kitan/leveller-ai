import os
import sys
from sqlalchemy import text
from sqlalchemy.inspection import inspect

# Thêm đường dẫn backend vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database import engine
from shared.models import Job

def sync_indexes():
    print("Connecting to database...")
    inspector = inspect(engine)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('jobs')]
    
    print(f"Existing indexes: {existing_indexes}")
    
    # Danh sách các cột cần đánh index (từ models.py mới cập nhật)
    columns_to_index = [
        'title_category', 'domain_role', 'company_name', 
        'min_salary_vnd', 'max_salary_vnd', 
        'location_normalized', 'location_district'
    ]
    
    try:
        with engine.connect() as conn:
            for col in columns_to_index:
                index_name = f"ix_jobs_{col}"
                if index_name not in existing_indexes:
                    print(f"Creating index {index_name}...")
                    conn.execute(text(f"CREATE INDEX {index_name} ON jobs ({col});"))
                    conn.commit()
                else:
                    print(f"Index {index_name} already exists.")
            print("Successfully synced all B-tree indexes!")
    except Exception as e:
        print(f"Error syncing indexes: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sync_indexes()
