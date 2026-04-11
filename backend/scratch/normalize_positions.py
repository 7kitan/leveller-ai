import os
os.environ["NEO4J_URI"] = "bolt://localhost:7687"

from shared.neo4j_client import neo4j_client

def normalize_positions():
    with neo4j_client.driver.session() as session:
        # Chuẩn hóa toàn bộ: Những gì là Role/Position thì Type = Position, Category = Role
        session.run("""
            MATCH (n:Skill)
            WHERE n.type IN ['Position', 'Role', 'position', 'role'] 
               OR n.category IN ['Role', 'Position', 'role', 'position']
            SET n.type = 'Position', n.category = 'Role'
        """)
        print('Successfully normalized all position nodes.')

if __name__ == "__main__":
    normalize_positions()
