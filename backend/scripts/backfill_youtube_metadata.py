"""
Backfill Script: Auto-tag existing YouTube videos with metadata

This script analyzes existing cached YouTube videos and infers:
- language (from title/description)
- skill_level (from title keywords)
- skills (extract from title)

Run with: python -m scripts.backfill_youtube_metadata
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
from sqlalchemy import text
from shared.database import SessionLocal
from shared.models import YouTubeCourse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_language(title: str, description: str) -> str:
    """Detect language from title and description."""
    text = (title + " " + (description or "")).lower()
    
    # Vietnamese indicators
    vi_keywords = [
        "học", "hoc", "khóa", "khoa", "hướng dẫn", "huong dan",
        "cơ bản", "co ban", "nâng cao", "nang cao", "trọn bộ", "tron bo",
        "đầy đủ", "day du", "cho người mới", "cho nguoi moi",
        "từng bước", "tu tung buoc", "giới thiệu", "gioi thieu"
    ]
    
    vi_count = sum(1 for kw in vi_keywords if kw in text)
    
    # English indicators
    en_keywords = [
        "tutorial", "course", "learn", "beginner", "advanced",
        "complete", "full", "guide", "introduction", "step by step"
    ]
    
    en_count = sum(1 for kw in en_keywords if kw in text)
    
    if vi_count > en_count:
        return "vi"
    elif en_count > 0:
        return "en"
    else:
        return None  # Unknown

def detect_skill_level(title: str, description: str) -> str:
    """Detect skill level from title and description."""
    text = (title + " " + (description or "")).lower()
    
    # Level indicators
    level_map = {
        "Junior": ["beginner", "basic", "cơ bản", "co ban", "cho người mới", "cho nguoi moi", "introduction", "giới thiệu"],
        "Mid-level": ["intermediate", "trung cấp", "trung cap"],
        "Senior": ["advanced", "nâng cao", "nang cao", "chuyên sâu", "chuyen sau"],
        "Expert": ["expert", "master", "chuyên gia", "chuyen gia", "professional"]
    }
    
    for level, keywords in level_map.items():
        if any(kw in text for kw in keywords):
            return level
    
    return None  # Unknown

def extract_skills(title: str) -> list:
    """Extract skill names from title."""
    # Common tech skills
    skills = [
        "Python", "JavaScript", "Java", "C++", "C#", "PHP", "Ruby", "Go", "Rust",
        "React", "Vue", "Angular", "Node.js", "Django", "Flask", "Spring",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP",
        "SQL", "MongoDB", "PostgreSQL", "MySQL",
        "Git", "Linux", "DevOps", "CI/CD",
        "Machine Learning", "AI", "Data Science",
        "3D", "3dsmax", "Maya", "Blender", "AutoCAD",
        "Photoshop", "Illustrator", "After Effects"
    ]
    
    found_skills = []
    title_lower = title.lower()
    
    for skill in skills:
        if skill.lower() in title_lower:
            found_skills.append(skill)
    
    return found_skills

def backfill_metadata():
    """Backfill metadata for existing YouTube videos."""
    db = SessionLocal()
    
    try:
        logger.info("=" * 80)
        logger.info("YOUTUBE METADATA BACKFILL")
        logger.info("=" * 80)
        
        # Get videos without metadata
        videos = db.query(YouTubeCourse).filter(
            (YouTubeCourse.language == None) | (YouTubeCourse.skill_level == None)
        ).all()
        
        logger.info(f"\nFound {len(videos)} videos without metadata\n")
        
        updated_count = 0
        skills_added = 0
        
        for video in videos:
            changes = []
            
            # Detect language
            if not video.language:
                lang = detect_language(video.title, video.description)
                if lang:
                    video.language = lang
                    changes.append(f"language={lang}")
            
            # Detect skill level
            if not video.skill_level:
                level = detect_skill_level(video.title, video.description)
                if level:
                    video.skill_level = level
                    changes.append(f"skill_level={level}")
            
            # Extract and tag skills
            skills = extract_skills(video.title)
            if skills:
                for skill in skills:
                    try:
                        db.execute(
                            text("""
                                INSERT INTO youtube_video_skills (video_id, skill_name)
                                VALUES (:vid, :skill)
                                ON CONFLICT (video_id, skill_name) DO NOTHING
                            """),
                            {"vid": video.video_id, "skill": skill}
                        )
                        skills_added += 1
                    except Exception as e:
                        logger.warning(f"Failed to tag skill '{skill}' for {video.video_id}: {e}")
            
            if changes:
                updated_count += 1
                logger.info(f"✓ {video.video_id}: {video.title[:50]}...")
                logger.info(f"  Updates: {', '.join(changes)}")
                if skills:
                    logger.info(f"  Skills: {', '.join(skills)}")
        
        db.commit()
        
        logger.info("\n" + "=" * 80)
        logger.info("BACKFILL COMPLETED")
        logger.info("=" * 80)
        logger.info(f"\n✓ Updated {updated_count} videos")
        logger.info(f"✓ Added {skills_added} skill tags")
        
        # Show statistics
        stats = db.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(language) as with_lang,
                COUNT(skill_level) as with_level,
                COUNT(DISTINCT yvs.video_id) as with_skills
            FROM youtube_courses yc
            LEFT JOIN youtube_video_skills yvs ON yc.video_id = yvs.video_id
        """)).fetchone()
        
        logger.info(f"\nFinal statistics:")
        logger.info(f"  Total videos: {stats.total}")
        logger.info(f"  With language: {stats.with_lang} ({stats.with_lang*100//stats.total}%)")
        logger.info(f"  With skill_level: {stats.with_level} ({stats.with_level*100//stats.total}%)")
        logger.info(f"  With skills tagged: {stats.with_skills} ({stats.with_skills*100//stats.total}%)")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Backfill failed: {e}", exc_info=True)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    backfill_metadata()
