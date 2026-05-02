"""
Test script to verify soft skill extraction and 5-dimension radar chart.

This script tests:
1. JD extraction with both technical and soft skills
2. Skill categorization (technical vs soft)
3. 5-dimension radar chart (Technical Skills, Soft Skills, Tools & Frameworks, Domain Knowledge, Certifications)
4. Separate scoring for each dimension
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.llm_utils import extract_skills_from_requirements
from shared.radar_dimensions import calculate_radar_scores, SOFT_SKILL_CATEGORIES
from services.analysis_service.engine.retriever import JDRequirementRetriever
import asyncio


# Sample JD with both technical and soft skills
SAMPLE_JD = """
Senior Backend Developer

Requirements:
- 5+ years experience with Python and Django
- Strong knowledge of PostgreSQL and Redis
- Experience with Docker and Kubernetes
- Proficiency in REST API design
- AWS cloud platform experience
- Git version control

Soft Skills:
- Excellent communication skills in English
- Strong leadership and mentoring abilities
- Team collaboration and cross-functional teamwork
- Problem-solving and analytical thinking
- Time management and ability to meet deadlines
- Adaptability and learning agility
"""


def test_skill_extraction():
    """Test skill extraction from requirements text."""
    print("=" * 70)
    print("TEST 1: Skill Extraction from Requirements")
    print("=" * 70)
    
    result = extract_skills_from_requirements(SAMPLE_JD, model_key="ai_model")
    
    if not result:
        print("❌ FAILED: No skills extracted")
        return False
    
    print(f"\n✓ Job Classification:")
    print(f"  - Is Tech Job: {result['is_tech_job']}")
    print(f"  - Confidence: {result['confidence']}")
    print(f"  - Domain: {result['primary_domain']}")
    print(f"  - Reason: {result['classification_reason']}")
    
    skills = result.get('skills', [])
    print(f"\n✓ Total Skills Extracted: {len(skills)}")
    
    # Separate technical and soft skills
    technical_skills = [s for s in skills if s.get('skill_type') == 'technical']
    soft_skills = [s for s in skills if s.get('skill_type') == 'soft']
    
    print(f"\n✓ Technical Skills ({len(technical_skills)}):")
    for skill in technical_skills[:10]:  # Show first 10
        print(f"  - {skill['skill_name']} ({skill['category']}) | "
              f"Level: {skill.get('required_level', 'N/A')} | "
              f"Weight: {skill['importance_weight']}")
    
    print(f"\n✓ Soft Skills ({len(soft_skills)}):")
    for skill in soft_skills:
        print(f"  - {skill['skill_name']} ({skill['category']}) | "
              f"Weight: {skill['importance_weight']}")
    
    if len(soft_skills) == 0:
        print("⚠️  WARNING: No soft skills extracted!")
        return False
    
    return True


async def test_jd_retriever():
    """Test JD retriever extraction."""
    print("\n" + "=" * 70)
    print("TEST 2: JD Retriever Extraction")
    print("=" * 70)
    
    retriever = JDRequirementRetriever()
    requirements = await retriever._ai_extract(SAMPLE_JD)
    
    if not requirements:
        print("❌ FAILED: No requirements extracted")
        return False
    
    print(f"\n✓ Total Requirements: {len(requirements)}")
    
    # Separate by skill_type
    technical_reqs = []
    soft_reqs = []
    
    for req in requirements:
        skill_type = req.get('skill_type', 'technical')
        if req.get('type') == 'skill':
            if skill_type == 'soft':
                soft_reqs.append(req)
            else:
                technical_reqs.append(req)
        elif req.get('type') == 'group':
            # Check skills in group
            for s in req.get('skills', []):
                if s.get('skill_type') == 'soft':
                    soft_reqs.append(s)
                else:
                    technical_reqs.append(s)
    
    print(f"\n✓ Technical Requirements ({len(technical_reqs)}):")
    for req in technical_reqs[:10]:
        skill_name = req.get('skill', 'N/A')
        level = req.get('target_level', 'N/A')
        years = req.get('years_required', 0)
        print(f"  - {skill_name} | Level: {level} | Years: {years}")
    
    print(f"\n✓ Soft Skill Requirements ({len(soft_reqs)}):")
    for req in soft_reqs:
        skill_name = req.get('skill', 'N/A')
        print(f"  - {skill_name}")
    
    if len(soft_reqs) == 0:
        print("⚠️  WARNING: No soft skills extracted from JD!")
        return False
    
    return True


def test_radar_scoring():
    """Test radar chart scoring (5 dimensions matching frontend)."""
    print("\n" + "=" * 70)
    print("TEST 3: Radar Chart Scoring (5 Dimensions)")
    print("=" * 70)
    
    # Sample CV skills (mixed technical, soft, tools, domain)
    cv_skills = [
        {"skill_name": "Python", "category": "Programming Language"},
        {"skill_name": "Django", "category": "Backend Framework"},
        {"skill_name": "PostgreSQL", "category": "Database"},
        {"skill_name": "Docker", "category": "DevOps & CI/CD"},
        {"skill_name": "Git", "category": "Version Control"},
        {"skill_name": "Microservices", "category": "Architecture"},
        {"skill_name": "Communication", "category": "Communication"},
        {"skill_name": "Leadership", "category": "Leadership"},
    ]
    
    # Sample JD skills (mixed technical, soft, tools, domain)
    jd_skills = [
        {"skill_name": "Python", "category": "Programming Language"},
        {"skill_name": "Django", "category": "Backend Framework"},
        {"skill_name": "PostgreSQL", "category": "Database"},
        {"skill_name": "Redis", "category": "Caching & Queue"},
        {"skill_name": "Docker", "category": "DevOps & CI/CD"},
        {"skill_name": "Kubernetes", "category": "DevOps & CI/CD"},
        {"skill_name": "Git", "category": "Version Control"},
        {"skill_name": "Jenkins", "category": "Build Tool"},
        {"skill_name": "Microservices", "category": "Architecture"},
        {"skill_name": "REST API", "category": "API Technology"},
        {"skill_name": "Communication", "category": "Communication"},
        {"skill_name": "Leadership", "category": "Leadership"},
        {"skill_name": "Teamwork", "category": "Teamwork"},
    ]
    
    # Calculate radar scores (should include all 5 dimensions)
    radar_data = calculate_radar_scores(cv_skills, jd_skills)
    
    print(f"\n✓ Overall Match (5 dimensions): {radar_data['overall_match']}%")
    print(f"\n✓ Dimension Scores:")
    
    expected_dimensions = ["Technical Skills", "Soft Skills", "Tools & Frameworks", "Domain Knowledge", "Certifications"]
    
    for i, dimension in enumerate(radar_data['dimensions']):
        match_pct = radar_data['match_percentages'][i]
        details = radar_data['dimension_details'][dimension]
        print(f"  {details['icon']} {dimension}: {match_pct}%")
        print(f"     CV: {len(details['cv_skills'])} | JD: {len(details['jd_skills'])} | "
              f"Matched: {len(details['matched'])} | Missing: {len(details['missing'])}")
    
    # Verify we have 5 dimensions
    if len(radar_data['dimensions']) != 5:
        print(f"\n⚠️  WARNING: Expected 5 dimensions, got {len(radar_data['dimensions'])}")
        return False
    
    # Verify dimension names match frontend expectations
    for expected_dim in expected_dimensions:
        if expected_dim not in radar_data['dimensions']:
            print(f"\n⚠️  WARNING: Expected dimension '{expected_dim}' not found")
            # Don't fail if Certifications is missing (no cert data in test)
            if expected_dim != "Certifications":
                return False
    
    # Verify soft skills are included as one of the 5 dimensions
    if "Soft Skills" not in radar_data['dimensions']:
        print(f"\n⚠️  WARNING: 'Soft Skills' dimension not found in radar chart")
        return False
    
    print(f"\n✓ All expected dimensions present")
    
    return True


def test_soft_skill_scoring():
    """Test soft skill scoring as one of 5 dimensions in radar chart."""
    print("\n" + "=" * 70)
    print("TEST 4: Soft Skills Scoring (One of 5 Dimensions)")
    print("=" * 70)
    
    # Sample CV skills
    cv_skills = [
        {"skill_name": "Communication", "category": "Communication"},
        {"skill_name": "Leadership", "category": "Leadership"},
    ]
    
    # Sample JD skills
    jd_skills = [
        {"skill_name": "Communication", "category": "Communication"},
        {"skill_name": "Leadership", "category": "Leadership"},
        {"skill_name": "Teamwork", "category": "Teamwork"},
    ]
    
    # Calculate radar scores
    radar_data = calculate_radar_scores(cv_skills, jd_skills)
    
    # Check if Soft Skills dimension exists
    if "Soft Skills" not in radar_data['dimension_details']:
        print(f"\n❌ FAILED: 'Soft Skills' dimension not found in radar chart")
        return False
    
    soft_details = radar_data['dimension_details']['Soft Skills']
    match_pct = soft_details['match_percentage']
    
    print(f"\n✓ Soft Skills Match (from radar chart): {match_pct}%")
    print(f"  - CV Soft Skills: {soft_details['cv_skills']}")
    print(f"  - JD Soft Skills: {soft_details['jd_skills']}")
    print(f"  - Matched: {soft_details['matched']}")
    print(f"  - Missing: {soft_details['missing']}")
    
    expected_match = 66.7  # 2 out of 3
    if abs(match_pct - expected_match) > 0.5:
        print(f"⚠️  WARNING: Expected ~{expected_match}%, got {match_pct}%")
        return False
    
    return True


def test_soft_skill_categories():
    """Test soft skill category definitions."""
    print("\n" + "=" * 70)
    print("TEST 5: Soft Skill Category Definitions")
    print("=" * 70)
    
    print(f"\n✓ Defined Soft Skill Categories ({len(SOFT_SKILL_CATEGORIES)}):")
    for category in sorted(SOFT_SKILL_CATEGORIES):
        print(f"  - {category}")
    
    expected_categories = {
        "Communication", "Leadership", "Teamwork",
        "Problem Solving", "Time Management", "Adaptability"
    }
    
    if SOFT_SKILL_CATEGORIES != expected_categories:
        print(f"\n⚠️  WARNING: Category mismatch!")
        print(f"  Expected: {expected_categories}")
        print(f"  Got: {SOFT_SKILL_CATEGORIES}")
        return False
    
    # Test radar dimensions
    from shared.radar_dimensions import RADAR_DIMENSIONS
    
    print(f"\n✓ Radar Dimensions ({len(RADAR_DIMENSIONS)}):")
    expected_radar_dims = ["Technical Skills", "Soft Skills", "Tools & Frameworks", "Domain Knowledge", "Certifications"]
    
    for dim_name in expected_radar_dims:
        if dim_name in RADAR_DIMENSIONS:
            config = RADAR_DIMENSIONS[dim_name]
            print(f"  {config['icon']} {dim_name}: {len(config['categories'])} categories")
        else:
            print(f"  ❌ {dim_name}: NOT FOUND")
            return False
    
    if len(RADAR_DIMENSIONS) != 5:
        print(f"\n⚠️  WARNING: Expected 5 radar dimensions, got {len(RADAR_DIMENSIONS)}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("SOFT SKILL EXTRACTION & SCORING TEST SUITE")
    print("=" * 70)
    
    results = []
    
    # Test 1: Skill extraction
    try:
        results.append(("Skill Extraction", test_skill_extraction()))
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        results.append(("Skill Extraction", False))
    
    # Test 2: JD retriever
    try:
        results.append(("JD Retriever", asyncio.run(test_jd_retriever())))
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        results.append(("JD Retriever", False))
    
    # Test 3: Radar scoring
    try:
        results.append(("Radar Scoring", test_radar_scoring()))
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        results.append(("Radar Scoring", False))
    
    # Test 4: Soft skill scoring
    try:
        results.append(("Soft Skill Scoring", test_soft_skill_scoring()))
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        results.append(("Soft Skill Scoring", False))
    
    # Test 5: Category definitions
    try:
        results.append(("Category Definitions", test_soft_skill_categories()))
    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        results.append(("Category Definitions", False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
