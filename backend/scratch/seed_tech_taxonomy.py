from neo4j import GraphDatabase
import os
import json
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

class TaxonomySeeder:
    def __init__(self, data_path: str):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.data_path = data_path

    def close(self):
        self.driver.close()

    def seed(self):
        if not os.path.exists(self.data_path):
            print(f"ERROR: Data file not found at {self.data_path}")
            return
            
        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        with self.driver.session() as session:
            print(f"--- [CLEAN] Clearing existing Graph data for fresh import ---")
            session.run("MATCH (n) DETACH DELETE n")
            
            print(f"--- [UPDATE] Merging technology map from {self.data_path} ---")

            
            # 1. Xử lý Ecosystems (Các công nghệ liên đới)
            ecosystems = data.get("ecosystems", {})
            for parent, children in ecosystems.items():
                session.run("MERGE (p:Skill {name: $name})", name=parent)
                for child in children:
                    session.run("""
                        MERGE (c:Skill {name: $c_name})
                        MERGE (p:Skill {name: $p_name})
                        MERGE (c)-[:SUBSET_OF]->(p)
                    """, c_name=child, p_name=parent)
            
            # 2. Xử lý Positions (Vị trí -> Kỹ năng mặc định) - CẢI TIẾN MỚI
            positions = data.get("positions", {})
            for pos_name, skills in positions.items():
                print(f"  > Mapping Position: {pos_name}")
                session.run("MERGE (pos:Skill {name: $name, type: 'Position'})", name=pos_name)
                for s_name in skills:
                    session.run("""
                        MERGE (s:Skill {name: $s_name})
                        MERGE (pos:Skill {name: $pos_name})
                        MERGE (pos)-[:COMPRISED_OF]->(s)
                    """, s_name=s_name, pos_name=pos_name)

            # 3. Xử lý Special Relations
            special_rels = data.get("special_relations", [])
            for rel in special_rels:
                s1, s2, r_type = rel["from"], rel["to"], rel["type"]
                session.run(f"""
                    MERGE (a:Skill {{name: $s1}})
                    MERGE (b:Skill {{name: $s2}})
                    MERGE (a)-[:{r_type}]->(b)
                """, s1=s1, s2=s2)

            print("--- [SUCCESS] Taxonomy with Position Inference Seeded! ---")

if __name__ == "__main__":
    possible_paths = [
        "/app/data/tech_taxonomy.json",
        "../data/tech_taxonomy.json",
        "./data/tech_taxonomy.json",
        "backend/data/tech_taxonomy.json"
    ]
    data_file = next((p for p in possible_paths if os.path.exists(p)), "/app/data/tech_taxonomy.json")

    seeder = TaxonomySeeder(data_file)
    seeder.seed()
    seeder.close()
