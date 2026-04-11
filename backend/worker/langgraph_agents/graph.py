from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict, List, Any
from .nodes_impl import extract_from_pdf, parse_with_llm, mask_pii, normalize_terms
from .neo4j_node import neo4j_normalize_node

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

def extract_node(state: AgentState):
    """Trích xuất text từ PDF bằng PyMuPDF."""
    print("---EXTRACTING TEXT---")
    text = extract_from_pdf(state["file_path"])
    if text:
        return {"raw_text": text, "is_ocr": False, "status": "extracted"}
    return {"status": "needs_ocr"}

def ocr_node(state: AgentState):
    """Dùng OCR nếu text trích xuất trực tiếp bị rỗng."""
    print("---RUNNING OCR---")
    text = "Dữ liệu giả lập từ OCR..."
    if text:
        return {"raw_text": text, "is_ocr": True, "status": "extracted"}
    return {"error": "Không thể trích xuất nội dung từ CV.", "status": "failed"}

def pii_mask_node(state: AgentState):
    """Ẩn danh thông tin nhạy cảm trước khi gửi tới LLM."""
    print("---PII MASKING---")
    if not state.get("raw_text"):
        return {"status": "failed", "error": "No text to mask"}
    
    masked_text = mask_pii(state["raw_text"])
    return {"raw_text": masked_text, "status": "masked"}

def normalization_node(state: AgentState):
    """Chuẩn hóa thuật ngữ kỹ thuật dựa trên Graph Taxonomy trước khi Parse."""
    print("---TERM NORMALIZATION---")
    if not state.get("raw_text"):
        return {"status": "failed", "error": "No text to normalize"}
    
    normalized_text = normalize_terms(state["raw_text"])
    return {"raw_text": normalized_text, "status": "normalized"}

async def llm_parse_node(state: AgentState):
    """Dùng LLM để parse text thành JSON."""
    print("---LLM PARSING---")
    # Tại bước này, raw_text đã được Normalize (ví dụ: "Thiết kế API [API Design]")
    parsed = await parse_with_llm(state["raw_text"])
    if parsed:
        return {"parsed_data": parsed, "status": "parsed"}
    return {"error": "AI không thể phân tích nội dung CV.", "status": "failed"}

def cleanup_node(state: AgentState):
    """Xóa file CV sau khi xử lý."""
    print("---CLEANING UP---")
    import os
    if os.path.exists(state["file_path"]):
        os.remove(state["file_path"])
    return {"status": "completed"}

def should_ocr(state: AgentState):
    if state["status"] == "needs_ocr":
        return "ocr"
    if state["status"] == "failed":
        return END
    return "pii_mask"

# Xây dựng Graph
workflow = StateGraph(AgentState)

workflow.add_node("extract", extract_node)
workflow.add_node("ocr", ocr_node)
workflow.add_node("pii_mask", pii_mask_node)
workflow.add_node("normalization", normalization_node)
workflow.add_node("llm_parse", llm_parse_node)
workflow.add_node("neo4j_normalize", neo4j_normalize_node)
workflow.add_node("cleanup", cleanup_node)

workflow.set_entry_point("extract")
workflow.add_conditional_edges(
    "extract",
    should_ocr,
    {
        "ocr": "ocr",
        "pii_mask": "pii_mask"
    }
)
workflow.add_edge("ocr", "pii_mask")
workflow.add_edge("pii_mask", "normalization")
workflow.add_edge("normalization", "llm_parse")
workflow.add_edge("llm_parse", "neo4j_normalize")
workflow.add_edge("neo4j_normalize", "cleanup")
workflow.add_edge("cleanup", END)

app_graph = workflow.compile()
