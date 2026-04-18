import os
import sys
from sqlalchemy import text
from dotenv import load_dotenv

# Thêm đường dẫn backend vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database import engine

def add_hnsw_index():
    print("Connecting to database...")
    try:
        with engine.connect() as conn:
            # 1. Đảm bảo extension vector tồn tại
            print("Checking for pgvector extension...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # 2. Xóa index cũ nếu có (để tránh lỗi nếu chạy lại)
            print("Cleaning up old indexes if any...")
            conn.execute(text("DROP INDEX IF EXISTS idx_jobs_vector_hnsw;"))
            
            # 3. Tạo HNSW index
            # Lưu ý: vector_cosine_ops phù hợp với 1 - (vector <=> :vec)
            print("Creating HNSW index on jobs.vector (this may take a few seconds)...")
            conn.execute(text("""
                CREATE INDEX idx_jobs_vector_hnsw 
                ON jobs 
                USING hnsw (vector vector_cosine_ops);
            """))
            conn.commit()
            print("Successfully created HNSW index on jobs.vector!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    add_hnsw_index()
