import os
os.environ["NEO4J_URI"] = "bolt://localhost:7687"

from shared.neo4j_client import neo4j_client

def analyze_api_positions():
    with neo4j_client.driver.session() as session:
        # 1. Tổng số Position
        total_count = session.run("MATCH (p:Skill) WHERE p.type = 'Position' RETURN count(p) as count").single()['count']
        
        # 2. Chi tiết quan hệ
        query = """
        MATCH (p:Skill)
        WHERE p.type = 'Position'
        OPTIONAL MATCH (p)-[r]->(c:Skill)
        RETURN p.name as name, count(r) as children_count
        ORDER BY children_count DESC
        """
        result = session.run(query)
        
        print(f"\nTotal Position nodes in DB: {total_count}")
        print("\n=== DETAILED ANALYSIS ===")
        in_api_count = 0
        for rec in result:
            status = "VISIBLE in API" if rec['children_count'] > 0 else "HIDDEN (No children)"
            if rec['children_count'] > 0:
                in_api_count += 1
            print(f"Position: {rec['name']:<25} | Children: {rec['children_count']:<3} | Status: {status}")
            
        print(f"\nFinal Analysis: Only {in_api_count} positions have relationships and thus appear in the Grouped Relations API.")

if __name__ == "__main__":
    analyze_api_positions()
