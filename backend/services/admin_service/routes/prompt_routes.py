"""
Admin API for LLM Prompt Management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json
import re

from shared.admin_auth import get_current_admin_user
from shared.database import get_db
from shared.prompt_manager import get_prompt_manager
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/prompts", tags=["Prompt Management"])


# ============================================================================
# Pydantic Models
# ============================================================================

class PromptMetadata(BaseModel):
    """Metadata for prompt templates - used in /categories endpoint"""
    category: str
    name: str
    description: str
    parameters: List[str]
    parameter_descriptions: Dict[str, str]
    example_usage: Optional[str]


class PromptTemplateCreate(BaseModel):
    name: str = Field(description="Display name: CV Parsing v2 - Detailed")
    category: str = Field(description="Category for grouping (cv_parsing, gap_analysis, etc.)")
    prompt_text: str = Field(description="Template with {{parameter}} placeholders")
    parameters: List[str] = Field(description="List of parameter names")
    llm_config: Dict[str, Any] = Field(default={"temperature": 0.7, "max_tokens": 2000}, description="LLM configuration")
    is_active: bool = False
    admin_notes: Optional[str] = None


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    prompt_text: Optional[str] = None
    parameters: Optional[List[str]] = None
    llm_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    admin_notes: Optional[str] = None


class PromptTemplateResponse(BaseModel):
    id: int
    category: str
    name: str
    prompt_text: str
    parameters: List[str]
    llm_config: Dict[str, Any]
    is_active: bool
    admin_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class PromptPreviewRequest(BaseModel):
    prompt_text: str
    parameters: Dict[str, Any] = Field(description="Parameter values for preview")


class PromptPreviewResponse(BaseModel):
    rendered_prompt: str
    unreplaced_params: List[str]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("", response_model=List[PromptTemplateResponse])
async def list_prompts(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user = Depends(get_current_admin_user),
    session = Depends(get_db)
):
    """List all prompt templates with optional filtering"""
    try:
        query = """
            SELECT id, category, name, prompt_text, parameters, 
                   model_config, is_active, admin_notes, created_at, updated_at
            FROM prompt_templates
            WHERE 1=1
        """
        params = {}
        
        if category:
            query += " AND category = :category"
            params["category"] = category
        
        if is_active is not None:
            query += " AND is_active = :is_active"
            params["is_active"] = is_active
        
        query += " ORDER BY category, created_at DESC"
        
        result = session.execute(text(query), params).fetchall()
        
        prompts = []
        for row in result:
            prompts.append(PromptTemplateResponse(
                id=row[0],
                category=row[1],
                name=row[2],
                prompt_text=row[3],
                parameters=row[4] if isinstance(row[4], list) else json.loads(row[4] or "[]"),
                llm_config=row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
                is_active=row[6],
                admin_notes=row[7],
                created_at=row[8],
                updated_at=row[9]
            ))
        
        return prompts
        
    except Exception as e:
        logger.error(f"Error listing prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories", response_model=List[PromptMetadata])
async def list_categories(
    current_user = Depends(get_current_admin_user),
    session = Depends(get_db)
):
    """
    List all available prompt categories with metadata.
    Returns hardcoded metadata definitions - DB can be empty.
    Admins use this to know what categories are available for creating prompts.
    """
    try:
        # Hardcoded metadata - serves as schema/contract
        metadata_map = {
            "cv_parsing": {
                "name": "CV Parsing",
                "description": "Parse CV from raw text and extract structured information",
                "parameters": ["masked_text", "current_date"],
                "parameter_descriptions": {
                    "masked_text": "CV text with PII masked (emails, phones, addresses)",
                    "current_date": "Current date in YYYY-MM-DD format for date calculations"
                },
                "example_usage": "Used in CV upload flow to extract skills, experience, education"
            },
            "gap_analysis": {
                "name": "Gap Analysis (Path A)",
                "description": "Analyze skill gaps between candidate CV and job requirements (pre-parsed)",
                "parameters": ["job_title", "requirements_json", "cv_json_str"],
                "parameter_descriptions": {
                    "job_title": "Job title from the job posting",
                    "requirements_json": "JSON string of pre-parsed job requirements",
                    "cv_json_str": "JSON string of parsed CV data"
                },
                "example_usage": "Used when both CV and JD are already parsed"
            },
            "gap_analysis_merged": {
                "name": "Gap Analysis (Path B - Merged)",
                "description": "Extract JD requirements and perform gap analysis in one call",
                "parameters": ["jd_text", "cv_text"],
                "parameter_descriptions": {
                    "jd_text": "Raw job description text",
                    "cv_text": "JSON string of parsed CV data"
                },
                "example_usage": "Used when JD is raw text and needs extraction first"
            },
            "course_recommendation": {
                "name": "Course Recommendation + Roadmap",
                "description": "Select courses and build learning roadmap based on skill gaps",
                "parameters": ["gaps_context", "candidates_context", "yt_context"],
                "parameter_descriptions": {
                    "gaps_context": "JSON string of skill gaps to address",
                    "candidates_context": "JSON string of available paid courses",
                    "yt_context": "JSON string of available YouTube videos"
                },
                "example_usage": "Used after gap analysis to recommend learning resources"
            },
            "jd_parsing": {
                "name": "JD Parsing (Standalone)",
                "description": "Extract structured requirements from job description",
                "parameters": ["jd_text"],
                "parameter_descriptions": {
                    "jd_text": "Raw job description text"
                },
                "example_usage": "Used in benchmark or standalone JD analysis"
            },
            "roadmap_building": {
                "name": "Roadmap Building (Standalone)",
                "description": "Build personalized learning roadmap from selected courses",
                "parameters": ["selected_courses", "skill_gaps", "target_role"],
                "parameter_descriptions": {
                    "selected_courses": "JSON string of selected courses",
                    "skill_gaps": "JSON string of skill gaps to address",
                    "target_role": "Target job role/title"
                },
                "example_usage": "Standalone roadmap generation (can also use course_recommendation for combined flow)"
            }
        }
        
        # Return all 6 metadata definitions
        metadata_list = []
        for category, meta in metadata_map.items():
            metadata_list.append(PromptMetadata(
                category=category,
                name=meta["name"],
                description=meta["description"],
                parameters=meta["parameters"],
                parameter_descriptions=meta["parameter_descriptions"],
                example_usage=meta.get("example_usage")
            ))
        
        return metadata_list
        
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{prompt_id}", response_model=PromptTemplateResponse)
async def get_prompt(
    prompt_id: int,
    current_user = Depends(get_current_admin_user),
    session = Depends(get_db)
):
    """Get a specific prompt template by ID"""
    try:
        query = text("""
            SELECT id, category, name, prompt_text, parameters, 
                   model_config, is_active, admin_notes, created_at, updated_at
            FROM prompt_templates
            WHERE id = :id
        """)
        result = session.execute(query, {"id": prompt_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")
        
        return PromptTemplateResponse(
            id=result[0],
            category=result[1],
            name=result[2],
            prompt_text=result[3],
            parameters=result[4] if isinstance(result[4], list) else json.loads(result[4] or "[]"),
            llm_config=result[5] if isinstance(result[5], dict) else json.loads(result[5] or "{}"),
            is_active=result[6],
            admin_notes=result[7],
            created_at=result[8],
            updated_at=result[9]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt: PromptTemplateCreate,
    current_user = Depends(get_current_admin_user),
    session = Depends(get_db)
):
    """Create a new prompt template"""
    try:
        # If is_active=true, check if there's already an active prompt with same category
        if prompt.is_active:
            check_query = text("""
                SELECT id FROM prompt_templates 
                WHERE category = :category AND is_active = true
            """)
            existing = session.execute(check_query, {"category": prompt.category}).fetchone()
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"An active prompt with category '{prompt.category}' already exists. Deactivate it first or create this as inactive."
                )
        
        # Insert new prompt (key = category for backward compatibility)
        insert_query = text("""
            INSERT INTO prompt_templates 
            (key, name, category, prompt_text, parameters, model_config, is_active, admin_notes)
            VALUES (:category, :name, :category, :prompt_text, :parameters, :model_config, :is_active, :admin_notes)
            RETURNING id, category, name, prompt_text, parameters, model_config, 
                      is_active, admin_notes, created_at, updated_at
        """)
        
        result = session.execute(insert_query, {
            "category": prompt.category,
            "name": prompt.name,
            "prompt_text": prompt.prompt_text,
            "parameters": json.dumps(prompt.parameters),
            "model_config": json.dumps(prompt.llm_config),
            "is_active": prompt.is_active,
            "admin_notes": prompt.admin_notes
        }).fetchone()
        
        session.commit()
        
        # Reload to Redis if active
        if prompt.is_active:
            prompt_manager = get_prompt_manager()
            if prompt_manager:
                prompt_manager.reload_prompt(prompt.category)
        
        logger.info(f"Created prompt '{prompt.name}' (category={prompt.category}) by user {current_user.id}")
        
        return PromptTemplateResponse(
            id=result[0],
            category=result[1],
            name=result[2],
            prompt_text=result[3],
            parameters=result[4] if isinstance(result[4], list) else json.loads(result[4] or "[]"),
            llm_config=result[5] if isinstance(result[5], dict) else json.loads(result[5] or "{}"),
            is_active=result[6],
            admin_notes=result[7],
            created_at=result[8],
            updated_at=result[9]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{prompt_id}", response_model=PromptTemplateResponse)
async def update_prompt(
    prompt_id: int,
    updates: PromptTemplateUpdate,
    current_user = Depends(get_current_admin_user),
    session = Depends(get_db)
):
    """Update an existing prompt template"""
    try:
        # Check if prompt exists
        check_query = text("SELECT category, is_active FROM prompt_templates WHERE id = :id")
        existing = session.execute(check_query, {"id": prompt_id}).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")
        
        old_category = existing[0]
        old_is_active = existing[1]
        
        # Validate parameters if both prompt_text and parameters are provided
        if updates.prompt_text and updates.parameters:
            for param in updates.parameters:
                placeholder = f"{{{{{param}}}}}"
                if placeholder not in updates.prompt_text:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Parameter '{param}' not found in prompt text. Use {{{{{param}}}}} format."
                    )
        
        # Build update query dynamically
        update_fields = []
        params = {"id": prompt_id}
        
        if updates.name is not None:
            update_fields.append("name = :name")
            params["name"] = updates.name
        
        if updates.category is not None:
            update_fields.append("category = :category")
            update_fields.append("key = :category")  # Keep key in sync with category
            params["category"] = updates.category
        
        if updates.prompt_text is not None:
            update_fields.append("prompt_text = :prompt_text")
            params["prompt_text"] = updates.prompt_text
        
        if updates.parameters is not None:
            update_fields.append("parameters = :parameters")
            params["parameters"] = json.dumps(updates.parameters)
        
        if updates.llm_config is not None:
            update_fields.append("model_config = :model_config")
            params["model_config"] = json.dumps(updates.llm_config)
        
        if updates.is_active is not None:
            update_fields.append("is_active = :is_active")
            params["is_active"] = updates.is_active
        
        if updates.admin_notes is not None:
            update_fields.append("admin_notes = :admin_notes")
            params["admin_notes"] = updates.admin_notes
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_query = text(f"""
            UPDATE prompt_templates
            SET {', '.join(update_fields)}
            WHERE id = :id
            RETURNING id, category, name, prompt_text, parameters, model_config, 
                      is_active, admin_notes, created_at, updated_at
        """)
        
        result = session.execute(update_query, params).fetchone()
        session.commit()
        
        # Reload Redis cache if active status changed or if it's active
        new_is_active = result[6]
        new_category = result[1]
        if old_is_active or new_is_active:
            prompt_manager = get_prompt_manager()
            if prompt_manager:
                # Reload both old and new category if category changed
                if updates.category and updates.category != old_category:
                    prompt_manager.reload_prompt(old_category)
                    prompt_manager.reload_prompt(new_category)
                else:
                    prompt_manager.reload_prompt(old_category)
        
        logger.info(f"Updated prompt {prompt_id} by user {current_user.id}")
        
        return PromptTemplateResponse(
            id=result[0],
            category=result[1],
            name=result[2],
            prompt_text=result[3],
            parameters=result[4] if isinstance(result[4], list) else json.loads(result[4] or "[]"),
            llm_config=result[5] if isinstance(result[5], dict) else json.loads(result[5] or "{}"),
            is_active=result[6],
            admin_notes=result[7],
            created_at=result[8],
            updated_at=result[9]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: int,
    current_user = Depends(get_current_admin_user),
    session = Depends(get_db)
):
    """Delete a prompt template"""
    try:
        # Get prompt info before deleting
        check_query = text("SELECT category, is_active FROM prompt_templates WHERE id = :id")
        existing = session.execute(check_query, {"id": prompt_id}).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")
        
        prompt_category = existing[0]
        was_active = existing[1]
        
        # Delete prompt
        delete_query = text("DELETE FROM prompt_templates WHERE id = :id")
        session.execute(delete_query, {"id": prompt_id})
        session.commit()
        
        # Invalidate cache if it was active
        if was_active:
            prompt_manager = get_prompt_manager()
            if prompt_manager:
                prompt_manager.invalidate_cache(prompt_category)
        
        logger.info(f"Deleted prompt {prompt_id} (category={prompt_category}) by user {current_user.id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{prompt_id}/activate", response_model=PromptTemplateResponse)
async def activate_prompt(
    prompt_id: int,
    current_user = Depends(get_current_admin_user),
    session = Depends(get_db)
):
    """
    Activate a prompt template.
    Automatically deactivates other prompts with the same category.
    """
    try:
        # Get prompt info
        check_query = text("SELECT category FROM prompt_templates WHERE id = :id")
        existing = session.execute(check_query, {"id": prompt_id}).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")
        
        prompt_category = existing[0]
        
        # Deactivate all other prompts with same category
        deactivate_query = text("""
            UPDATE prompt_templates
            SET is_active = false
            WHERE category = :category AND id != :id
        """)
        session.execute(deactivate_query, {"category": prompt_category, "id": prompt_id})
        
        # Activate this prompt
        activate_query = text("""
            UPDATE prompt_templates
            SET is_active = true
            WHERE id = :id
            RETURNING id, category, name, prompt_text, parameters, model_config, 
                      is_active, admin_notes, created_at, updated_at
        """)
        result = session.execute(activate_query, {"id": prompt_id}).fetchone()
        session.commit()
        
        # Reload to Redis
        prompt_manager = get_prompt_manager()
        if prompt_manager:
            prompt_manager.reload_prompt(prompt_category)
        
        logger.info(f"Activated prompt {prompt_id} (category={prompt_category}) by user {current_user.id}")
        
        return PromptTemplateResponse(
            id=result[0],
            category=result[1],
            name=result[2],
            prompt_text=result[3],
            parameters=result[4] if isinstance(result[4], list) else json.loads(result[4] or "[]"),
            llm_config=result[5] if isinstance(result[5], dict) else json.loads(result[5] or "{}"),
            is_active=result[6],
            admin_notes=result[7],
            created_at=result[8],
            updated_at=result[9]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error activating prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview", response_model=PromptPreviewResponse)
async def preview_prompt(
    request: PromptPreviewRequest,
    current_user: dict = Depends(get_current_admin_user)
):
    """Preview a prompt with sample parameters (for testing before save)"""
    try:
        template = request.prompt_text
        
        # Replace parameters
        for param_name, param_value in request.parameters.items():
            placeholder = f"{{{{{param_name}}}}}"
            template = template.replace(placeholder, str(param_value))
        
        # Find unreplaced parameters
        unreplaced = re.findall(r'\{\{(\w+)\}\}', template)
        
        return PromptPreviewResponse(
            rendered_prompt=template,
            unreplaced_params=unreplaced
        )
        
    except Exception as e:
        logger.error(f"Error previewing prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload", status_code=status.HTTP_200_OK)
async def reload_all_prompts(
    current_user = Depends(get_current_admin_user)
):
    """Reload all active prompts to Redis cache"""
    try:
        prompt_manager = get_prompt_manager()
        if not prompt_manager:
            raise HTTPException(status_code=500, detail="Prompt manager not initialized")
        
        count = prompt_manager.load_active_prompts_to_redis()
        
        logger.info(f"Reloaded {count} active prompts to Redis by user {current_user.id}")
        
        return {
            "message": f"Successfully reloaded {count} active prompts to Redis",
            "count": count
        }
        
    except Exception as e:
        logger.error(f"Error reloading prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
