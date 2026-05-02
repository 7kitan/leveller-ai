"""
Debug script to test skill extraction for a specific job.

Usage:
    python scripts/debug_job_extraction.py <job_id>
    python scripts/debug_job_extraction.py --url "https://www.topcv.vn/viec-lam/..."
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database import SessionLocal
from shared.models import Job
from shared.llm_utils import extract_skills_from_requirements
from services.analysis_service.engine.retriever import JDRequirementRetriever
import asyncio
import json


def debug_job_by_id(job_id: str):
    """Debug skill extraction for a job by ID."""
    db = SessionLocal()
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            print(f"❌ Job not found: {job_id}")
            return
        
        print("=" * 70)
        print(f"JOB FOUND: {job.title}")
        print("=" * 70)
        print(f"ID: {job.id}")
        print(f"URL: {job.source_url}")
        print(f"Created: {job.created_at}")
        print(f"Is Tech Job: {job.is_tech_job}")
        print(f"Primary Domain: {job.primary_domain}")
        
        # Check requirements text
        print("\n" + "=" * 70)
        print("REQUIREMENTS TEXT")
        print("=" * 70)
        if job.requirements:
            print(f"Length: {len(job.requirements)} chars")
            print(f"Preview:\n{job.requirements[:500]}...")
        else:
            print("❌ NULL - No requirements text!")
            return
        
        # Check extracted requirements
        print("\n" + "=" * 70)
        print("EXTRACTED REQUIREMENTS (Current)")
        print("=" * 70)
        if job.extracted_requirements_json:
            print(json.dumps(job.extracted_requirements_json, indent=2, ensure_ascii=False))
            
            # Count skills by type
            technical_count = 0
            soft_count = 0
            for req in job.extracted_requirements_json:
                skill_type = req.get("skill_type", "technical")
                if skill_type == "soft":
                    soft_count += 1
                else:
                    technical_count += 1
            
            print(f"\n✓ Total requirements: {len(job.extracted_requirements_json)}")
            print(f"  - Technical: {technical_count}")
            print(f"  - Soft: {soft_count}")
        else:
            print("❌ NULL - No skills extracted!")
        
        # Test extraction with current code
        print("\n" + "=" * 70)
        print("TEST EXTRACTION (Re-run with current code)")
        print("=" * 70)
        
        print("\n[1] Testing llm_utils.extract_skills_from_requirements()...")
        result = extract_skills_from_requirements(job.requirements)
        
        if result:
            print(f"✓ Classification:")
            print(f"  - Is Tech Job: {result['is_tech_job']}")
            print(f"  - Confidence: {result['confidence']}")
            print(f"  - Domain: {result['primary_domain']}")
            print(f"  - Reason: {result['classification_reason']}")
            
            skills = result.get('skills', [])
            technical_skills = [s for s in skills if s.get('skill_type') == 'technical']
            soft_skills = [s for s in skills if s.get('skill_type') == 'soft']
            
            print(f"\n✓ Extracted {len(skills)} skills:")
            print(f"  - Technical: {len(technical_skills)}")
            print(f"  - Soft: {len(soft_skills)}")
            
            print(f"\n✓ Technical Skills (first 10):")
            for skill in technical_skills[:10]:
                print(f"  - {skill['skill_name']} ({skill['category']}) | "
                      f"Level: {skill.get('required_level', 'N/A')} | "
                      f"Weight: {skill['importance_weight']}")
            
            print(f"\n✓ Soft Skills:")
            for skill in soft_skills:
                print(f"  - {skill['skill_name']} ({skill['category']}) | "
                      f"Weight: {skill['importance_weight']}")
        else:
            print("❌ Extraction failed!")
        
        print("\n[2] Testing JDRequirementRetriever._ai_extract()...")
        retriever = JDRequirementRetriever()
        requirements = asyncio.run(retriever._ai_extract(job.requirements))
        
        if requirements:
            print(f"✓ Extracted {len(requirements)} requirements")
            
            # Count by type
            technical_count = 0
            soft_count = 0
            for req in requirements:
                skill_type = req.get("skill_type", "technical")
                if skill_type == "soft":
                    soft_count += 1
                else:
                    technical_count += 1
            
            print(f"  - Technical: {technical_count}")
            print(f"  - Soft: {soft_count}")
            
            print(f"\nFirst 5 requirements:")
            for req in requirements[:5]:
                req_type = req.get("type", "skill")
                if req_type == "skill":
                    skill_name = req.get("skill", "N/A")
                    skill_type = req.get("skill_type", "technical")
                    print(f"  - {skill_name} ({skill_type})")
                else:
                    group_name = req.get("group_name", "N/A")
                    print(f"  - GROUP: {group_name}")
        else:
            print("❌ Extraction failed!")
        
    finally:
        db.close()


def debug_job_by_url(url: str):
    """Debug skill extraction for a job by URL."""
    db = SessionLocal()
    
    try:
        job = db.query(Job).filter(Job.source_url.like(f"%{url}%")).first()
        
        if not job:
            print(f"❌ Job not found with URL containing: {url}")
            return
        
        debug_job_by_id(str(job.id))
        
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/debug_job_extraction.py <job_id>")
        print("  python scripts/debug_job_extraction.py --url <url_fragment>")
        sys.exit(1)
    
    if sys.argv[1] == "--url":
        if len(sys.argv) < 3:
            print("Error: --url requires a URL fragment")
            sys.exit(1)
        debug_job_by_url(sys.argv[2])
    else:
        debug_job_by_id(sys.argv[1])
