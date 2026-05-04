from worker.celery_app import celery_app
from worker.extensions.benchmark.service import BenchmarkService
from shared.database import SessionLocal
from shared.models import LLMBenchmarkSession
import logging
import uuid

logger = logging.getLogger("benchmark_worker")

# ============================================================================
# PARALLEL EXECUTION ARCHITECTURE
# ============================================================================
# 
# Session Coordinator (run_benchmark_session_task)
#   ├─→ Test Case Task 1 (run_test_case_task) [parallel]
#   ├─→ Test Case Task 2 (run_test_case_task) [parallel]
#   ├─→ Test Case Task 3 (run_test_case_task) [parallel]
#   └─→ Finalize (finalize_session_task)
#
# Benefits:
# - Multiple test cases run in parallel (limited by worker count)
# - Multiple sessions can run concurrently
# - Better resource utilization
# - Faster benchmark completion
# ============================================================================

@celery_app.task(name="worker.benchmark.run_test_case_task", bind=True)
def run_test_case_task(self, session_id: str, test_case_id: str, model_config: dict):
    """
    Run a single test case (can run in parallel with other test cases).
    
    Args:
        session_id: Benchmark session ID
        test_case_id: Test case ID to run
        model_config: Model configuration
        
    Returns:
        dict: Result with status, score, latency, tokens
    """
    logger.info(f"[BENCHMARK] Running test case {test_case_id} for session {session_id}")
    
    db = SessionLocal()
    try:
        service = BenchmarkService(db)
        
        # Get test case with test_set relationship eagerly loaded
        from shared.models import LLMTestCase
        from sqlalchemy.orm import joinedload
        
        test_case = db.query(LLMTestCase)\
                      .options(joinedload(LLMTestCase.test_set))\
                      .filter(LLMTestCase.id == test_case_id)\
                      .first()
        
        if not test_case:
            raise ValueError(f"Test case {test_case_id} not found")
        
        # Run test case
        import asyncio
        result = asyncio.run(service._run_test_case(test_case, model_config, uuid.UUID(session_id)))
        
        logger.info(f"[BENCHMARK] Completed test case {test_case_id}: score={result.score}")
        
        return {
            "test_case_id": test_case_id,
            "status": result.status,
            "score": result.score,
            "latency_ms": result.latency_ms,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens
        }
        
    except Exception as e:
        logger.error(f"[BENCHMARK] Failed test case {test_case_id}: {e}", exc_info=True)
        
        # Create failed result
        from shared.models import LLMBenchmarkResult
        result = LLMBenchmarkResult(
            id=uuid.uuid4(),
            session_id=uuid.UUID(session_id),
            test_case_id=uuid.UUID(test_case_id),
            status="error",
            error_message=str(e),
            score=0.0,
            latency_ms=0,
            prompt_tokens=0,
            completion_tokens=0
        )
        db.add(result)
        db.commit()
        
        return {
            "test_case_id": test_case_id,
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(name="worker.benchmark.finalize_session_task")
def finalize_session_task(results: list, session_id: str):
    """
    Finalize benchmark session after all test cases complete.
    
    Args:
        results: List of test case results
        session_id: Session ID to finalize
    """
    logger.info(f"[BENCHMARK] Finalizing session {session_id} with {len(results)} results")
    
    db = SessionLocal()
    try:
        session = db.query(LLMBenchmarkSession).filter(
            LLMBenchmarkSession.id == session_id
        ).first()
        
        if not session:
            logger.error(f"[BENCHMARK] Session {session_id} not found")
            return
        
        # Calculate aggregated metrics
        successful_results = [r for r in results if r.get("status") == "success"]
        
        if len(successful_results) > 0:
            total_score = sum(r.get("score", 0.0) for r in successful_results)
            total_latency = sum(r.get("latency_ms", 0) for r in successful_results)
            total_tokens = sum(
                r.get("prompt_tokens", 0) + r.get("completion_tokens", 0) 
                for r in successful_results
            )
            
            session.overall_score = total_score / len(successful_results)
            session.total_latency_ms = total_latency
            session.total_tokens = total_tokens
            session.status = "completed"
        else:
            session.status = "failed"
            session.overall_score = 0.0
        
        from datetime import datetime
        session.completed_at = datetime.now()
        db.commit()
        
        logger.info(f"[BENCHMARK] Session {session_id} finalized: score={session.overall_score:.2f}")
        
    except Exception as e:
        logger.error(f"[BENCHMARK] Failed to finalize session {session_id}: {e}", exc_info=True)
    finally:
        db.close()


@celery_app.task(name="worker.benchmark.run_session_task")
def run_benchmark_session_task(session_id: str, test_set_id: str, model_config: dict, admin_id: str):
    """
    Coordinator task: Updates session and spawns parallel test case tasks.
    
    Args:
        session_id: Pre-created session ID
        test_set_id: Test set ID to run
        model_config: Model configuration
        admin_id: Admin user ID
        
    Returns:
        str: Session ID
    """
    logger.info(f"[BENCHMARK] Starting session coordinator for session: {session_id}")
    
    db = SessionLocal()
    try:
        from shared.models import LLMTestSet
        from celery import chord
        
        # Get test set
        test_set = db.query(LLMTestSet).filter(LLMTestSet.id == test_set_id).first()
        if not test_set:
            raise ValueError(f"Test set {test_set_id} not found")
        
        # Get existing session and update status to running
        session = db.query(LLMBenchmarkSession).filter(LLMBenchmarkSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.status = "running"
        db.commit()
        
        test_cases = test_set.test_cases
        
        logger.info(f"[BENCHMARK] Session {session_id} running with {len(test_cases)} test cases")
        
        # Spawn parallel test case tasks using Celery chord
        # chord: Run tasks in parallel, then call callback when all complete
        test_case_tasks = [
            run_test_case_task.s(session_id, str(case.id), model_config)
            for case in test_cases
        ]
        
        # Execute in parallel and finalize when done
        callback = finalize_session_task.s(session_id)
        chord(test_case_tasks)(callback)
        
        logger.info(f"[BENCHMARK] Spawned {len(test_case_tasks)} parallel tasks for session {session_id}")
        
        return session_id
        
    except Exception as e:
        logger.error(f"[BENCHMARK] Failed to start session: {e}", exc_info=True)
        # Update session status to failed
        try:
            session = db.query(LLMBenchmarkSession).filter(LLMBenchmarkSession.id == session_id).first()
            if session:
                session.status = "failed"
                db.commit()
        except:
            pass
        raise
    finally:
        db.close()
