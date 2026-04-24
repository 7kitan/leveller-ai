"""
Skill extraction and management utilities.
Handles extracting skills from job requirements and managing skill database.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from shared.models import Skill, Job, JobSkillRequirement
from shared.llm_utils import extract_skills_from_requirements, get_embedding, build_jd_skill_context
import uuid

logger = logging.getLogger("skill_extraction")


def find_or_create_skill(db: Session, skill_name: str, category: str = None) -> Skill:
    """
    Find existing skill by name (case-insensitive) or create new one.
    
    Args:
        db: Database session
        skill_name: Name of the skill
        category: Category of the skill (optional)
    
    Returns:
        Skill object (existing or newly created)
    """
    # Normalize skill name
    normalized_name = skill_name.strip().title()
    
    # Try to find existing skill (case-insensitive)
    existing = db.query(Skill).filter(
        Skill.name.ilike(normalized_name)
    ).first()
    
    if existing:
        logger.debug(f"[SKILL DB] Found existing skill: {existing.name}")
        return existing
    
    # Create new skill with embedding
    logger.info(f"[SKILL DB] Creating new skill: {normalized_name} ({category})")
    
    # Generate embedding for skill
    skill_context = f"Skill: {normalized_name}"
    if category:
        skill_context += f". Category: {category}"
    
    vector = get_embedding(skill_context, log_cost=False)  # Don't log cost for individual skills
    
    new_skill = Skill(
        id=uuid.uuid4(),
        name=normalized_name,
        category=category,
        vector=vector
    )
    
    db.add(new_skill)
    db.flush()  # Get ID without committing
    
    return new_skill


def save_job_skills(
    db: Session, 
    job: Job, 
    extracted_skills: List[Dict[str, Any]],
    commit: bool = True
) -> int:
    """
    Save extracted skills as JobSkillRequirement records with embeddings.
    
    Args:
        db: Database session
        job: Job object
        extracted_skills: List of skill dicts from LLM extraction
        commit: Whether to commit the transaction
    
    Returns:
        Number of skills saved
    """
    if not extracted_skills:
        logger.warning(f"[SKILL DB] No skills to save for job {job.id}")
        return 0
    
    saved_count = 0
    
    # Delete existing skills for this job (if re-processing)
    db.query(JobSkillRequirement).filter(
        JobSkillRequirement.job_id == job.id
    ).delete()
    
    for skill_data in extracted_skills:
        try:
            skill_name = skill_data.get("skill_name")
            if not skill_name:
                logger.warning(f"[SKILL DB] Skipping skill with no name: {skill_data}")
                continue
            
            # Find or create skill
            skill = find_or_create_skill(
                db, 
                skill_name, 
                skill_data.get("category")
            )
            
            # Build embedding context for this specific requirement
            required_level = skill_data.get("required_level")
            min_years = skill_data.get("min_years_exp", 0)
            
            embedding_ctx = build_jd_skill_context(
                skill_name=skill_name,
                level=required_level or "",
                years=min_years,
                domain=job.domain_role or ""
            )
            
            # Generate embedding for this specific job-skill requirement
            vector = get_embedding(embedding_ctx, log_cost=False)
            
            # Create JobSkillRequirement
            job_skill = JobSkillRequirement(
                id=uuid.uuid4(),
                job_id=job.id,
                skill_id=skill.id,
                required_level=required_level,
                min_years_exp=min_years,
                is_mandatory=skill_data.get("is_mandatory", True),
                importance_weight=skill_data.get("importance_weight", 5),
                embedding_context=embedding_ctx,
                vector=vector
            )
            
            db.add(job_skill)
            saved_count += 1
            
            logger.debug(f"[SKILL DB] Saved: {skill_name} (Level: {required_level}, Years: {min_years})")
            
        except Exception as e:
            logger.error(f"[SKILL DB] Error saving skill {skill_data.get('skill_name')}: {e}")
            continue
    
    if commit:
        db.commit()
        logger.info(f"[SKILL DB] ✓ Saved {saved_count} skills for job {job.id}")
    
    return saved_count


def extract_and_save_job_skills(
    db: Session,
    job: Job,
    model_key: str = "ai_model",
    commit: bool = True,
    user_id: Optional[str] = None
) -> Optional[int]:
    """
    Complete workflow: Extract skills from job requirements and save to database.
    
    Args:
        db: Database session
        job: Job object with requirements field
        model_key: LLM model to use for extraction
        commit: Whether to commit the transaction
    
    Returns:
        Number of skills saved, or None if extraction failed
    """
    if not job.requirements:
        logger.warning(f"[SKILL WORKFLOW] Job {job.id} has no requirements text")
        return None
    
    logger.info(f"[SKILL WORKFLOW] Starting skill extraction for job {job.id}: {job.title_raw}")
    
    # Step 1: Extract skills using LLM
    extracted_skills = extract_skills_from_requirements(
        job.requirements,
        model_key=model_key,
        user_id=user_id
    )
    
    if not extracted_skills:
        logger.warning(f"[SKILL WORKFLOW] No skills extracted for job {job.id}")
        return None
    
    # Step 2: Save to database
    saved_count = save_job_skills(
        db=db,
        job=job,
        extracted_skills=extracted_skills,
        commit=commit
    )
    
    # Step 3: Update job metadata
    job.extracted_requirements_json = extracted_skills
    if commit:
        db.commit()
    
    logger.info(f"[SKILL WORKFLOW] ✓ Complete for job {job.id}: {saved_count} skills saved")
    
    return saved_count
