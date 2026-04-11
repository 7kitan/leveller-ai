from typing import Dict, Any
from shared.neo4j_client import neo4j_client
import logging

logger = logging.getLogger("cv_parsing")

async def neo4j_normalize_node_func(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node LangGraph: Chuẩn hóa tên kỹ năng dựa trên Neo4j Knowledge Graph.
    Ví dụ: 'nodejs' -> 'Node.js', 'reactjs' -> 'React'
    """
    if not state.get("parsed_data") or "skills" not in state["parsed_data"]:
        return state

    raw_skills = state["parsed_data"]["skills"]
    normalized_skills = []
    skill_categories = {}

    logger.info(f"--- [NEO4J NORMALIZATION NODE] Normalizing {len(raw_skills)} skills ---")

    with neo4j_client.driver.session() as session:
        for skill_name in raw_skills:
            query = """
            MATCH (s:Skill)
            WHERE toLower(s.name) = toLower($name)
            OPTIONAL MATCH (s)-[:BELONGS_TO]->(c:Category)
            RETURN s.name as canonical_name, c.name as category
            """
            result = session.run(query, name=skill_name.strip()).single()
            
            if result:
                canonical_name = result["canonical_name"]
                normalized_skills.append(canonical_name)
                if result["category"]:
                    skill_categories[canonical_name] = result["category"]
            else:
                normalized_skills.append(skill_name)

    state["parsed_data"]["skills"] = list(set(normalized_skills))
    state["skill_categories"] = skill_categories
    
    return state
