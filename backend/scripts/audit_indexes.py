#!/usr/bin/env python3
"""
Database Index Audit Report Generator

Generates a comprehensive report of all indexes in the database,
categorized by type and purpose.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from shared.config_utils import config_manager
from tabulate import tabulate

def main():
    db_url = config_manager.get_setting("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found")
        return 1
    
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Get all indexes
        result = conn.execute(text("""
            SELECT 
                t.tablename,
                i.indexname,
                CASE 
                    WHEN i.indexname LIKE 'idx_%' THEN 'Performance (Custom)'
                    WHEN i.indexname LIKE 'ix_%' THEN 'SQLAlchemy (Auto)'
                    WHEN i.indexname LIKE '%_pkey' THEN 'Primary Key'
                    WHEN i.indexname LIKE '%_key' THEN 'Unique Constraint'
                    WHEN i.indexname LIKE 'uq_%' THEN 'Unique Constraint'
                    ELSE 'Other'
                END as index_type,
                CASE 
                    WHEN i.indexdef LIKE '%USING gin%' THEN 'GIN'
                    WHEN i.indexdef LIKE '%USING hnsw%' THEN 'HNSW (Vector)'
                    WHEN i.indexdef LIKE '%USING btree%' THEN 'B-Tree'
                    ELSE 'Unknown'
                END as index_method,
                pg_size_pretty(pg_relation_size(i.indexrelid::regclass)) as size
            FROM pg_indexes i
            JOIN pg_tables t ON i.tablename = t.tablename
            WHERE i.schemaname = 'public'
            ORDER BY t.tablename, i.indexname
        """))
        
        indexes = result.fetchall()
        
        # Summary by table
        print("\n" + "="*80)
        print("DATABASE INDEX AUDIT REPORT")
        print("="*80 + "\n")
        
        result = conn.execute(text("""
            SELECT 
                tablename,
                COUNT(*) as total_indexes,
                COUNT(CASE WHEN indexname LIKE 'idx_%' THEN 1 END) as performance_indexes,
                COUNT(CASE WHEN indexname LIKE 'ix_%' THEN 1 END) as sqlalchemy_indexes,
                COUNT(CASE WHEN indexname LIKE '%_pkey' OR indexname LIKE '%_key' OR indexname LIKE 'uq_%' THEN 1 END) as constraint_indexes
            FROM pg_indexes
            WHERE schemaname = 'public'
            GROUP BY tablename
            ORDER BY tablename
        """))
        
        summary = result.fetchall()
        
        print("📊 INDEX SUMMARY BY TABLE\n")
        headers = ["Table", "Total", "Performance", "SQLAlchemy", "Constraints"]
        print(tabulate(summary, headers=headers, tablefmt="grid"))
        
        # Detailed breakdown
        print("\n\n📋 DETAILED INDEX BREAKDOWN\n")
        
        current_table = None
        for idx in indexes:
            if idx[0] != current_table:
                current_table = idx[0]
                print(f"\n{'─'*80}")
                print(f"TABLE: {current_table}")
                print(f"{'─'*80}")
            
            print(f"  • {idx[1]:<40} [{idx[2]:<25}] {idx[3]:<15} ({idx[4]})")
        
        # Index type summary
        result = conn.execute(text("""
            SELECT 
                CASE 
                    WHEN indexname LIKE 'idx_%' THEN 'Performance (Custom)'
                    WHEN indexname LIKE 'ix_%' THEN 'SQLAlchemy (Auto)'
                    WHEN indexname LIKE '%_pkey' THEN 'Primary Key'
                    WHEN indexname LIKE '%_key' OR indexname LIKE 'uq_%' THEN 'Unique Constraint'
                    ELSE 'Other'
                END as category,
                COUNT(*) as count
            FROM pg_indexes
            WHERE schemaname = 'public'
            GROUP BY category
            ORDER BY count DESC
        """))
        
        type_summary = result.fetchall()
        
        print("\n\n" + "="*80)
        print("INDEX TYPE SUMMARY")
        print("="*80 + "\n")
        print(tabulate(type_summary, headers=["Category", "Count"], tablefmt="grid"))
        
        # Critical indexes check
        print("\n\n" + "="*80)
        print("CRITICAL INDEX VERIFICATION")
        print("="*80 + "\n")
        
        critical_checks = [
            ("courses", "idx_courses_tags_gin", "GIN index for tags array search"),
            ("courses", "idx_courses_skills_raw_gin", "GIN index for skills JSON search"),
            ("courses", "idx_courses_vector_hnsw", "HNSW index for vector similarity"),
            ("courses", "idx_courses_title_trgm", "Trigram index for title ILIKE"),
            ("job_skill_requirement", "idx_job_skill_req_job_id", "FK index for job_id"),
            ("job_skill_requirement", "idx_job_skill_req_skill_id", "FK index for skill_id"),
            ("user_skill_profile", "idx_user_skill_profile_user_id", "Index for user_id"),
            ("skills", "idx_skills_vector_hnsw", "HNSW index for skill vectors"),
        ]
        
        for table, index_name, description in critical_checks:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND tablename = :table 
                AND indexname = :index
            """), {"table": table, "index": index_name})
            
            exists = result.scalar() > 0
            status = "✅" if exists else "❌"
            print(f"{status} {table}.{index_name:<40} - {description}")
        
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    sys.exit(main())
