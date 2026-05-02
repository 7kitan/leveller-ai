"""
Test script to verify alternative skill groups functionality.

Usage:
    python scripts/test_skill_groups.py

This script will:
1. Check if migration added new columns
2. Test skill extraction with alternative patterns
3. Verify gap analysis handles groups correctly
"""

import os
import sys
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import JobSkillRequirement, Job, Skill
from shared.skill_extraction import save_extracted_skills_to_db
from shared.llm_utils import extract_skills_from_requirements

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/advisor_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def test_migration():
    """Test 1: Verify migration added new columns"""
    print("\n" + "="*60)
    print("TEST 1: Verify Migration")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Check if columns exist
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'job_skill_requirement' 
            AND column_name IN ('is_group', 'group_strategy', 'alternative_skills', 'min_required')
            ORDER BY column_name
        """))
        
        columns = result.fetchall()
        
        if len(columns) == 4:
            print("✅ All 4 columns exist:")
            for col in columns:
                print(f"   - {col[0]} ({col[1]})")
            return True
        else:
            print(f"❌ Expected 4 columns, found {len(columns)}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        db.close()


async def test_skill_extraction():
    """Test 2: Test skill extraction with alternative patterns"""
    print("\n" + "="*60)
    print("TEST 2: Skill Extraction with Alternative Patterns")
    print("="*60)
    
    test_cases = [
        {
            "name": "Vietnamese OR pattern",
            "text": "Thành thạo Blender, Maya, hoặc 3ds Max",
            "expected_group": True,
            "expected_alternatives": ["Blender", "Maya", "3ds Max"]
        },
        {
            "name": "English OR pattern",
            "text": "Proficient in React, Vue, or Angular",
            "expected_group": True,
            "expected_alternatives": ["React", "Vue", "Angular"]
        },
        {
            "name": "At least one pattern",
            "text": "Experience with at least one of: AWS, Azure, GCP",
            "expected_group": True,
            "expected_alternatives": ["AWS", "Azure", "GCP"]
        },
        {
            "name": "Slash pattern",
            "text": "Knowledge of Python/Java/C++",
            "expected_group": True,
            "expected_alternatives": ["Python", "Java", "C++"]
        },
        {
            "name": "Regular skill (no group)",
            "text": "5 years experience with Docker",
            "expected_group": False,
            "expected_alternatives": []
        }
    ]
    
    results = []
    for test in test_cases:
        print(f"\n📝 Testing: {test['name']}")
        print(f"   Input: {test['text']}")
        
        try:
            # Extract skills using LLM
            extracted = await extract_skills_from_requirements(test['text'])
            
            if not extracted:
                print(f"   ❌ No skills extracted")
                results.append(False)
                continue
            
            skill = extracted[0]
            is_group = skill.get("is_group", False)
            alternatives = skill.get("alternative_skills", [])
            
            print(f"   Extracted: is_group={is_group}, alternatives={alternatives}")
            
            # Verify
            if is_group == test['expected_group']:
                if not test['expected_group']:
                    print(f"   ✅ Correctly identified as individual skill")
                    results.append(True)
                elif set(alternatives) == set(test['expected_alternatives']):
                    print(f"   ✅ Correctly identified group with all alternatives")
                    results.append(True)
                else:
                    print(f"   ⚠️  Group detected but alternatives mismatch")
                    print(f"      Expected: {test['expected_alternatives']}")
                    print(f"      Got: {alternatives}")
                    results.append(False)
            else:
                print(f"   ❌ is_group mismatch (expected {test['expected_group']}, got {is_group})")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n📊 Success Rate: {success_rate:.1f}% ({sum(results)}/{len(results)})")
    return success_rate >= 80


def test_database_query():
    """Test 3: Query existing skill groups from database"""
    print("\n" + "="*60)
    print("TEST 3: Query Existing Skill Groups")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Find skill groups
        groups = db.query(JobSkillRequirement).filter(
            JobSkillRequirement.is_group == True
        ).limit(5).all()
        
        if groups:
            print(f"✅ Found {len(groups)} skill groups in database:")
            for g in groups:
                skill_name = g.skill.name if g.skill else "Unknown"
                print(f"\n   📦 {skill_name}")
                print(f"      Strategy: {g.group_strategy}")
                print(f"      Alternatives: {g.alternative_skills}")
                print(f"      Min Required: {g.min_required}")
            return True
        else:
            print("⚠️  No skill groups found yet (this is OK if no JDs have been processed)")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        db.close()


def test_gap_analysis_logic():
    """Test 4: Test gap analysis group resolution logic"""
    print("\n" + "="*60)
    print("TEST 4: Gap Analysis Group Logic")
    print("="*60)
    
    try:
        from services.analysis_service.engine.advanced_gap_engine import AdvancedGapEngine
        
        engine = AdvancedGapEngine()
        
        # Test case: User has Blender, group requires Blender/Maya/3ds Max
        test_group = {
            "is_group": True,
            "group_strategy": "any_one",
            "alternative_skills": ["Blender", "Maya", "3ds Max"],
            "min_required": 1
        }
        
        # Simulate skill results: Blender matched, others didn't
        skill_results = [
            {"skill": "Blender", "score": 0.95},
            {"skill": "Maya", "score": 0.0},
            {"skill": "3ds Max", "score": 0.0}
        ]
        
        result = engine.resolve_group_score(test_group, skill_results)
        
        print(f"   Input: User has Blender")
        print(f"   Group: Blender/Maya/3ds Max (any_one)")
        print(f"   Result: score={result.get('score')}, match_found={result.get('match_found')}")
        
        if result.get('match_found') and result.get('score') > 0.8:
            print(f"   ✅ Group correctly satisfied (user has 1 of 3 alternatives)")
            return True
        else:
            print(f"   ❌ Group logic failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 SKILL GROUPS FUNCTIONALITY TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Migration
    results.append(("Migration", test_migration()))
    
    # Test 2: Skill Extraction
    results.append(("Skill Extraction", await test_skill_extraction()))
    
    # Test 3: Database Query
    results.append(("Database Query", test_database_query()))
    
    # Test 4: Gap Analysis Logic
    results.append(("Gap Analysis Logic", test_gap_analysis_logic()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Skill groups feature is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")


if __name__ == "__main__":
    asyncio.run(main())
