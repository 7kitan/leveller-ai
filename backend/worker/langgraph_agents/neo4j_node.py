from typing import Dict, Any
from shared.neo4j_client import neo4j_client
import logging

async def neo4j_normalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node LangGraph: Chuẩn hóa tên kỹ năng dựa trên Neo4j Knowledge Graph.
    Ví dụ: 'nodejs' -> 'Node.js', 'reactjs' -> 'React'
    """
    if not state.get("parsed_data") or "skills" not in state["parsed_data"]:
        return state

    raw_skills = state["parsed_data"]["skills"]
    normalized_skills = []
    skill_categories = {}

    logging.warning(f"Neo4j Node: Normalizing {len(raw_skills)} skills...")

    with neo4j_client.driver.session() as session:
        for skill_obj in raw_skills:
            # Handle both string (legacy) and dict (new format) skill entries
            if isinstance(skill_obj, str):
                name_to_query = skill_obj.strip()
            else:
                name_to_query = skill_obj.get("skill_name", skill_obj.get("skill", "Unknown")).strip()

            # Tìm kiếm chính xác (không phân biệt hoa thường) tên Kỹ năng hoặc Alias trong Neo4j
            query = """
            MATCH (s:Skill)
            WHERE toLower(s.name) = toLower($name)
            OPTIONAL MATCH (s)-[:BELONGS_TO]->(c:Category)
            RETURN s.name as canonical_name, c.name as category
            """
            result = session.run(query, name=name_to_query).single()
            
            if result:
                canonical_name = result["canonical_name"]
                
                # Cập nhật tên chuẩn nhưng giữ lại metadata nếu là dict
                if isinstance(skill_obj, str):
                    normalized_item = canonical_name
                else:
                    normalized_item = skill_obj.copy()
                    normalized_item["skill_name"] = canonical_name
                
                normalized_skills.append(normalized_item)
                
                if result["category"]:
                    skill_categories[canonical_name] = result["category"]
                logging.warning(f"  - Matched: '{name_to_query}' -> '{canonical_name}' ({result['category']})")
            else:
                # Nếu không thấy trong Graph, giữ nguyên tên/đối tượng gốc
                normalized_skills.append(skill_obj)
                logging.warning(f"  - No match for: '{name_to_query}', keeping original.")

    # Cập nhật kết quả bóc tách đã được chuẩn hóa (Xóa trùng lặp dựa trên tên)
    seen_names = set()
    unique_skills = []
    for s in normalized_skills:
        name = s if isinstance(s, str) else s.get("skill_name")
        if name not in seen_names:
            unique_skills.append(s)
            seen_names.add(name)

    state["parsed_data"]["skills"] = unique_skills
    state["skill_categories"] = skill_categories
    
    return state
