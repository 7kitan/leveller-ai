import json
import os
import sys

# Setup path for shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.neo4j_client import Neo4jClient

def seed_full_taxonomy():
    client = Neo4jClient()
    
    file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'tech_taxonomy.json')
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with client.driver.session() as session:
        # 1. Seed Ecosystems (COMPRISED_OF)
        print("Seeding Ecosystems...")
        for eco, skills in data.get('ecosystems', {}).items():
            # Create Parent Node
            session.run("MERGE (p:Skill {name: $name}) SET p.category = 'Ecosystem', p.type = 'Domain'", name=eco)
            for skill in skills:
                # Create Child Node & Link
                session.run("""
                    MERGE (c:Skill {name: $skill})
                    WITH c
                    MATCH (p:Skill {name: $parent})
                    MERGE (p)-[:COMPRISED_OF]->(c)
                """, skill=skill, parent=eco)
        
        # 2. Seed Positions (REQUIRES)
        print("Seeding Positions...")
        for pos, requirements in data.get('positions', {}).items():
            session.run("MERGE (p:Skill {name: $name}) SET p.category = 'Position', p.type = 'Role'", name=pos)
            for req in requirements:
                session.run("""
                    MERGE (c:Skill {name: $skill})
                    WITH c
                    MATCH (p:Skill {name: $parent})
                    MERGE (p)-[:REQUIRES]->(c)
                """, skill=req, parent=pos)

        # 3. Seed Special Relations (Grouped by type since Cypher doesn't allow dynamic REL types in MERGE)
        print("Seeding Special Relations...")
        rels_by_type = {}
        for rel in data.get('special_relations', []):
            rtype = rel['type']
            if rtype not in rels_by_type: rels_by_type[rtype] = []
            rels_by_type[rtype].append(rel)
        
        for rtype, items in rels_by_type.items():
            print(f"  - Creating relationships of type: {rtype}")
            for item in items:
                session.run(f"""
                    MERGE (f:Skill {{name: $from_node}})
                    MERGE (t:Skill {{name: $to_node}})
                    WITH f, t
                    MERGE (f)-[:{rtype}]->(t)
                """, from_node=item['from'], to_node=item['to'])

    print("--- Seeding Completed Successfully ---")

if __name__ == "__main__":
    seed_full_taxonomy()
