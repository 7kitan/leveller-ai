import asyncio
import sys
import os
from unittest.mock import MagicMock

# Add backend to path to import shared modules
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock dependencies BEFORE importing SkillMatcher
mock_neo4j = MagicMock()
mock_neo4j.is_primary_tech.return_value = True
mock_neo4j.get_gap_classification.return_value = {"gap_type": "MISSING"}

mock_taxonomy = MagicMock()
mock_taxonomy.get_canonical_mapping.return_value = {}

sys.modules["shared.neo4j_client"] = MagicMock(neo4j_client=mock_neo4j)
sys.modules["shared.taxonomy_service"] = MagicMock(taxonomy_service=mock_taxonomy)

from services.analysis_service.engine.matcher import SkillMatcher
from shared.level_mapper import LevelMapper

class MockDB:
    pass

async def test_matcher():
    matcher = SkillMatcher(MockDB())
    
    # Mock user skill map
    # Candidate has:
    # - Python: Senior (4), 4 years
    # - Java: Junior (2), 1 year
    # - Docker: Mid-level (3), 2 years
    user_skill_map = {
        "python": {"level": "Senior", "years": 4},
        "java": {"level": "Junior", "years": 1},
        "docker": {"level": "Mid-level", "years": 2},
        "restapi": {"level": "Basic", "years": 0.5}
    }
    user_skills_list = ["Python", "Java", "Docker", "REST API"]

    print("\n=== Scenario 1: No years required (General knowledge) ===")
    req1 = {"skill": "REST API", "target_level": "Mid-level", "years_required": 0}
    res1 = await matcher.match_skill(req1, user_skill_map, user_skills_list)
    print(f"Skill: {req1['skill']}, Req Years: {req1['years_required']}")
    print(f"Result Score: {res1['score']}, Match Found: {res1['match_found']}, Gap Type: {res1['gap_type']}")
    # Expectation: Score 1.0, MET because years_required is 0
    
    print("\n=== Scenario 2: Years required (Exact match, met) ===")
    # Req: Python 3 years Mid-level. User: 4 years Senior
    req2 = {"skill": "Python", "target_level": "Mid-level", "years_required": 3}
    res2 = await matcher.match_skill(req2, user_skill_map, user_skills_list)
    print(f"Skill: {req2['skill']}, Req Years: {req2['years_required']}, Req Level: {req2['target_level']}")
    print(f"User: {user_skill_map['python']}")
    print(f"Result Score: {round(res2['score'], 3)}, Gap Type: {res2['gap_type']}")
    # Expectation: Score 1.0 (Level 4>=3 -> 1.0, Years 4>=3 -> 1.0)

    print("\n=== Scenario 3: Partial Match (Years required, low level & years) ===")
    # Req: Java 3 years Senior. User: 1 year Junior
    # Level: 2/4 = 0.5. Years: 1/3 = 0.333. Final: (0.5+0.333)/2 = 0.416
    req3 = {"skill": "Java", "target_level": "Senior", "years_required": 3}
    res3 = await matcher.match_skill(req3, user_skill_map, user_skills_list)
    print(f"Skill: {req3['skill']}, Req Years: {req3['years_required']}, Req Level: {req3['target_level']}")
    print(f"User: {user_skill_map['java']}")
    print(f"Result Score: {round(res3['score'], 3)}, Gap Type: {res3['gap_type']}")

    print("\n=== Scenario 4: Skill match with low level but NO years required ===")
    # Req: Docker 0 years Expert. User: 2 years Mid-level
    req4 = {"skill": "Docker", "target_level": "Expert", "years_required": 0}
    res4 = await matcher.match_skill(req4, user_skill_map, user_skills_list)
    print(f"Skill: {req4['skill']}, Req Years: {req4['years_required']}, Req Level: {req4['target_level']}")
    print(f"User: {user_skill_map['docker']}")
    print(f"Result Score: {round(res4['score'], 3)}, Gap Type: {res4['gap_type']}")
    # Expectation: Score 1.0 (Match found, ignore level)

if __name__ == "__main__":
    asyncio.run(test_matcher())

if __name__ == "__main__":
    asyncio.run(test_matcher())
