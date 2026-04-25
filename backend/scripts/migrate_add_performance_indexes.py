"""
Database Migration: Add Missing Indexes for Performance

This migration adds indexes to frequently queried columns to improve query performance.
"""
import logging
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment."""
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "career_advisor")
    
    return f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


def add_indexes():
    """Add missing indexes to improve query performance."""
    
    engine = create_engine(get_database_url())
    
    # List of indexes to add
    indexes = [
        # UserFeedback table - analysis_id used in queries
        {
            "name": "idx_user_feedback_analysis_id",
            "table": "user_feedback",
            "column": "analysis_id",
            "description": "Index on analysis_id for feedback queries"
        },
        # MarketSkillStats table - category used for filtering
        {
            "name": "idx_market_skill_stats_category",
            "table": "market_skill_stats",
            "column": "category",
            "description": "Index on category for skill filtering"
        },
        # UserCV table - cv_parsed_at used in queries
        {
            "name": "idx_user_cv_parsed_at",
            "table": "user_cv",
            "column": "cv_parsed_at",
            "description": "Index on cv_parsed_at for CV status queries"
        },
        # UserCV table - user_id + status composite index
        {
            "name": "idx_user_cv_user_status",
            "table": "user_cv",
            "columns": ["user_id", "status"],
            "description": "Composite index for user CV queries by status"
        },
        # UserAnalysis table - user_id + created_at for history queries
        {
            "name": "idx_user_analysis_user_created",
            "table": "user_analysis",
            "columns": ["user_id", "created_at"],
            "description": "Composite index for user analysis history"
        },
        # Jobs table - status + created_at for active job queries
        {
            "name": "idx_jobs_status_created",
            "table": "jobs",
            "columns": ["status", "created_at"],
            "description": "Composite index for active job listings"
        },
        # Jobs table - title_category for filtering
        {
            "name": "idx_jobs_title_category",
            "table": "jobs",
            "column": "title_category",
            "description": "Index on title_category for job filtering"
        },
        # Courses table - is_active + level for filtering
        {
            "name": "idx_courses_active_level",
            "table": "courses",
            "columns": ["is_active", "level"],
            "description": "Composite index for course filtering"
        },
        # LLMLogs table - user_id + created_at for usage tracking
        {
            "name": "idx_llm_logs_user_created",
            "table": "llm_logs",
            "columns": ["user_id", "created_at"],
            "description": "Composite index for user token usage queries"
        }
    ]
    
    with engine.connect() as conn:
        for idx in indexes:
            try:
                # Check if index already exists
                check_query = text("""
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = :index_name
                """)
                result = conn.execute(check_query, {"index_name": idx["name"]}).fetchone()
                
                if result:
                    logger.info(f"✓ Index {idx['name']} already exists, skipping")
                    continue
                
                # Create index
                if "columns" in idx:
                    # Composite index
                    columns_str = ", ".join(idx["columns"])
                    create_query = text(f"""
                        CREATE INDEX {idx['name']} 
                        ON {idx['table']} ({columns_str})
                    """)
                else:
                    # Single column index
                    create_query = text(f"""
                        CREATE INDEX {idx['name']} 
                        ON {idx['table']} ({idx['column']})
                    """)
                
                conn.execute(create_query)
                conn.commit()
                logger.info(f"✓ Created index: {idx['name']} - {idx['description']}")
                
            except Exception as e:
                logger.error(f"✗ Failed to create index {idx['name']}: {e}")
                conn.rollback()
    
    logger.info("=" * 80)
    logger.info("Index migration completed!")
    logger.info("=" * 80)


if __name__ == "__main__":
    logger.info("Starting database index migration...")
    add_indexes()
