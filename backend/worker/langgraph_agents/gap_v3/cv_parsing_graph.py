"""
CV Parsing LangGraph Orchestrator — Pipeline 1.
Chạy 1 lần khi user upload CV.
"""

import time
import logging
from langgraph.graph import StateGraph, END
from .states import CVParsingState
from .nodes.cv_parsing_nodes import (
    extract_text_node,
    llm_parse_cv_node,
    normalize_cv_node,
    persist_cv_data_node,
)
from shared.redis_client import result_cache

logger = logging.getLogger("cv_parsing_graph")


def _should_continue(state: CVParsingState) -> str:
    status = state.get("status", "unknown")
    error = state.get("error")
    if error or status == "failed":
        logger.warning(
            f"[GRAPH] _should_continue → END  cv_id={state.get('cv_id')} "
            f"status={status} error={error}"
        )
        return "end"
    logger.info(
        f"[GRAPH] _should_continue → CONTINUE cv_id={state.get('cv_id')} status={status}"
    )
    return "continue"


# Build graph
cv_parsing_workflow = StateGraph(CVParsingState)

cv_parsing_workflow.set_entry_point("extract_text")
cv_parsing_workflow.add_node("extract_text", extract_text_node)
cv_parsing_workflow.add_node("llm_parse", llm_parse_cv_node)
cv_parsing_workflow.add_node("normalize", normalize_cv_node)
cv_parsing_workflow.add_node("persist", persist_cv_data_node)

cv_parsing_workflow.add_conditional_edges(
    "extract_text", _should_continue, {"continue": "llm_parse", "end": END}
)
cv_parsing_workflow.add_conditional_edges(
    "llm_parse", _should_continue, {"continue": "normalize", "end": END}
)
cv_parsing_workflow.add_conditional_edges(
    "normalize", _should_continue, {"continue": "persist", "end": END}
)
cv_parsing_workflow.add_edge("persist", END)

cv_parsing_graph = cv_parsing_workflow.compile()


async def run_cv_parsing_pipeline(cv_id: str, user_id: str, db) -> dict:
    """
    Entry point: Parse CV → structured data → save to DB.
    Gọi từ Celery task sau khi user upload CV thành công.
    """
    t0 = time.monotonic()

    initial_state: CVParsingState = {
        "cv_id": cv_id,
        "user_id": user_id,
        "db": db,
        "raw_text": None,
        "is_ocr": False,
        "cv_parsed": None,
        "status": "started",
        "error": None,
    }

    logger.info(
        "\n" + "=" * 60 + "\n"
        f"[PIPELINE START] cv_id={cv_id} | user_id={user_id}\n"
        f"  Initial state: status=started, raw_text=None, cv_parsed=None\n" + "=" * 60
    )

    # ── STEP 0: Invoke graph node-by-node with timing ──────────────────────
    step_names = ["extract_text", "llm_parse", "normalize", "persist"]
    step_labels = [
        "STEP 1/4: Text Extraction (pymupdf / OCR fallback)",
        "STEP 2/4: LLM Structured Parsing (OpenAI gpt-4o-mini)",
        "STEP 3/4: Normalize Skills + Validate",
        "STEP 4/4: Persist to DB (cv_parsed_json + skills)",
    ]

    state = initial_state
    for i, (node_name, label) in enumerate(zip(step_names, step_labels), 1):
        t_step = time.monotonic()
        logger.info(f"\n{'─' * 60}\n[GRAPH {label}] cv_id={cv_id}")
        try:
            node_fn = {
                "extract_text": extract_text_node,
                "llm_parse": llm_parse_cv_node,
                "normalize": normalize_cv_node,
                "persist": persist_cv_data_node,
            }[node_name]

            state = await node_fn(state)
            elapsed = time.monotonic() - t_step
            total = time.monotonic() - t0

            cv_parsed_keys = (
                list(state.get("cv_parsed").keys())
                if isinstance(state.get("cv_parsed"), dict)
                else type(state.get("cv_parsed")).__name__
            )
            logger.info(
                f"[GRAPH] {label} → DONE | elapsed={elapsed:.1f}s | total={total:.1f}s\n"
                f"  returned status : {state.get('status')}\n"
                f"  returned error  : {state.get('error') or 'None'}\n"
                f"  raw_text chars  : {len(state.get('raw_text') or '')}\n"
                f"  cv_parsed type  : {cv_parsed_keys}"
            )

            # Early exit on failure
            if state.get("error") or state.get("status") == "failed":
                logger.warning(
                    f"[GRAPH] Early exit at {label} — status=failed | error={state.get('error')}"
                )
                break

        except Exception as node_err:
            elapsed = time.monotonic() - t_step
            logger.error(
                f"[GRAPH] Exception in {label}: {type(node_err).__name__}: {node_err}\n"
                f"  elapsed={elapsed:.1f}s | total={time.monotonic() - t0:.1f}s"
            )
            state = {**state, "status": "failed", "error": str(node_err)}
            break

    # ── Final result ─────────────────────────────────────────────────────────
    total_elapsed = time.monotonic() - t0

    # Cleanup Redis Progress
    try:
        result_cache.delete(f"cv_progress:{cv_id}")
    except Exception as e:
        logger.warning(f"Failed to clear progress in Redis for cv_progress:{cv_id}: {e}")

    if state.get("cv_parsed"):
        parsed = state["cv_parsed"]
        logger.info(
            "\n" + "=" * 60 + "\n"
            f"[PIPELINE SUCCESS] cv_id={cv_id} | total={total_elapsed:.1f}s\n"
            f"  full_name      : {parsed.get('full_name')}\n"
            f"  seniority      : {parsed.get('seniority')}\n"
            f"  experience_yrs : {parsed.get('experience_years_total')}\n"
            f"  skills         : {len(parsed.get('skills', []))}\n"
            f"  work_history   : {len(parsed.get('work_history', []))}\n"
            f"  education      : {len(parsed.get('education', []))}\n"
            f"  certifications : {len(parsed.get('certifications', []))}\n"
            f"  is_ocr         : {parsed.get('is_ocr', False)}\n"
            f"  ocr_confidence : {parsed.get('ocr_confidence', 0):.2f}\n" + "=" * 60
        )
        return {"status": "success", "cv_parsed": parsed, "cv_id": cv_id}
    else:
        error = state.get("error", "Pipeline failed with no error message")
        logger.warning(
            "\n" + "=" * 60 + "\n"
            f"[PIPELINE FAILED] cv_id={cv_id} | total={total_elapsed:.1f}s\n"
            f"  final status: {state.get('status')}\n"
            f"  final error : {error}\n" + "=" * 60
        )
        return {
            "status": "failed",
            "error": error,
            "cv_id": cv_id,
        }
