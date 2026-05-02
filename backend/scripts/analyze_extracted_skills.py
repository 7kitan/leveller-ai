"""
Analyze extracted skills from job_skill_requirement table to identify issues.
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from shared.database import SessionLocal
import re

def analyze_skills():
    """Analyze extracted skills to identify quality issues."""
    
    db = SessionLocal()
    try:
        print("=" * 80)
        print("SKILL EXTRACTION ANALYSIS")
        print("=" * 80)
        
        # 1. Top 30 most common skills
        print("\n1. TOP 30 MOST COMMON SKILLS:")
        print("-" * 80)
        result = db.execute(text("""
            SELECT skill_name, category, COUNT(*) as usage_count 
            FROM job_skill_requirement 
            GROUP BY skill_name, category 
            ORDER BY usage_count DESC 
            LIMIT 30
        """))
        for row in result:
            print(f"  {row.skill_name:40} | {row.category:25} | {row.usage_count:3} jobs")
        
        # 2. Category distribution
        print("\n2. CATEGORY DISTRIBUTION:")
        print("-" * 80)
        result = db.execute(text("""
            SELECT category, COUNT(*) as count 
            FROM job_skill_requirement 
            GROUP BY category 
            ORDER BY count DESC
        """))
        for row in result:
            print(f"  {row.category:40} | {row.count:4} occurrences")
        
        # 3. Vietnamese skills (contains Vietnamese characters)
        print("\n3. VIETNAMESE SKILL NAMES (Sample):")
        print("-" * 80)
        result = db.execute(text("""
            SELECT DISTINCT skill_name, category 
            FROM job_skill_requirement 
            WHERE skill_name ~ '[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]'
            LIMIT 30
        """))
        vietnamese_count = 0
        for row in result:
            print(f"  {row.skill_name:50} | {row.category}")
            vietnamese_count += 1
        
        # Count total Vietnamese skills
        total_vn = db.execute(text("""
            SELECT COUNT(DISTINCT skill_name) 
            FROM job_skill_requirement 
            WHERE skill_name ~ '[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]'
        """)).scalar()
        print(f"\n  Total Vietnamese skills: {total_vn}")
        
        # 4. Suspiciously long skill names (likely junk)
        print("\n4. SUSPICIOUSLY LONG SKILL NAMES (>50 chars):")
        print("-" * 80)
        result = db.execute(text("""
            SELECT DISTINCT skill_name, LENGTH(skill_name) as len, category 
            FROM job_skill_requirement 
            WHERE LENGTH(skill_name) > 50 
            ORDER BY len DESC 
            LIMIT 20
        """))
        for row in result:
            print(f"  [{row.len:3}] {row.skill_name[:70]}... | {row.category}")
        
        # 5. Skills with numbers (might be junk like "5+ years")
        print("\n5. SKILLS WITH NUMBERS (Potential Junk):")
        print("-" * 80)
        result = db.execute(text("""
            SELECT DISTINCT skill_name, category 
            FROM job_skill_requirement 
            WHERE skill_name ~ '[0-9]' 
            LIMIT 20
        """))
        for row in result:
            print(f"  {row.skill_name:50} | {row.category}")
        
        # 6. Soft skills (often too generic)
        print("\n6. SOFT SKILLS (Often Too Generic):")
        print("-" * 80)
        result = db.execute(text("""
            SELECT DISTINCT skill_name, COUNT(*) as count 
            FROM job_skill_requirement 
            WHERE category ILIKE '%soft%' 
            GROUP BY skill_name 
            ORDER BY count DESC 
            LIMIT 20
        """))
        for row in result:
            print(f"  {row.skill_name:50} | {row.count:3} jobs")
        
        # 7. Total stats
        print("\n7. OVERALL STATISTICS:")
        print("-" * 80)
        total_skills = db.execute(text("SELECT COUNT(*) FROM job_skill_requirement")).scalar()
        unique_skills = db.execute(text("SELECT COUNT(DISTINCT skill_name) FROM job_skill_requirement")).scalar()
        total_jobs = db.execute(text("SELECT COUNT(DISTINCT job_id) FROM job_skill_requirement")).scalar()
        
        print(f"  Total skill records: {total_skills}")
        print(f"  Unique skill names: {unique_skills}")
        print(f"  Jobs with skills: {total_jobs}")
        print(f"  Avg skills per job: {total_skills / total_jobs if total_jobs > 0 else 0:.1f}")
        
        # 8. Sample job with extracted skills
        print("\n8. SAMPLE JOB WITH EXTRACTED SKILLS:")
        print("-" * 80)
        result = db.execute(text("""
            SELECT j.title_raw, j.id, 
                   array_agg(jsr.skill_name ORDER BY jsr.importance_weight DESC) as skills
            FROM job j
            JOIN job_skill_requirement jsr ON j.id = jsr.job_id
            WHERE j.extracted_requirements_json IS NOT NULL
            GROUP BY j.id, j.title_raw
            LIMIT 1
        """))
        for row in result:
            print(f"  Job: {row.title_raw}")
            print(f"  ID: {row.id}")
            print(f"  Skills: {', '.join(row.skills[:15])}...")
    
    finally:
        db.close()

if __name__ == "__main__":
    analyze_skills()
