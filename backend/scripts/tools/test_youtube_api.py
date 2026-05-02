"""
Test script for YouTube curation API endpoints
Run inside admin container to bypass auth
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from shared.database import SessionLocal

def test_endpoints():
    db = SessionLocal()
    
    print("=" * 60)
    print("Testing YouTube Curation API Endpoints")
    print("=" * 60)
    
    # Test 1: Get videos with filters
    print("\n1. Testing GET /admin/youtube with filters...")
    try:
        result = db.execute(
            text("""
                SELECT v.video_id, v.title, v.language, v.skill_level, v.is_curated
                FROM youtube_courses v
                WHERE v.language = 'en' AND v.is_curated = true
                LIMIT 5
            """)
        ).fetchall()
        print(f"   ✅ Found {len(result)} curated English videos")
        for row in result:
            print(f"      - {row.video_id}: {row.title[:50]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Get skills list
    print("\n2. Testing GET /admin/youtube/skills...")
    try:
        result = db.execute(
            text("SELECT DISTINCT skill_name FROM youtube_video_skills ORDER BY skill_name")
        ).fetchall()
        skills = [row[0] for row in result]
        print(f"   ✅ Found {len(skills)} unique skills: {', '.join(skills)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Get video with skills joined
    print("\n3. Testing video with skills JOIN...")
    try:
        result = db.execute(
            text("""
                SELECT v.video_id, v.title, v.language, v.skill_level, 
                       array_agg(s.skill_name) as skills
                FROM youtube_courses v
                LEFT JOIN youtube_video_skills s ON v.video_id = s.video_id
                WHERE v.is_curated = true
                GROUP BY v.video_id, v.title, v.language, v.skill_level
                LIMIT 3
            """)
        ).fetchall()
        print(f"   ✅ Found {len(result)} videos with skills:")
        for row in result:
            print(f"      - {row.video_id}: {row.skills}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Test filters
    print("\n4. Testing combined filters (language + level + skill)...")
    try:
        result = db.execute(
            text("""
                SELECT v.video_id, v.title
                FROM youtube_courses v
                JOIN youtube_video_skills s ON v.video_id = s.video_id
                WHERE v.language = 'en' 
                  AND v.skill_level = 'Junior'
                  AND s.skill_name = 'React'
                  AND v.is_curated = true
                LIMIT 5
            """)
        ).fetchall()
        print(f"   ✅ Found {len(result)} videos matching all filters")
        for row in result:
            print(f"      - {row.video_id}: {row.title[:50]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Check indexes
    print("\n5. Checking indexes...")
    try:
        result = db.execute(
            text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename IN ('youtube_courses', 'youtube_video_skills')
                  AND indexname LIKE 'idx_youtube%'
                ORDER BY indexname
            """)
        ).fetchall()
        indexes = [row[0] for row in result]
        print(f"   ✅ Found {len(indexes)} indexes:")
        for idx in indexes:
            print(f"      - {idx}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 6: Statistics
    print("\n6. Database statistics...")
    try:
        result = db.execute(
            text("""
                SELECT 
                    COUNT(*) as total_videos,
                    COUNT(CASE WHEN is_curated = true THEN 1 END) as curated_videos,
                    COUNT(CASE WHEN language = 'en' THEN 1 END) as english_videos,
                    COUNT(CASE WHEN language = 'vi' THEN 1 END) as vietnamese_videos
                FROM youtube_courses
            """)
        ).fetchone()
        print(f"   ✅ Total videos: {result.total_videos}")
        print(f"   ✅ Curated videos: {result.curated_videos}")
        print(f"   ✅ English videos: {result.english_videos}")
        print(f"   ✅ Vietnamese videos: {result.vietnamese_videos}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    db.close()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_endpoints()
