import json
import os
import sys

# Thêm đường dẫn để import shared
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.neo4j_client import Neo4jClient

def compare():
    client = Neo4jClient()
    
    # 1. Đọc dữ liệu từ JSON
    with open('data/tech_taxonomy.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    json_skills = set()
    json_rels = [] # (parent, child, type)
    
    # Duyệt Ecosystems
    for eco, skills in data.get('ecosystems', {}).items():
        json_skills.add(eco)
        for s in skills:
            json_skills.add(s)
            json_rels.append((eco, s, "COMPRISED_OF"))
            
    # Duyệt Positions
    for pos, components in data.get('positions', {}).items():
        json_skills.add(pos)
        for comp in components:
            json_skills.add(comp)
            json_rels.append((pos, comp, "REQUIRES"))
            
    # Duyệt Special Relations
    for rel in data.get('special_relations', []):
        json_skills.add(rel['from'])
        json_skills.add(rel['to'])
        json_rels.append((rel['from'], rel['to'], rel['type']))
        
    print(f"--- JSON Stats ---")
    print(f"Total Unique Skills: {len(json_skills)}")
    print(f"Total Relationships: {len(json_rels)}")
    
    # 2. Truy vấn Database
    with client.driver.session() as session:
        # Lấy danh sách Skill hiện có
        db_skills_res = session.run("MATCH (s:Skill) RETURN s.name as name")
        db_skills = {record["name"] for record in db_skills_res}
        
        # Lấy danh sách quan hệ hiện có
        db_rels_res = session.run("MATCH (p:Skill)-[r]->(c:Skill) RETURN p.name as parent, type(r) as type, c.name as child")
        db_rels = {(record["parent"], record["child"], record["type"]) for record in db_rels_res}
        
    print(f"\n--- Database Stats ---")
    print(f"Skills in DB: {len(db_skills)}")
    print(f"Relationships in DB: {len(db_rels)}")
    
    # 3. So sánh
    missing_skills = json_skills - db_skills
    missing_rels = [r for r in json_rels if r not in db_rels]
    
    print(f"\n--- Comparison ---")
    print(f"Missing Skills: {len(missing_skills)}")
    print(f"Missing Relationships: {len(missing_rels)}")
    
    if missing_skills:
        print("\nSome missing skills sample:")
        print(list(missing_skills)[:10])
        
    if missing_rels:
        print("\nSome missing relationships sample:")
        print(missing_rels[:10])

if __name__ == "__main__":
    compare()
