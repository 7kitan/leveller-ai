import json
import os
import sys

# Setup path for shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.neo4j_client import Neo4jClient

def audit():
    client = Neo4jClient()
    with client.driver.session() as session:
        # Check parent categories and their relations
        query = """
        MATCH (p:Skill)-[r]->(c:Skill)
        RETURN p.category as category, 
               p.name as parent_name, 
               count(c) as child_count
        ORDER BY p.category, parent_name
        """
        results = session.run(query)
        
        stats = {}
        for record in results:
            cat = record["category"] or "Uncategorized"
            if cat not in stats: stats[cat] = []
            stats[cat].append({
                "name": record["parent_name"],
                "children": record["child_count"]
            })
            
        print("--- Taxonomy Audit Result ---")
        for cat, nodes in stats.items():
            print(f"\n[Category: {cat}] ({len(nodes)} groups)")
            for node in nodes[:5]: # Show first 5
                print(f"  - {node['name']} ({node['children']} children)")
            if len(nodes) > 5:
                print(f"  ... and {len(nodes) - 5} more")

if __name__ == "__main__":
    audit()
