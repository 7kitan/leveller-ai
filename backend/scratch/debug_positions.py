import os
# Thiết lập địa chỉ Neo4j cho môi trường local trước khi import client
os.environ["NEO4J_URI"] = "bolt://localhost:7687"

from shared.neo4j_client import neo4j_client
import json

def debug_positions():
    with neo4j_client.driver.session() as session:
        # Tìm tất cả các ứng viên là Vị trí
        query = """
        MATCH (n:Skill)
        WHERE n.type IN ['Position', 'Role', 'position', 'role'] 
           OR n.category IN ['Role', 'Position', 'role', 'position']
        OPTIONAL MATCH (parent)-[r]->(n)
        RETURN n.name as name, 
               n.type as type, 
               n.category as category, 
               collect({parent: parent.name, rel: type(r)}) as incoming
        """
        result = session.run(query)
        
        print("\n=== DEBUG POSITIONS DATA ===")
        for rec in result:
            incoming = [i for i in rec['incoming'] if i['parent'] is not None]
            # Một nút được coi là Root nếu không có quan hệ CHA-CON (COMPRISED_OF, SUBSET_OF) trỏ tới nó
            hierarchical_parents = [i for i in incoming if i['rel'] in ['COMPRISED_OF', 'SUBSET_OF']]
            is_root = len(hierarchical_parents) == 0
            
            print(f"Node: {rec['name']}")
            print(f"  - Type: {rec['type']}")
            print(f"  - Category: {rec['category']}")
            print(f"  - Hierarchical Parents: {hierarchical_parents}")
            print(f"  - Is Root: {is_root}")
            print("-" * 30)

if __name__ == "__main__":
    debug_positions()
