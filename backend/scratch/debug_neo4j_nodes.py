from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# Đang chạy từ trong container nên load .env từ /app
load_dotenv("/app/.env")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

def debug_neo4j():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        print("--- Node Check ---")
        res = session.run("MATCH (n:Skill) RETURN n.name as name LIMIT 10")
        print("First 10 Skills in DB:", [r["name"] for r in res])
        
        print("\n--- 'Backend Developer' Details ---")
        res = session.run("MATCH (p:Skill) WHERE p.name =~ '(?i).*Backend.*' RETURN p.name as name")
        found_names = [r["name"] for r in res]

        print(f"Nodes containing 'Backend': {found_names}")
        
        for name in found_names:
            print(f"\nRelations for '{name}':")
            res = session.run("MATCH (p:Skill {name: $name})-[r]->(s) RETURN type(r) as rel, s.name as target", name=name)
            for r in res:
                print(f"  --[{r['rel']}]--> {r['target']}")

    driver.close()

if __name__ == "__main__":
    debug_neo4j()
