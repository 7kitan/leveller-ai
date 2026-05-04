"""
Re-extract skills for a specific job to test skill groups feature.

Usage:
    python scripts/reextract_job.py <job_id>
"""

import os
import sys
import asyncio
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import Job, JobSkillRequirement, Skill
from shared.llm_utils import extract_skills_from_requirements
from shared.skill_extraction import save_job_skills
from shared.database import get_db


async def reextract_job(job_id: str):
    """Re-extract skills for a job"""
    db = next(get_db())
    
    try:
        # 1. Load job
        print(f"\n{'='*60}")
        print(f"Re-extracting skills for job: {job_id}")
        print(f"{'='*60}\n")
        
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            print(f"❌ Job not found: {job_id}")
            return
        
        print(f"📋 Job Title: {job.title_raw}")
        print(f"📅 Created: {job.created_at}")
        
        if not job.raw_text:
            print(f"❌ No raw_text found for this job")
            return
        
        # 2. Extract skills using NEW code with skill groups support
        print(f"\n🔍 Extracting skills from raw text...")
        print(f"   Text length: {len(job.raw_text)} characters")
        
        # Find the relevant section
        if "Blender" in job.raw_text or "Maya" in job.raw_text:
            lines = job.raw_text.split('\n')
            for i, line in enumerate(lines):
                if 'Blender' in line or 'Maya' in line:
                    print(f"\n   📝 Found pattern at line {i}:")
                    print(f"      {line.strip()}")
        
        extracted_result = extract_skills_from_requirements(job.raw_text)
        
        if not extracted_result:
            print(f"❌ No skills extracted")
            return
        
        # Extract skills array from result
        extracted_skills = extracted_result.get("skills", [])
        is_tech_job = extracted_result.get("is_tech_job", True)
        primary_domain = extracted_result.get("primary_domain", "Unknown")
        
        print(f"\n✅ Job Classification:")
        print(f"   Tech Job: {is_tech_job}")
        print(f"   Domain: {primary_domain}")
        print(f"   Extracted {len(extracted_skills)} skills/groups:")
        
        # 3. Display extracted skills
        for i, skill in enumerate(extracted_skills, 1):
            is_group = skill.get("is_group", False)
            if is_group:
                print(f"\n   {i}. 📦 GROUP: {skill.get('skill_name')}")
                print(f"      Strategy: {skill.get('group_strategy')}")
                print(f"      Alternatives: {skill.get('alternative_skills')}")
                print(f"      Min Required: {skill.get('min_required', 1)}")
                print(f"      Mandatory: {skill.get('is_mandatory')}")
                print(f"      Weight: {skill.get('importance_weight')}")
            else:
                print(f"   {i}. {skill.get('skill_name')} (individual)")
        
        # 4. Save to database
        print(f"\n💾 Saving to database...")
        
        # Save extracted_requirements_json
        job.extracted_requirements_json = extracted_skills
        
        # Save to job_skill_requirement table
        saved_count = save_job_skills(
            db=db,
            job=job,
            extracted_skills=extracted_skills,
            commit=True
        )
        
        print(f"✅ Saved {saved_count} records to job_skill_requirement table")
        
        # 5. Verify saved data
        print(f"\n🔍 Verifying saved data...")
        db.refresh(job)
        
        requirements = db.query(JobSkillRequirement, Skill.name).join(
            Skill, JobSkillRequirement.skill_id == Skill.id
        ).filter(JobSkillRequirement.job_id == job.id).all()
        
        print(f"\n📊 Database records ({len(requirements)} total):")
        for jsr, skill_name in requirements:
            if jsr.is_group:
                print(f"\n   📦 {skill_name} (GROUP)")
                print(f"      Strategy: {jsr.group_strategy}")
                print(f"      Alternatives: {jsr.alternative_skills}")
                print(f"      Min Required: {jsr.min_required}")
            else:
                print(f"   • {skill_name}")
        
        print(f"\n{'='*60}")
        print(f"✅ Re-extraction completed successfully!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/reextract_job.py <job_id>")
        print("\nExample:")
        print("  python scripts/reextract_job.py dfc832c9-db82-4a49-ad27-c91b4d93cfd7")
        sys.exit(1)
    
    job_id = sys.argv[1]
    asyncio.run(reextract_job(job_id))
