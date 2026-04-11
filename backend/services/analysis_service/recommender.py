from sqlalchemy.orm import Session
from sqlalchemy import text
from shared.models import Course, Skill
from shared.level_mapper import LevelMapper
from shared.llm_utils import get_embedding
import uuid
import logging
import re

logger = logging.getLogger("recommender")

class CourseRecommender:
    def __init__(self, db: Session):
        self.db = db

    def recommend_for_gap(self, skill_name: str, target_level_score: int, gap_type: str = "MISSING", limit: int = 2):
        """
        Gợi ý khóa học dựa trên tên kỹ năng, trình độ mục tiêu và loại Gap.
        Đã cải tiến: Hỗ trợ Semantic Fallback và xử lý cụm kỹ năng phức tạp.
        """
        logger.info(f"Recommending courses for {skill_name} | Gap: {gap_type} | Target Level: {target_level_score}")
        
        # 1. Tiền xử lý tên kỹ năng (Trường hợp AI ghép chuỗi bằng dấu /)
        search_terms = [s.strip() for s in skill_name.split('/')]
        primary_term = search_terms[0] if search_terms else skill_name
        
        try:
            res = []
            # Thử tìm kỹ năng trong Taxonomy để lấy Vector có sẵn
            skill_obj = self.db.query(Skill).filter(Skill.name.ilike(primary_term)).first()
            
            target_vector = None
            if skill_obj and skill_obj.vector is not None:
                target_vector = skill_obj.vector
            else:
                # SEMANTIC FALLBACK: Tạo embedding trực tiếp cho tên kỹ năng
                logger.info(f"Skill '{primary_term}' not in taxonomy. Generating semantic vector...")
                target_vector = get_embedding(primary_term)

            if target_vector and len(target_vector) > 0:
                # Tìm kiếm Vector Similarity trực tiếp trên bảng courses
                query = text("""
                    SELECT id, title, platform, url, level, is_certification, provider,
                           1 - (vector <=> CAST(:skill_vector AS vector)) as similarity
                    FROM courses
                    WHERE vector IS NOT NULL
                    ORDER BY (1 - (vector <=> CAST(:skill_vector AS vector))) DESC
                    LIMIT :limit
                """)
                params = {"skill_vector": target_vector, "limit": limit * 5}
                res = self.db.execute(query, params).fetchall()
            
            # 2. Keyword Fallback (Nếu vector search vẫn rỗng hoặc thất bại)
            if not res:
                logger.info(f"Vector search failed. Falling back to Keyword search for '{primary_term}'")
                query = text("""
                    SELECT id, title, platform, url, level, is_certification, provider, 0.5 as similarity
                    FROM courses
                    WHERE title ILIKE :name_pattern OR provider ILIKE :name_pattern OR tags::text ILIKE :name_pattern
                    LIMIT :limit
                """)
                res = self.db.execute(query, {"name_pattern": f"%{primary_term}%", "limit": limit * 5}).fetchall()

            # 3. Ranking & Filtering
            scored_courses = []
            for r in res:
                c_level_score = LevelMapper.to_score(r.level)
                rank_score = float(r.similarity)
                
                # Level balance penalty
                level_diff = c_level_score - target_level_score
                if level_diff < 0:
                    rank_score += (level_diff * 0.15) # Penalty for 'too easy'
                elif level_diff >= 0:
                    rank_score += 0.05 # Small bonus for matching level
                
                # Certification Boost
                if getattr(r, 'is_certification', False):
                    rank_score += 0.2
                
                scored_courses.append({
                    "course": {
                        "id": str(r.id),
                        "title": r.title,
                        "platform": r.platform,
                        "url": r.url,
                        "level": r.level,
                        "provider": getattr(r, 'provider', 'Unknown'),
                        "is_certification": getattr(r, 'is_certification', False)
                    },
                    "rank": rank_score
                })
            
            scored_courses.sort(key=lambda x: x["rank"], reverse=True)
            return [c["course"] for c in scored_courses[:limit]]
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Recommendation Error: {e}")
            return []
