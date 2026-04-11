from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict, List, Any
from .nodes_impl import extract_from_pdf, parse_with_llm, mask_pii, normalize_terms
from .neo4j_node import neo4j_normalize_node
from .nodes.ocr_node import ocr_node_func

class AgentState(TypedDict):
    user_id: str
    cv_id: str
    file_path: str
    raw_text: Optional[str]
    is_ocr: bool
    parsed_data: Optional[Dict[str, Any]]
    skill_categories: Optional[Dict[str, str]]
    error: Optional[str]
    status: str

# --- FLOW CŨ (ĐÃ TẠM DỪNG ĐỂ CHUYỂN SANG 100% OCR) ---
# def extract_node(state: AgentState):
#     """Trích xuất text từ PDF bằng PyMuPDF."""
#     print("---EXTRACTING TEXT---")
#     text = extract_from_pdf(state["file_path"])
#     if text:
#         return {"raw_text": text, "is_ocr": False, "status": "extracted"}
#     return {"status": "needs_ocr"}

# def should_ocr(state: AgentState):
#     if state["status"] == "needs_ocr":
#         return "ocr"
#     if state["status"] == "failed":
#         return END
#     return "pii_mask"
# ----------------------------------------------------

async def ocr_node(state: AgentState):
    """
    Dùng Chandra OCR API thông qua ocr_node_func.
    Mọi tài liệu đều đi qua node này để OCR 100%.
    """
    print("---RUNNING CHANDRA OCR (Always-on)---")
    result = await ocr_node_func(state)
    return result

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

# workflow.add_node("extract", extract_node) # Tạm dừng
workflow.add_node("ocr", ocr_node)
workflow.add_node("pii_mask", pii_mask_node)
workflow.add_node("normalization", normalization_node)
workflow.add_node("llm_parse", llm_parse_node)
workflow.add_node("neo4j_normalize", neo4j_normalize_node)
workflow.add_node("cleanup", cleanup_node)

# Bắt đầu thẳng từ OCR theo yêu cầu mới (Always OCR)
workflow.set_entry_point("ocr")

# workflow.add_conditional_edges(
#     "extract",
#     should_ocr,
#     {
#         "ocr": "ocr",
#         "pii_mask": "pii_mask"
#     }
# )

workflow.add_edge("ocr", "pii_mask")
workflow.add_edge("pii_mask", "normalization")
workflow.add_edge("normalization", "llm_parse")
workflow.add_edge("llm_parse", "neo4j_normalize")
workflow.add_edge("neo4j_normalize", "cleanup")
workflow.add_edge("cleanup", END)

app_graph = workflow.compile()
