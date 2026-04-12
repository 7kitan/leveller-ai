from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict, List, Any
from .nodes_impl import parse_with_llm, mask_pii, normalize_terms
from .neo4j_node import neo4j_normalize_node
from ..tasks.cv_parsing_utils import extract_cv_hybrid

class AgentState(TypedDict):
    user_id: str
    cv_id: str
    file_path: str
    raw_text: Optional[str]
    is_ocr: bool
    method: Optional[str]
    parsed_data: Optional[Dict[str, Any]]
    skill_categories: Optional[Dict[str, str]]
    error: Optional[str]
    status: str

async def extraction_node(state: AgentState):
    """
    Sử dụng Hybrid Strategy (Direct Text + OCR fallback).
    """
    print("---EXTRACTION---")
    result = await extract_cv_hybrid(state["file_path"])
    
    if result.get("raw_text"):
        return {
            "raw_text": result["raw_text"], 
            "is_ocr": result["is_ocr"], 
            "method": result["method"],
            "status": "extracted"
        }
    
    return {"error": "Không thể trích xuất văn bản từ CV.", "status": "failed"}

def pii_mask_node(state: AgentState):
    """Ẩn danh thông tin nhạy cảm trước khi gửi tới LLM."""
    print("---PII MASKING---")
    if not state.get("raw_text") or state.get("status") == "failed":
        return {"status": "failed", "error": state.get("error", "No text to mask")}
    
    masked_text = mask_pii(state["raw_text"])
    return {"raw_text": masked_text, "status": "masked"}

def normalization_node(state: AgentState):
    """Chuẩn hóa thuật ngữ kỹ thuật dựa trên Graph Taxonomy trước khi Parse."""
    print("---TERM NORMALIZATION---")
    if not state.get("raw_text") or state.get("status") == "failed":
        return {"status": "failed", "error": state.get("error", "No text to normalize")}
    
    normalized_text = normalize_terms(state["raw_text"])
    return {"raw_text": normalized_text, "status": "normalized"}

async def llm_parse_node(state: AgentState):
    """Dùng LLM để parse text thành JSON."""
    print("---LLM PARSING---")
    if not state.get("raw_text") or state.get("status") == "failed":
        return {"status": "failed", "error": state.get("error", "No text to parse")}
        
    parsed = await parse_with_llm(state["raw_text"])
    if parsed:
        return {"parsed_data": parsed, "status": "parsed"}
    return {"error": "AI không thể phân tích nội dung CV.", "status": "failed"}

def cleanup_node(state: AgentState):
    """Xóa file CV sau khi xử lý."""
    print("---CLEANING UP---")
    import os
    if os.path.exists(state["file_path"]):
        try:
            os.remove(state["file_path"])
        except Exception as e:
            print(f"Warning: Could not remove file {state['file_path']}: {e}")
    return {"status": "completed"}

# Xây dựng Graph
workflow = StateGraph(AgentState)

workflow.add_node("extraction", extraction_node)
workflow.add_node("pii_mask", pii_mask_node)
workflow.add_node("normalization", normalization_node)
workflow.add_node("llm_parse", llm_parse_node)
workflow.add_node("neo4j_normalize", neo4j_normalize_node)
workflow.add_node("cleanup", cleanup_node)

# Bắt đầu từ Hybrid Extraction
workflow.set_entry_point("extraction")

workflow.add_edge("extraction", "pii_mask")
workflow.add_edge("pii_mask", "normalization")
workflow.add_edge("normalization", "llm_parse")
workflow.add_edge("llm_parse", "neo4j_normalize")
workflow.add_edge("neo4j_normalize", "cleanup")
workflow.add_edge("cleanup", END)

app_graph = workflow.compile()
