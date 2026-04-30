"""
Test script for Skill Management API endpoints
Run inside admin container to test the new endpoints
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from shared.database import SessionLocal

def test_skill_endpoints():
    db = SessionLocal()
    
    print("=" * 60)
    print("Testing Skill Management API Endpoints")
    print("=" * 60)
    
    # Test 1: Count total skills
    print("\n1. Testing skills table...")
    try:
        result = db.execute(text("SELECT COUNT(*) FROM skills;")).scalar()
        print(f"   ✅ Total skills in database: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Count pending skills
    print("\n2. Testing pending_skills table...")
    try:
        result = db.execute(text("SELECT COUNT(*) FROM pending_skills;")).scalar()
        print(f"   ✅ Total pending skills: {result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Check youtube_video_skills with skill_id
    print("\n3. Testing youtube_video_skills linkage...")
    try:
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(skill_id) as linked,
                COUNT(*) - COUNT(skill_id) as unlinked
            FROM youtube_video_skills
        """)).fetchone()
        print(f"   ✅ Total: {result[0]}, Linked: {result[1]}, Unlinked: {result[2]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Sample skills by category
    print("\n4. Testing skill categories...")
    try:
        result = db.execute(text("""
            SELECT category, COUNT(*) as count
            FROM skills
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
            LIMIT 5
        """)).fetchall()
        print(f"   ✅ Top 5 categories:")
        for row in result:
            print(f"      - {row[0]}: {row[1]} skills")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Check if React, JavaScript, Web Development are linked
    print("\n5. Testing YouTube video skills linkage...")
    try:
        result = db.execute(text("""
            SELECT yvs.skill_name, s.name as master_name, yvs.skill_id
            FROM youtube_video_skills yvs
            LEFT JOIN skills s ON yvs.skill_id = s.id
            LIMIT 5
        """)).fetchall()
        print(f"   ✅ Sample linkages:")
        for row in result:
            status = "✓ Linked" if row[2] else "✗ Unlinked"
            print(f"      - {row[0]} → {row[1] or 'N/A'} ({status})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    db.close()
    
    print("\n" + "=" * 60)
    print("✅ Database tests completed!")
    print("=" * 60)
    print("\nAPI Endpoints Available:")
    print("  GET    /admin/skills")
    print("  POST   /admin/skills")
    print("  GET    /admin/skills/categories")
    print("  GET    /admin/skills/pending")
    print("  POST   /admin/skills/pending/{id}/approve")
    print("  POST   /admin/skills/pending/{id}/reject")
    print("  POST   /admin/skills/pending/{id}/merge")

if __name__ == "__main__":
    test_skill_endpoints()
