from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging
from dotenv import load_dotenv

load_dotenv()

from shared.logging_utils import setup_logger

logger = setup_logger("database", log_file="db.log")

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB", "career_advisor")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# SECURITY: Enforce password in production
if not POSTGRES_PASSWORD:
    logger.critical("=" * 80)
    logger.critical("SECURITY WARNING: POSTGRES_PASSWORD not set!")
    logger.critical("Using default password is a security risk.")
    logger.critical("=" * 80)
    
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        logger.critical("FATAL: Cannot start in production without POSTGRES_PASSWORD!")
        import sys
        sys.exit(1)
    
    POSTGRES_PASSWORD = "postgres"  # Development fallback only

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# PERFORMANCE FIX: Configure connection pooling
# pool_size: Number of connections to maintain in the pool
# max_overflow: Maximum number of connections that can be created beyond pool_size
# pool_pre_ping: Verify connections before using them (prevents stale connections)
# pool_recycle: Recycle connections after this many seconds (prevents timeout issues)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,              # Maintain 10 connections in pool
    max_overflow=20,           # Allow up to 30 total connections (10 + 20)
    pool_pre_ping=True,        # Test connections before use
    pool_recycle=3600,         # Recycle connections after 1 hour
    echo=False,                # Set to True for SQL query logging (debug only)
    connect_args={
        "connect_timeout": 10,  # Connection timeout in seconds
        "options": "-c timezone=utc"  # Set timezone to UTC
    }
)

logger.info(f"Database engine initialized with connection pooling: pool_size=10, max_overflow=20")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables and run migrations. Should be called during app startup."""
    from . import models # Ensure models are registered
    Base.metadata.create_all(bind=engine)
    
    # Run pending migrations
    try:
        from scripts.run_migrations import run_migrations
        logger.info("Running database migrations...")
        run_migrations()
    except Exception as e:
        logger.warning(f"Migration runner not available or failed: {e}")
        logger.warning("Please run migrations manually: python scripts/run_migrations.py")
