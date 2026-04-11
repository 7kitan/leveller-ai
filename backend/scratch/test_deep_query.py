import json
import os
import sys

# Setup path for shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.neo4j_client import Neo4jClient

def test_deep_hierarchy():
    client = Neo4jClient()
    with client.driver.session() as session:
        # Lấy thử 5 quan hệ đầu tiên bao gồm cả category của con
        query = """
        MATCH (p:Skill)-[r]->(c:Skill)
        RETURN p.name as parent, p.category as p_cat, 
               collect({name: c.name, rel_type: type(r), cat: c.category}) as children
        LIMIT 5
        """
        results = session.run(query)
        for r in results:
            print(f"Parent: {r['parent']} ({r['p_cat']})")
            for child in r['children']:
                print(f"  -> Child: {child['name']} ({child['cat']})")

if __name__ == "__main__":
    test_deep_hierarchy()
