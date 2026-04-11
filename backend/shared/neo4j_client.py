from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def find_transferable_skills(self, user_skills: list, target_skill: str):
        """
        Truy vấn đồ thị để tìm các kỹ năng liên quan. 
        Hỗ trợ tìm kiếm xuyên suốt các quan hệ Tech (Cha-Con, Anh-Em qua gốc chung).
        """
        if not user_skills:
            return []
            
        with self.driver.session() as session:
            # Truy vấn linh hoạt: tìm đường đi ngắn nhất giữa target và user_skills
            query = """
            MATCH (target:Skill) 
            WHERE target.name =~ ('(?i)' + $target_skill)
            MATCH (user_s:Skill) 
            WHERE ANY(us IN $user_skills WHERE toLower(user_s.name) = toLower(us) OR toLower(us) CONTAINS toLower(user_s.name))
            MATCH p = shortestPath((target)-[*1..2]-(user_s))
            RETURN user_s.name as related_skill, 
                   type(relationships(p)[0]) as rel_type,
                   startNode(relationships(p)[0]) = target as is_parent_req,
                   length(p) as distance
            ORDER BY distance ASC
            LIMIT 5
            """
            result = session.run(query, target_skill=target_skill, user_skills=user_skills)

            relationships = []
            for record in result:
                relationships.append({
                    "skill": record["related_skill"],
                    "type": record["rel_type"],
                    "is_child_of_req": record["is_parent_req"],
                    "distance": record["distance"]
                })
            return relationships

    def get_gap_classification(self, user_skills: list, target_skill: str) -> dict:
        """
        Phân loại Gap dựa trên quan hệ trong Graph và trả về giải thích chi tiết.
        """
        if not user_skills: return {"gap_type": "MISSING", "matched_by": None, "reason": None}

        with self.driver.session() as session:
            query = """
            MATCH (target:Skill) WHERE target.name =~ ('(?i)' + $target_skill)
            MATCH (user_s:Skill) WHERE ANY(us IN $user_skills WHERE toLower(user_s.name) = toLower(us))
            
            // 1. Check Framework Gap (Parent-Child)
            OPTIONAL MATCH (target)-[r_par:SUBSET_OF|COMPRISED_OF|BUILT_ON]->(user_s)
            
            // 2. Check Transition (Siblings)
            OPTIONAL MATCH (target)-[:SUBSET_OF]->(p:Skill)<-[:SUBSET_OF]-(user_s)
            
            WITH user_s, r_par, p,
                 CASE 
                    WHEN r_par IS NOT NULL THEN 'FRAMEWORK_GAP'
                    WHEN p IS NOT NULL THEN 'TRANSITION'
                    ELSE 'MISSING'
                 END as g_type
            WHERE g_type <> 'MISSING'
            
            RETURN g_type as gap_type, 
                   user_s.name as matched_by,
                   CASE 
                     WHEN r_par IS NOT NULL THEN 'Là thành phần của ' + user_s.name
                     WHEN p IS NOT NULL THEN 'Cùng hệ sinh thái với ' + user_s.name + ' (qua ' + p.name + ')'
                     ELSE ''
                   END as reason
            LIMIT 1
            """
            result = session.run(query, target_skill=target_skill, user_skills=user_skills).single()
            if result:
                return {
                    "gap_type": result["gap_type"],
                    "matched_by": result["matched_by"],
                    "reason": result["reason"]
                }
            return {"gap_type": "MISSING", "matched_by": None, "reason": None}

    def is_skill_transferable(self, skill_name: str) -> bool:
        """
        Kiểm tra kỹ năng có phải là kỹ năng mềm hoặc kỹ năng phổ quát (Transferable) không.
        """
        with self.driver.session() as session:
            query = """
            MATCH (s:Skill) 
            WHERE s.name =~ ('(?i)' + $skill_name)
            AND (s.category IN ['Soft Skill', 'Methodology', 'Universal', 'Role', 'Foundational Standards'] OR s.type = 'Position')
            RETURN count(s) > 0 as is_transferable
            """
            result = session.run(query, skill_name=skill_name).single()
            return result["is_transferable"] if result else False

    def is_foundational_standard(self, skill_name: str) -> bool:
        """
        Kiểm tra xem một skill có phải là tiêu chuẩn nền tảng (Clean Code, Modularization, v.v.)
        """
        query = """
        MATCH (s:Skill)-[:SUBSET_OF]->(p:Skill {name: 'Foundational Standards'})
        WHERE toLower(s.name) = toLower($name)
        RETURN count(s) > 0 as is_standard
        """
        with self.driver.session() as session:
            result = session.run(query, name=skill_name).single()
            return result["is_standard"] if result else False

    def is_primary_tech(self, skill_name: str) -> bool:
        """
        Dùng Neo4j để kiểm tra xem một kỹ năng có phải là Core Technology hay không.
        """
        query = """
        MATCH (s:Skill) WHERE toLower(s.name) = toLower($name)
        OPTIONAL MATCH (s)-[:SUBSET_OF|COMPRISED_OF|BUILT_ON]->(p:Skill)
        WHERE NOT p.category IN ['Position', 'Domain', 'Role', 'Methodology']
        RETURN count(p) = 0 as is_root
        """
        with self.driver.session() as session:
            result = session.run(query, name=skill_name).single()
            if result is None: return True
            return result["is_root"]

    # --- ROLE-BASED INFERENCE (PURE GRAPH) ---

    def get_positions(self) -> list:
        """Lấy danh sách các vai trò chuyên môn (Positions) từ Graph."""
        query = "MATCH (p:Skill {type: 'Position'}) RETURN p.name as name"
        with self.driver.session() as session:
            result = session.run(query)
            return [record["name"] for record in result]

    def is_skill_implied_by_role(self, skill_name: str, role_name: str) -> bool:
        """
        Kiểm tra chuyên sâu trong Graph xem một kỹ năng có được ngầm định bởi vai trò hay không.
        Hỗ trợ quan hệ đa tầng (Role -> Category -> Skill).
        """
        if not role_name: return False
        
        query = """
        MATCH (p:Skill {name: $role_name, type: 'Position'})-[:COMPRISED_OF|SUBSET_OF*1..2]->(s:Skill)
        WHERE toLower(s.name) = toLower($skill_name)
        RETURN count(s) > 0 as is_implied
        """
        with self.driver.session() as session:
            result = session.run(query, role_name=role_name, skill_name=skill_name).single()
            return result["is_implied"] if result else False

neo4j_client = Neo4jClient()
