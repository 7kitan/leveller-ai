from shared.neo4j_client import neo4j_client
import logging

logger = logging.getLogger("taxonomy_service")

class TaxonomyService:
    def __init__(self):
        self.client = neo4j_client

    def get_all_skills(self, limit: int = 100, skip: int = 0):
        """Lấy danh sách tất cả kỹ năng và bí danh."""
        query = """
        MATCH (s:Skill)
        RETURN s.name as name, 
               s.category as category, 
               s.type as type, 
               coalesce(s['aliases'], []) as aliases
        ORDER BY s.name ASC
        SKIP $skip LIMIT $limit
        """
        with self.client.driver.session() as session:
            result = session.run(query, skip=skip, limit=limit)
            return [record.data() for record in result]

    def create_or_update_skill(self, name: str, category: str = "Technology", skill_type: str = "Skill", aliases: list = None):
        """Thêm mới hoặc cập nhật thông tin một kỹ năng."""
        if aliases is None: aliases = []
        
        query = """
        MERGE (s:Skill {name: $name})
        SET s.category = $category,
            s.type = $skill_type,
            s.aliases = $aliases,
            s.updated_at = datetime()
        RETURN s.name as name
        """
        with self.client.driver.session() as session:
            result = session.run(query, name=name, category=category, skill_type=skill_type, aliases=aliases)
            return result.single()

    def delete_skill(self, name: str):
        """Xóa một kỹ năng và các quan hệ liên quan."""
        query = "MATCH (s:Skill {name: $name}) DETACH DELETE s"
        with self.client.driver.session() as session:
            session.run(query, name=name)
            return True

    def link_skills(self, parent_name: str, child_name: str, rel_type: str = "COMPRISED_OF"):
        """Tạo mối quan hệ giữa hai kỹ năng (ví dụ: Backend -> API Design)."""
        if rel_type not in ["COMPRISED_OF", "SUBSET_OF", "RELATED_TO", "BUILT_ON"]:
            raise ValueError("Invalid relationship type")

        query = f"""
        MATCH (p:Skill {{name: $parent_name}})
        MATCH (c:Skill {{name: $child_name}})
        MERGE (p)-[r:{rel_type}]->(c)
        RETURN type(r)
        """
        with self.client.driver.session() as session:
            result = session.run(query, parent_name=parent_name, child_name=child_name)
            return result.single()

    def get_all_relationships(self, limit: int = 100):
        """Lấy danh sách các mối quan hệ kỹ năng hiện có."""
        query = """
        MATCH (p:Skill)-[r]->(c:Skill)
        RETURN p.name as parent, type(r) as rel_type, c.name as child
        LIMIT $limit
        """
        with self.client.driver.session() as session:
            result = session.run(query, limit=limit)
            return [record.data() for record in result]

    def get_relationships_grouped(self, limit: int = 100, parent_type: str = None):
        """Lấy danh sách quan hệ được nhóm theo Kỹ năng Cha, có thể lọc theo loại (Ưu tiên Position)."""
        type_filter = "WHERE p.type = $parent_type" if parent_type else ""
        query = f"""
        MATCH (p:Skill)-[r]->(c:Skill)
        {type_filter}
        WITH p, collect({{name: c.name, type: type(r)}}) as children_list
        ORDER BY CASE WHEN p.type = 'Position' THEN 0 ELSE 1 END, p.name ASC
        LIMIT $limit
        OPTIONAL MATCH (p)<-[:COMPRISED_OF|SUBSET_OF]-(parent)
        RETURN p.name as parent, 
               p.type as parent_type,
               p.category as parent_category,
               count(parent) = 0 as is_root,
               children_list as children
        """
        logger.info(f"Executing grouped relationships query with limit={limit}, parent_type={parent_type}")
        
        with self.client.driver.session() as session:
            result = session.run(query, limit=limit, parent_type=parent_type)
            data = [record.data() for record in result]
            
            logger.info(f"Neo4j returned {len(data)} grouped records.")
            if len(data) > 0:
                logger.debug(f"First 3 parents: {[d['parent'] for d in data[:3]]}")
            
            return data

    def delete_relationship(self, parent: str, child: str, rel_type: str):
        """Xóa một mối quan hệ kỹ năng."""
        query = f"MATCH (p:Skill {{name: $parent}})-[r:{rel_type}]->(c:Skill {{name: $child}}) DELETE r"
        with self.client.driver.session() as session:
            session.run(query, parent=parent, child=child)
            return True

    def get_canonical_mapping(self) -> dict:
        """
        Tạo bảng tra cứu từ Alias sang Canonical Name.
        Dùng cho bước Pre-parsing (Normalization).
        """
        query = """
        MATCH (s:Skill)
        WHERE 'aliases' IN keys(s) AND s.aliases IS NOT NULL AND size(s.aliases) > 0
        RETURN s.name as canonical, s.aliases as aliases
        """
        mapping = {}
        with self.client.driver.session() as session:
            result = session.run(query)
            for record in result:
                for alias in record["aliases"]:
                    mapping[alias.lower().strip()] = record["canonical"]
        return mapping

taxonomy_service = TaxonomyService()
