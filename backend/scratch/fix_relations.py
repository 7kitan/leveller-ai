from shared.neo4j_client import neo4j_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fix_relations")

def fix_vue_js_relation():
    with neo4j_client.driver.session() as session:
        # 1. Xóa quan hệ ngược (Vue -> JS)
        logger.info("Removing incorrect relation: (Vue)-[:SUBSET_OF]->(JavaScript)...")
        session.run("""
            MATCH (v:Skill {name: 'Vue'})-[r:SUBSET_OF]->(js:Skill {name: 'JavaScript'})
            DELETE r
        """)
        
        # 2. Tạo quan hệ đúng (JS -> Vue)
        logger.info("Creating correct relation: (JavaScript)-[:COMPRISED_OF]->(Vue)...")
        session.run("""
            MATCH (js:Skill {name: 'JavaScript'})
            MATCH (v:Skill {name: 'Vue'})
            MERGE (js)-[:COMPRISED_OF]->(v)
        """)

        # 3. Chuẩn hóa labels cho Frontend Developer và JavaScript
        logger.info("Normalizing labels for Role and Domain entities...")
        session.run("""
            MATCH (s:Skill {name: 'Frontend Developer'}) SET s.type = 'Position', s.category = 'Role'
        """)
        session.run("""
            MATCH (s:Skill {name: 'Game Developer'}) SET s.type = 'Position', s.category = 'Role'
        """)
        session.run("""
            MATCH (s:Skill {name: 'JavaScript'}) SET s.type = 'Skill', s.category = 'Technology'
        """)

    logger.info("Relations fixed successfully.")

if __name__ == "__main__":
    fix_vue_js_relation()
