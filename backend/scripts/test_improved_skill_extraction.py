"""
Test script for improved skill extraction with validation.
Tests the new prompt and validation logic.
"""
import sys
sys.path.insert(0, '/app')

from shared.llm_utils import extract_skills_from_requirements, validate_and_clean_skill
import json

# Test cases with various scenarios
TEST_CASES = [
    {
        "name": "Clean Technical Job (English)",
        "requirements": """
        We are looking for a Senior Backend Developer with the following skills:
        
        Required:
        - Python (5+ years experience)
        - Django or Flask framework
        - PostgreSQL database
        - Docker and Kubernetes
        - AWS cloud services
        - RESTful API design
        
        Nice to have:
        - React for frontend
        - Redis caching
        - CI/CD with Jenkins
        - Agile/Scrum methodology
        """
    },
    {
        "name": "Mixed Vietnamese/English (Should filter Vietnamese)",
        "requirements": """
        Yêu cầu công việc:
        - Có kinh nghiệm 3 năm với Python
        - Thành thạo Django framework
        - Biết sử dụng PostgreSQL
        - Am hiểu về Docker và Kubernetes
        - Good communication skills
        - Team work ability
        """
    },
    {
        "name": "Problematic Requirements (Generic phrases)",
        "requirements": """
        Requirements:
        - 5+ years of experience in software development
        - Strong knowledge of programming languages
        - Excellent problem-solving skills
        - Ability to work in a team
        - Bachelor's degree in Computer Science
        - Good understanding of databases
        - Experience with cloud platforms
        """
    },
    {
        "name": "Specific Technical Stack",
        "requirements": """
        Tech Stack:
        - Frontend: React, TypeScript, Next.js
        - Backend: Node.js, Express, NestJS
        - Database: MongoDB, Redis
        - Cloud: AWS (EC2, S3, Lambda)
        - DevOps: Docker, GitHub Actions
        - Testing: Jest, Cypress
        """
    },
    {
        "name": "Mobile & ML Stack (Testing new categories)",
        "requirements": """
        We need a Mobile Developer with ML experience:
        
        Required:
        - Flutter or React Native for mobile development
        - iOS (Swift) and Android (Kotlin) knowledge
        - REST API and GraphQL integration
        - TensorFlow or PyTorch for ML models
        - Pandas and NumPy for data processing
        - JWT and OAuth for authentication
        - Kafka for event streaming
        - Jest and Cypress for testing
        """
    }
]

def test_validation_function():
    """Test the validation function directly with edge cases."""
    print("=" * 80)
    print("TESTING VALIDATION FUNCTION")
    print("=" * 80)
    
    test_skills = [
        {"skill_name": "Python", "category": "Programming Language", "importance_weight": 10},
        {"skill_name": "Có kinh nghiệm Python", "category": "Programming Language", "importance_weight": 8},  # Vietnamese
        {"skill_name": "5+ years of experience", "category": "Other", "importance_weight": 5},  # Invalid pattern
        {"skill_name": "Knowledge of Java", "category": "Programming Language", "importance_weight": 7},  # Invalid pattern
        {"skill_name": "A" * 60, "category": "Tool", "importance_weight": 5},  # Too long
        {"skill_name": "JS", "category": "Programming Language", "importance_weight": 8},  # Valid short name
        {"skill_name": "", "category": "Framework", "importance_weight": 5},  # Empty
        {"skill_name": "Bachelor's degree", "category": "Education", "importance_weight": 3},  # Education requirement
    ]
    
    for skill in test_skills:
        result = validate_and_clean_skill(skill)
        status = "✓ PASS" if result else "✗ REJECT"
        print(f"{status:10} | {skill['skill_name'][:50]:50}")
    
    print()

def test_extraction():
    """Test extraction on various job requirements."""
    print("=" * 80)
    print("TESTING SKILL EXTRACTION WITH IMPROVED PROMPT")
    print("=" * 80)
    print()
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST CASE {i}: {test_case['name']}")
        print(f"{'=' * 80}")
        print(f"\nRequirements Text:")
        print(test_case['requirements'][:200] + "..." if len(test_case['requirements']) > 200 else test_case['requirements'])
        print()
        
        # Extract skills
        try:
            skills = extract_skills_from_requirements(test_case['requirements'])
            
            if skills:
                print(f"✓ Extracted {len(skills)} skills:\n")
                
                # Group by category
                by_category = {}
                for skill in skills:
                    cat = skill.get('category', 'Unknown')
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append(skill)
                
                # Display grouped results
                for category, cat_skills in sorted(by_category.items()):
                    print(f"  {category}:")
                    for skill in cat_skills:
                        mandatory = "REQUIRED" if skill.get('is_mandatory') else "OPTIONAL"
                        level = skill.get('required_level') or "Any"
                        years = skill.get('min_years_exp', 0)
                        weight = skill.get('importance_weight', 5)
                        
                        print(f"    - {skill['skill_name']:25} | {mandatory:8} | Level: {level:6} | Years: {years:2} | Weight: {weight:2}")
                    print()
                
                # Show JSON for first test case
                if i == 1:
                    print("\nJSON Output (first 3 skills):")
                    print(json.dumps(skills[:3], indent=2, ensure_ascii=False))
            else:
                print("✗ No skills extracted (or all rejected by validation)")
        
        except Exception as e:
            print(f"✗ ERROR: {e}")
        
        print()

def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("IMPROVED SKILL EXTRACTION TEST SUITE")
    print("=" * 80)
    print()
    
    # Test 1: Validation function
    test_validation_function()
    
    # Test 2: Full extraction pipeline
    print("\n" + "=" * 80)
    print("NOTE: The following tests require LLM API access.")
    print("If you see errors, make sure your .env is configured correctly.")
    print("=" * 80)
    input("\nPress Enter to continue with LLM tests (or Ctrl+C to skip)...")
    
    test_extraction()
    
    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
