"""
Skill extraction and management utilities.
Handles extracting skills from job requirements and managing skill database.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from shared.models import Skill, Job, JobSkillRequirement
from shared.llm_utils import extract_skills_from_requirements, get_embedding, get_embeddings_batch, build_jd_skill_context
from shared.system_logger import system_logger
import uuid

logger = logging.getLogger("skill_extraction")


def find_or_create_skill(db: Session, skill_name: str, category: str = None, vector: Optional[List[float]] = None) -> Skill:
    """
    Find existing skill by name (case-insensitive) or create new one.
    
    Args:
        db: Database session
        skill_name: Name of the skill
        category: Category of the skill (optional)
        vector: Pre-generated embedding vector (optional)
    
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
    
    # Generate embedding if not provided
    if vector is None:
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
    Optimized to use Batch Embedding.
    """
    if not extracted_skills:
        logger.warning(f"[SKILL DB] No skills to save for job {job.id}")
        return 0
    
    saved_count = 0
    
    # Delete existing skills for this job (if re-processing)
    db.query(JobSkillRequirement).filter(
        JobSkillRequirement.job_id == job.id
    ).delete()
    
    # --- PHASE 1: Handle Skill Entities (find/create) ---
    skill_names = [s.get("skill_name") for s in extracted_skills if s.get("skill_name")]
    if not skill_names: return 0
    
    # Bulk find existing skills
    existing_skills_query = db.query(Skill).filter(
        or_(*[Skill.name.ilike(name) for name in skill_names])
    ).all()
    
    skill_map = {s.name.lower(): s for s in existing_skills_query}
    
    # Identify skills that need to be created
    new_skill_requests = []
    for s_data in extracted_skills:
        name = s_data.get("skill_name")
        if name and name.lower() not in skill_map:
            new_skill_requests.append(s_data)
    
    if new_skill_requests:
        logger.info(f"[SKILL DB] Batch creating {len(new_skill_requests)} new skills...")
        new_skill_contexts = []
        for s in new_skill_requests:
            ctx = f"Skill: {s['skill_name']}"
            if s.get("category"): ctx += f". Category: {s['category']}"
            new_skill_contexts.append(ctx)
        
        # Batch embed new skills
        new_skill_vectors = get_embeddings_batch(new_skill_contexts, log_cost=False)
        
        for i, s_data in enumerate(new_skill_requests):
            if i < len(new_skill_vectors):
                new_skill = find_or_create_skill(
                    db, 
                    s_data["skill_name"], 
                    s_data.get("category"),
                    vector=new_skill_vectors[i]
                )
                skill_map[new_skill.name.lower()] = new_skill

    # --- PHASE 2: Handle JobSkillRequirements (Batch Embed) ---
    requirement_contexts = []
    valid_skill_data = []
    
    for s_data in extracted_skills:
        name = s_data.get("skill_name")
        skill = skill_map.get(name.lower()) if name else None
        
        if skill:
            level = s_data.get("required_level")
            years = s_data.get("min_years_exp", 0)
            
            ctx = build_jd_skill_context(
                skill_name=name,
                level=level or "",
                years=years,
                domain=job.domain_role or ""
            )
            requirement_contexts.append(ctx)
            valid_skill_data.append((s_data, skill, ctx))
    
    if not requirement_contexts:
        return 0
        
    logger.info(f"[SKILL DB] Batch embedding {len(requirement_contexts)} requirements...")
    requirement_vectors = get_embeddings_batch(requirement_contexts, log_cost=False)
    
    for i, (s_data, skill, ctx) in enumerate(valid_skill_data):
        if i >= len(requirement_vectors): break
        
        # Create JobSkillRequirement
        job_skill = JobSkillRequirement(
            id=uuid.uuid4(),
            job_id=job.id,
            skill_id=skill.id,
            required_level=s_data.get("required_level"),
            min_years_exp=s_data.get("min_years_exp", 0),
            is_mandatory=s_data.get("is_mandatory", True),
            importance_weight=s_data.get("importance_weight", 5),
            embedding_context=ctx,
            vector=requirement_vectors[i]
        )
        db.add(job_skill)
        saved_count += 1
    
    if commit:
        db.commit()
        logger.info(f"[SKILL DB] ✓ Batch Saved {saved_count} skills for job {job.id}")
    
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
    system_logger.info("AI_SKILL_EXTRACT", f"Starting skill extraction for Job: {job.title_raw}")
    
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
    system_logger.info("AI_SKILL_EXTRACT", f"Completed skill extraction for Job {job.id}: {saved_count} skills saved")
    
    return saved_count
