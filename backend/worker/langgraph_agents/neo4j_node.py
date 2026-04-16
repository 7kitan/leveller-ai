from typing import Dict, Any
# from shared.neo4j_client import neo4j_client
import logging

async def neo4j_normalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node LangGraph: Chuẩn hóa tên kỹ năng dựa trên Neo4j Knowledge Graph.
    (DISABLED: Commented out to bypass Neo4j)
    """
    # logger = logging.getLogger("worker.neo4j_node")
    # raw_skills = state.get("parsed_data", {}).get("skills", [])
    # if not raw_skills:
    #     return {}

    # logging.warning(f"Neo4j Node: Normalizing {len(raw_skills)} skills...")
    # normalized_skills = []

    # with neo4j_client.driver.session() as session:
    #     for skill in raw_skills:
    #         # Tìm kiếm chính xác (không phân biệt hoa thường) tên Kỹ năng hoặc Alias trong Neo4j
    #         query = """
    #         MATCH (s:Skill) 
    #         WHERE toLower(s.name) = toLower($name)
    #         RETURN s.name as canonical_name
    #         LIMIT 1
    #         """
    #         result = session.run(query, name=skill.get("name")).single()
    #         if result:
    #             skill["name"] = result["canonical_name"]
    #         normalized_skills.append(skill)

    # return {"parsed_data": {**state.get("parsed_data", {}), "skills": normalized_skills}}
    return {}
