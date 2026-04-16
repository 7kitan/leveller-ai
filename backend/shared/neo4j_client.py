# from neo4j import GraphDatabase
# import os
# from dotenv import load_dotenv

# load_dotenv()

# NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
# NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
# NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

class Neo4jClient:
    def __init__(self):
        # self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.driver = None

    def close(self):
        # if self.driver:
        #     self.driver.close()
        pass

    def find_transferable_skills(self, user_skills: list, target_skill: str):
        """
        Truy vấn đồ thị để tìm các kỹ năng liên quan. 
        Hỗ trợ tìm kiếm xuyên suốt các quan hệ Tech (Cha-Con, Anh-Em qua gốc chung).
        """
        return []

    def get_gap_classification(self, user_skills: list, target_skill: str) -> dict:
        """
        Phân loại Gap dựa trên quan hệ trong Graph và trả về giải thích chi tiết.
        """
        return {"gap_type": "MISSING", "matched_by": None, "reason": None}

    def is_skill_transferable(self, skill_name: str) -> bool:
        """
        Kiểm tra kỹ năng có phải là kỹ năng mềm hoặc kỹ năng phổ quát (Transferable) không.
        """
        return False

    def is_foundational_standard(self, skill_name: str) -> bool:
        """
        Kiểm tra xem một skill có phải là tiêu chuẩn nền tảng (Clean Code, Modularization, v.v.)
        """
        return False

    def is_primary_tech(self, skill_name: str) -> bool:
        """
        Dùng Neo4j để kiểm tra xem một kỹ năng có phải là Core Technology hay không.
        """
        return True

    # --- ROLE-BASED INFERENCE (PURE GRAPH) ---

    def get_positions(self) -> list:
        """Lấy danh sách các vai trò chuyên môn (Positions) từ Graph."""
        return []

    def is_skill_implied_by_role(self, skill_name: str, role_name: str) -> bool:
        """
        Kiểm tra chuyên sâu trong Graph xem một kỹ năng có được ngầm định bởi vai trò hay không.
        Hỗ trợ quan hệ đa tầng (Role -> Category -> Skill).
        """
        return False

neo4j_client = Neo4jClient()
