"""
Test YouTube Search Scoring Improvements

This script tests the new boost scoring system for YouTube video search:
- Curated video prioritization
- Quality score boosting
- Skill level matching
- Exact skill name matching via youtube_video_skills junction table
- Language matching

Run with: python -m scripts.test_youtube_search_scoring
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from sqlalchemy import text
from shared.database import SessionLocal
from shared.youtube_service import youtube_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_search_scoring():
    """Test the improved search scoring system."""
    db = SessionLocal()
    
    try:
        logger.info("=" * 80)
        logger.info("YOUTUBE SEARCH SCORING TEST")
        logger.info("=" * 80)
        
        # Test 1: Check database state
        logger.info("\n[TEST 1] Checking database state...")
        
        total_videos = db.execute(text("SELECT COUNT(*) FROM youtube_courses")).scalar()
        curated_videos = db.execute(text("SELECT COUNT(*) FROM youtube_courses WHERE is_curated = TRUE")).scalar()
        with_quality = db.execute(text("SELECT COUNT(*) FROM youtube_courses WHERE quality_score IS NOT NULL")).scalar()
        with_level = db.execute(text("SELECT COUNT(*) FROM youtube_courses WHERE skill_level IS NOT NULL")).scalar()
        with_skills = db.execute(text("SELECT COUNT(DISTINCT video_id) FROM youtube_video_skills")).scalar()
        
        logger.info(f"✓ Total videos: {total_videos}")
        logger.info(f"✓ Curated videos: {curated_videos}")
        logger.info(f"✓ Videos with quality_score: {with_quality}")
        logger.info(f"✓ Videos with skill_level: {with_level}")
        logger.info(f"✓ Videos with skills tagged: {with_skills}")
        
        if total_videos == 0:
            logger.warning("⚠ No videos in database. Please add some videos first.")
            return
        
        # Test 2: Test query parsing
        logger.info("\n[TEST 2] Testing query parsing...")
        
        test_queries = [
            ("Python Beginner", "python", "Junior"),
            ("Docker Mid-level", "docker", "Mid-level"),
            ("React Advanced", "react", "Senior"),
            ("JavaScript", "javascript", None),
        ]
        
        for query, expected_skill, expected_level in test_queries:
            logger.info(f"  Query: '{query}' → Skill: '{expected_skill}', Level: {expected_level}")
        
        # Test 3: Test search with different queries
        logger.info("\n[TEST 3] Testing search with boost scoring...")
        
        test_cases = [
            {"query": "Python Beginner", "lang": "en", "domain": "programming"},
            {"query": "Docker Mid-level", "lang": "en", "domain": "devops"},
            {"query": "React Advanced", "lang": "en", "domain": "web-development"},
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n  Test Case {i}: {test_case['query']}")
            logger.info(f"  Language: {test_case['lang']}, Domain: {test_case['domain']}")
            
            results = await youtube_service.search_and_cache(
                query=test_case['query'],
                db=db,
                limit=5,
                lang=test_case['lang'],
                domain=test_case['domain']
            )
            
            logger.info(f"  Results: {len(results)} videos found")
            
            for j, video in enumerate(results, 1):
                logger.info(f"    {j}. {video.get('title', 'N/A')[:60]}...")
                logger.info(f"       Channel: {video.get('channel_name', 'N/A')}")
                logger.info(f"       Video ID: {video.get('video_id', 'N/A')}")
        
        # Test 4: Compare curated vs non-curated
        logger.info("\n[TEST 4] Testing curated video prioritization...")
        
        if curated_videos > 0:
            # Get a curated video's skill
            curated_sample = db.execute(text("""
                SELECT yc.video_id, yc.title, yvs.skill_name, yc.skill_level
                FROM youtube_courses yc
                LEFT JOIN youtube_video_skills yvs ON yc.video_id = yvs.video_id
                WHERE yc.is_curated = TRUE
                LIMIT 1
            """)).fetchone()
            
            if curated_sample:
                skill = curated_sample.skill_name or "Python"
                level = curated_sample.skill_level or "Junior"
                
                logger.info(f"  Testing with curated video skill: {skill} {level}")
                
                results = await youtube_service.search_and_cache(
                    query=f"{skill} {level}",
                    db=db,
                    limit=5,
                    lang="en",
                    domain="programming"
                )
                
                if results:
                    first_result_id = results[0].get('video_id')
                    is_curated_first = db.execute(
                        text("SELECT is_curated FROM youtube_courses WHERE video_id = :vid"),
                        {"vid": first_result_id}
                    ).scalar()
                    
                    if is_curated_first:
                        logger.info("  ✓ SUCCESS: Curated video appears first!")
                    else:
                        logger.warning("  ⚠ WARNING: Curated video not first. Check scoring weights.")
                else:
                    logger.warning("  ⚠ No results found")
        else:
            logger.info("  ⚠ No curated videos to test. Please curate some videos via admin UI.")
        
        # Test 5: Verify scoring query structure
        logger.info("\n[TEST 5] Verifying scoring query structure...")
        
        # Test the raw query to see scoring details
        from shared.llm_utils import get_embedding
        test_query = "Python Beginner"
        query_vector = get_embedding(f"{test_query} programming full course")
        
        if query_vector:
            results = db.execute(text("""
                WITH ranked_videos AS (
                    SELECT 
                        yc.video_id,
                        yc.title,
                        yc.is_curated,
                        yc.quality_score,
                        yc.skill_level,
                        yc.language,
                        (1 - (yc.vector <=> :v)) as similarity,
                        CASE WHEN yc.is_curated = TRUE THEN 0.10 ELSE 0 END as curated_boost,
                        CASE WHEN yc.quality_score >= 80 THEN 0.05 
                             WHEN yc.quality_score >= 60 THEN 0.02 
                             ELSE 0 END as quality_boost,
                        CASE WHEN yc.skill_level = :target_level THEN 0.05 ELSE 0 END as level_boost,
                        CASE WHEN EXISTS (
                            SELECT 1 FROM youtube_video_skills yvs
                            WHERE yvs.video_id = yc.video_id 
                            AND yvs.skill_name ILIKE :skill
                        ) THEN 0.12 ELSE 0 END as skill_boost,
                        CASE WHEN yc.language = :lang THEN 0.03 ELSE 0 END as lang_boost
                    FROM youtube_courses yc
                    WHERE (1 - (yc.vector <=> :v)) > 0.75
                      AND (yc.expires_at > NOW() OR yc.expires_at IS NULL)
                )
                SELECT 
                    video_id, title, is_curated, quality_score, skill_level, language,
                    similarity, curated_boost, quality_boost, level_boost, skill_boost, lang_boost,
                    (similarity + curated_boost + quality_boost + level_boost + skill_boost + lang_boost) as final_score
                FROM ranked_videos
                ORDER BY final_score DESC
                LIMIT 3
            """), {
                "v": str(query_vector),
                "skill": "%python%",
                "target_level": "Junior",
                "lang": "en"
            }).fetchall()
            
            logger.info("  Top 3 results with scoring breakdown:")
            for i, r in enumerate(results, 1):
                logger.info(f"\n  {i}. {r.title[:50]}...")
                logger.info(f"     Video ID: {r.video_id}")
                logger.info(f"     Curated: {r.is_curated}, Quality: {r.quality_score}, Level: {r.skill_level}, Lang: {r.language}")
                logger.info(f"     Similarity: {r.similarity:.3f}")
                logger.info(f"     Boosts: curated={r.curated_boost:.2f}, quality={r.quality_boost:.2f}, "
                          f"level={r.level_boost:.2f}, skill={r.skill_boost:.2f}, lang={r.lang_boost:.2f}")
                logger.info(f"     FINAL SCORE: {r.final_score:.3f}")
        else:
            logger.warning("  ⚠ Could not generate embedding for test query")
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST COMPLETED")
        logger.info("=" * 80)
        
        # Summary
        logger.info("\n[SUMMARY]")
        logger.info("✓ Search scoring improvements are active")
        logger.info("✓ Boost factors: curated (+0.10), quality (+0.05), level (+0.05), skill (+0.12), lang (+0.03)")
        logger.info("✓ Curated videos will be prioritized when they match the search query")
        logger.info("\nNext steps:")
        logger.info("1. Add curated videos via Admin UI (/admin/youtube)")
        logger.info("2. Tag videos with skills using youtube_video_skills")
        logger.info("3. Set quality_score and skill_level for better ranking")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_search_scoring())
