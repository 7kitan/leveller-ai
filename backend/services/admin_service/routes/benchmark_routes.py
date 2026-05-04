from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Any, Optional
import uuid

from shared.database import get_db
from shared.admin_auth import require_admin, get_current_admin_user
from shared.models import LLMTestSet, LLMTestCase, LLMBenchmarkSession, LLMBenchmarkResult, UserCV, Job, User
from worker.extensions.benchmark.service import BenchmarkService

router = APIRouter(prefix="/admin/benchmarks", tags=["Benchmarks"])

# ============================================================================
# Data Selection Endpoints (for UI)
# ============================================================================

# NOTE: All /data/* endpoints removed to reduce code duplication
# Frontend should call these endpoints directly:
# - /admin/ai-models (for models list)
# - /analysis/admin/cvs (for CVs list with pagination)
# - /jd/admin/list (for jobs list with pagination)

# ============================================================================
# Test Set & Test Case Management
# ============================================================================

@router.get("/test-sets/{test_set_id}/cases")
async def get_test_cases(
    test_set_id: str,
    db: Session = Depends(get_db), 
    admin = Depends(require_admin)
):
    """Get all test cases for a test set."""
    test_set = db.query(LLMTestSet).filter(LLMTestSet.id == test_set_id).first()
    if not test_set:
        raise HTTPException(status_code=404, detail="Test set not found")
    
    cases = db.query(LLMTestCase)\
              .filter(LLMTestCase.test_set_id == test_set_id)\
              .all()
    
    return {
        "test_set": {
            "id": str(test_set.id),
            "name": test_set.name,
            "flow_type": test_set.flow_type
        },
        "cases": [
            {
                "id": str(case.id),
                "input_data": case.input_data,
                "reference_output": case.reference_output,
                "test_metadata": case.test_metadata,
                "created_at": case.created_at.isoformat() if case.created_at else None
            }
            for case in cases
        ]
    }

from pydantic import BaseModel

class UpdateTestCaseRequest(BaseModel):
    input_data: Dict[str, Any]
    reference_output: Optional[Dict[str, Any]] = None
    test_metadata: Optional[Dict[str, Any]] = None

@router.patch("/test-cases/{case_id}")
async def update_test_case(
    case_id: str,
    request: UpdateTestCaseRequest,
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """Update test case fields (input_data, reference_output, metadata)."""
    case = db.query(LLMTestCase).filter(LLMTestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    # Update fields
    case.input_data = request.input_data
    if request.reference_output is not None:
        case.reference_output = request.reference_output
    if request.test_metadata is not None:
        case.test_metadata = request.test_metadata
    
    db.commit()
    db.refresh(case)
    
    return {
        "message": "Test case updated successfully",
        "case": {
            "id": str(case.id),
            "input_data": case.input_data,
            "reference_output": case.reference_output,
            "test_metadata": case.test_metadata
        }
    }

@router.delete("/test-cases/{case_id}")
async def delete_test_case(
    case_id: str,
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """Delete a test case."""
    case = db.query(LLMTestCase).filter(LLMTestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    db.delete(case)
    db.commit()
    
    return {"message": "Test case deleted successfully"}

# ============================================================================
# Quick Benchmark (No Save)
# ============================================================================

class QuickBenchmarkRequest(BaseModel):
    cv_id: str
    job_id: str
    flow_type: str  # "cv_parsing_v3" | "gap_analysis_merged" | "full_cv_to_gap"
    llm_config: Dict[str, Any]
    reference_output: Dict[str, Any] = None  # Optional ground truth

@router.post("/quick-run")
async def quick_benchmark(
    request: QuickBenchmarkRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """
    Run a quick benchmark without saving test case.
    Creates a temporary test set and test case, runs benchmark, returns session ID.
    """
    # Verify CV and Job exist
    cv = db.query(UserCV).filter(UserCV.id == request.cv_id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Create temporary test set
    temp_test_set = LLMTestSet(
        id=uuid.uuid4(),
        name=f"Quick Benchmark - {cv.full_name or 'Unknown'} vs {job.title}",
        description=f"Temporary test set for quick benchmark",
        flow_type=request.flow_type,
        is_active=False  # Mark as temporary
    )
    db.add(temp_test_set)
    db.flush()
    
    # Create temporary test case
    input_data = {
        "cv_id": request.cv_id,
        "job_id": request.job_id
    }
    
    if request.flow_type == "gap_analysis_merged":
        # Need JD text
        input_data["jd_text"] = job.description or ""
    
    temp_test_case = LLMTestCase(
        id=uuid.uuid4(),
        test_set_id=temp_test_set.id,
        input_data=input_data,
        reference_output=request.reference_output or {},
        test_metadata={"temporary": True, "quick_benchmark": True}
    )
    db.add(temp_test_case)
    db.commit()
    
    # Trigger benchmark
    from worker.extensions.benchmark.tasks import run_benchmark_session_task
    run_benchmark_session_task.delay(
        str(temp_test_set.id), 
        request.llm_config, 
        str(admin.id)
    )
    
    return {
        "message": "Quick benchmark started",
        "test_set_id": str(temp_test_set.id),
        "cv_name": cv.full_name or "Unknown",
        "job_title": job.title
    }

# ============================================================================
# Existing Endpoints
# ============================================================================

@router.get("/test-sets")
async def get_test_sets(db: Session = Depends(get_db), admin = Depends(require_admin)):
    """List all available benchmark test sets."""
    return db.query(LLMTestSet).all()

@router.get("/test-sets/{test_set_id}")
async def get_test_set(
    test_set_id: str,
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """Get a single test set by ID."""
    test_set = db.query(LLMTestSet).filter(LLMTestSet.id == test_set_id).first()
    if not test_set:
        raise HTTPException(status_code=404, detail="Test set not found")
    return test_set

class CreateTestSetRequest(BaseModel):
    name: str
    description: str = None
    flow_type: str = "cv_parsing_v3"
    is_active: bool = True

@router.post("/test-sets")
async def create_test_set(
    request: CreateTestSetRequest,
    db: Session = Depends(get_db), 
    admin = Depends(require_admin)
):
    """Create a new benchmark test set."""
    test_set = LLMTestSet(
        id=uuid.uuid4(),
        name=request.name,
        description=request.description,
        flow_type=request.flow_type,
        is_active=request.is_active
    )
    db.add(test_set)
    db.commit()
    db.refresh(test_set)
    return test_set

class UpdateTestSetRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    flow_type: Optional[str] = None
    is_active: Optional[bool] = None

@router.patch("/test-sets/{test_set_id}")
async def update_test_set(
    test_set_id: str,
    request: UpdateTestSetRequest,
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """Update a test set."""
    test_set = db.query(LLMTestSet).filter(LLMTestSet.id == test_set_id).first()
    if not test_set:
        raise HTTPException(status_code=404, detail="Test set not found")
    
    if request.name is not None:
        test_set.name = request.name
    if request.description is not None:
        test_set.description = request.description
    if request.flow_type is not None:
        test_set.flow_type = request.flow_type
    if request.is_active is not None:
        test_set.is_active = request.is_active
    
    db.commit()
    db.refresh(test_set)
    return test_set

@router.delete("/test-sets/{test_set_id}")
async def delete_test_set(
    test_set_id: str,
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """Delete a test set and all its test cases."""
    test_set = db.query(LLMTestSet).filter(LLMTestSet.id == test_set_id).first()
    if not test_set:
        raise HTTPException(status_code=404, detail="Test set not found")
    
    db.delete(test_set)
    db.commit()
    return {"message": "Test set deleted successfully"}

@router.post("/test-sets/{test_set_id}/cases")
async def add_test_case(
    test_set_id: str,
    input_data: Dict[str, Any],
    reference_output: Dict[str, Any] = None,
    test_metadata: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """Add a single test case to a set."""
    case = LLMTestCase(
        id=uuid.uuid4(),
        test_set_id=test_set_id,
        input_data=input_data,
        reference_output=reference_output,
        test_metadata=test_metadata
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case

@router.post("/test-sets/{test_set_id}/cases/bulk")
async def bulk_upload_test_cases(
    test_set_id: str,
    cases: List[Dict[str, Any]],
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """Bulk upload multiple test cases to a set."""
    created_cases = []
    for case_data in cases:
        case = LLMTestCase(
            id=uuid.uuid4(),
            test_set_id=test_set_id,
            input_data=case_data.get("input_data", {}),
            reference_output=case_data.get("reference_output"),
            test_metadata=case_data.get("metadata")
        )
        db.add(case)
        created_cases.append(case)
    
    db.commit()
    return {"count": len(created_cases)}

class BatchAddTestCasesRequest(BaseModel):
    cv_ids: List[str]
    job_ids: List[str]
    mode: str = "all_combinations"  # "all_combinations" or "paired"

@router.post("/test-sets/{test_set_id}/batch-add")
async def batch_add_cvs_to_test_set(
    test_set_id: str,
    request: BatchAddTestCasesRequest,
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """
    Generate test cases for combinations of CVs and Job IDs.
    Supports two modes:
    - all_combinations: Create N×M test cases (every CV with every Job)
    - paired: Create min(N,M) test cases (CV[i] with Job[i])
    """
    # Verify test set exists
    test_set = db.query(LLMTestSet).filter(LLMTestSet.id == test_set_id).first()
    if not test_set:
        raise HTTPException(status_code=404, detail="Test set not found")
    
    cv_ids = request.cv_ids
    job_ids = request.job_ids
    mode = request.mode
    
    if not cv_ids or not job_ids:
        raise HTTPException(status_code=400, detail="Both cv_ids and job_ids are required")
    
    # Generate test case pairs based on mode
    test_case_pairs = []
    if mode == "all_combinations":
        # Create all combinations: CV × Job
        for cv_id in cv_ids:
            for job_id in job_ids:
                test_case_pairs.append((cv_id, job_id))
    elif mode == "paired":
        # Create paired combinations: CV[i] + Job[i]
        for cv_id, job_id in zip(cv_ids, job_ids):
            test_case_pairs.append((cv_id, job_id))
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'all_combinations' or 'paired'")
    
    # Create test cases
    created_count = 0
    for cv_id, job_id in test_case_pairs:
        test_case = LLMTestCase(
            id=uuid.uuid4(),
            test_set_id=test_set_id,
            input_data={"cv_id": cv_id, "job_id": job_id},
            reference_output=None,
            test_metadata={"mode": mode}
        )
        db.add(test_case)
        created_count += 1
    
    db.commit()
    
    return {
        "message": f"Created {created_count} test cases",
        "count": created_count,
        "mode": mode
    }

from pydantic import BaseModel
class RunBenchmarkRequest(BaseModel):
    test_set_id: str
    llm_config: Dict[str, Any]  # Allow any type of value (str, int, float, bool, etc.)

@router.post("/run")
async def run_benchmark(
    req: RunBenchmarkRequest,
    db: Session = Depends(get_db), 
    admin: User = Depends(get_current_admin_user)
):
    """
    Trigger a benchmark session via Celery worker.
    """
    test_set_id = req.test_set_id
    llm_config = req.llm_config
    # Verify test set exists
    test_set = db.query(LLMTestSet).filter(LLMTestSet.id == test_set_id).first()
    if not test_set:
        raise HTTPException(status_code=404, detail="Test set not found")
    
    # Create session immediately so we can return session_id
    session = LLMBenchmarkSession(
        id=uuid.uuid4(),
        test_set_id=test_set_id,
        model_config=llm_config,
        status="queued",
        created_by=str(admin.id)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
        
    # Trigger Celery task with session_id
    from worker.extensions.benchmark.tasks import run_benchmark_session_task
    run_benchmark_session_task.delay(str(session.id), test_set_id, llm_config, str(admin.id))
    
    return {
        "message": "Benchmark session queued in Celery",
        "session_id": str(session.id),
        "test_set": test_set.name,
        "status": "queued"
    }

@router.get("/sessions")
async def get_sessions(db: Session = Depends(get_db), admin = Depends(require_admin)):
    """List all benchmark sessions."""
    return db.query(LLMBenchmarkSession)\
             .options(joinedload(LLMBenchmarkSession.test_set))\
             .order_by(LLMBenchmarkSession.created_at.desc()).all()

@router.get("/sessions/{session_id}")
async def get_session_details(session_id: str, db: Session = Depends(get_db), admin = Depends(require_admin)):
    """Get detailed results for a specific session."""
    session = db.query(LLMBenchmarkSession)\
                .options(joinedload(LLMBenchmarkSession.test_set))\
                .filter(LLMBenchmarkSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    results = db.query(LLMBenchmarkResult).filter(LLMBenchmarkResult.session_id == session_id).all()
    return {
        "session": session,
        "results": results
    }

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db), admin = Depends(require_admin)):
    """Delete a benchmark session and its results."""
    session = db.query(LLMBenchmarkSession).filter(LLMBenchmarkSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    db.delete(session)
    db.commit()
    return {"message": "Session deleted successfully"}

@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str, 
    format: str = "json",  # "json" | "csv"
    db: Session = Depends(get_db), 
    admin = Depends(require_admin)
):
    """Export benchmark session results to JSON or CSV."""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    import json
    
    session = db.query(LLMBenchmarkSession)\
                .options(joinedload(LLMBenchmarkSession.test_set))\
                .filter(LLMBenchmarkSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    results = db.query(LLMBenchmarkResult)\
                .filter(LLMBenchmarkResult.session_id == session_id).all()
    
    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "test_case_id", "score", "faithfulness", "relevancy", 
            "completeness", "latency_ms", "prompt_tokens", 
            "completion_tokens", "status", "error_message"
        ])
        
        # Data rows
        for result in results:
            metrics = result.metrics or {}
            writer.writerow([
                str(result.test_case_id),
                result.score or 0.0,
                metrics.get("faithfulness", 0.0),
                metrics.get("relevancy", 0.0),
                metrics.get("completeness", 0.0),
                result.latency_ms or 0,
                result.prompt_tokens or 0,
                result.completion_tokens or 0,
                result.status or "unknown",
                result.error_message or ""
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=benchmark_{session_id}.csv"}
        )
    
    else:  # JSON format
        data = {
            "session": {
                "id": str(session.id),
                "test_set_id": str(session.test_set_id),
                "test_set_name": session.test_set.name if session.test_set else None,
                "model_config": session.model_config,
                "status": session.status,
                "overall_score": session.overall_score,
                "total_latency_ms": session.total_latency_ms,
                "total_tokens": session.total_tokens,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None
            },
            "results": [
                {
                    "id": str(result.id),
                    "test_case_id": str(result.test_case_id),
                    "actual_output": result.actual_output,
                    "score": result.score,
                    "metrics": result.metrics,
                    "latency_ms": result.latency_ms,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "status": result.status,
                    "error_message": result.error_message
                }
                for result in results
            ]
        }
        
        return StreamingResponse(
            iter([json.dumps(data, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=benchmark_{session_id}.json"}
        )

@router.get("/test-sets/{test_set_id}/export")
async def export_test_set_comparison(
    test_set_id: str,
    format: str = "csv",
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """Export comparison of all sessions for a test set."""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    import json
    
    test_set = db.query(LLMTestSet).filter(LLMTestSet.id == test_set_id).first()
    if not test_set:
        raise HTTPException(status_code=404, detail="Test set not found")
    
    sessions = db.query(LLMBenchmarkSession)\
                 .filter(LLMBenchmarkSession.test_set_id == test_set_id)\
                 .order_by(LLMBenchmarkSession.created_at.desc()).all()
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "session_id", "parsing_model", "judge_strategy", 
            "overall_score", "total_latency_ms", "total_tokens",
            "status", "created_at", "completed_at"
        ])
        
        # Data rows
        for session in sessions:
            model_config = session.model_config or {}
            writer.writerow([
                str(session.id),
                model_config.get("parsing_model", "unknown"),
                model_config.get("evaluation_strategy", "unknown"),
                session.overall_score or 0.0,
                session.total_latency_ms or 0,
                session.total_tokens or 0,
                session.status,
                session.created_at.isoformat() if session.created_at else "",
                session.completed_at.isoformat() if session.completed_at else ""
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=benchmark_comparison_{test_set_id}.csv"}
        )
    
    else:  # JSON format
        data = {
            "test_set": {
                "id": str(test_set.id),
                "name": test_set.name,
                "flow_type": test_set.flow_type
            },
            "sessions": [
                {
                    "id": str(session.id),
                    "model_config": session.model_config,
                    "overall_score": session.overall_score,
                    "total_latency_ms": session.total_latency_ms,
                    "total_tokens": session.total_tokens,
                    "status": session.status,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "completed_at": session.completed_at.isoformat() if session.completed_at else None
                }
                for session in sessions
            ]
        }
        
        return StreamingResponse(
            iter([json.dumps(data, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=benchmark_comparison_{test_set_id}.json"}
        )
