from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict, List, Any
from .nodes_impl import parse_with_llm, mask_pii, normalize_terms
# from .neo4j_node import neo4j_normalize_node
from ..tasks.cv_parsing_utils import extract_cv_hybrid

# ... (AgentState and other nodes remain unchanged)

# Xây dựng Graph
workflow = StateGraph(AgentState)

workflow.add_node("extraction", extraction_node)
workflow.add_node("pii_mask", pii_mask_node)
workflow.add_node("normalization", normalization_node)
workflow.add_node("llm_parse", llm_parse_node)
# workflow.add_node("neo4j_normalize", neo4j_normalize_node)
workflow.add_node("cleanup", cleanup_node)

# Bắt đầu từ Hybrid Extraction
workflow.set_entry_point("extraction")

workflow.add_edge("extraction", "pii_mask")
workflow.add_edge("pii_mask", "normalization")
workflow.add_edge("normalization", "llm_parse")
# workflow.add_edge("llm_parse", "neo4j_normalize")
# workflow.add_edge("neo4j_normalize", "cleanup")
workflow.add_edge("llm_parse", "cleanup")
workflow.add_edge("cleanup", END)

app_graph = workflow.compile()

