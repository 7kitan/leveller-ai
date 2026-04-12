
import json
import re

def filter_requirements(requirements_source):
    FILTER_KEYWORDS = ["technologies", "languages", "requirements", "tools", "stack", "category", "alternative", 
                       "development", "communication", "teamwork", "management", "problem solving"]
    valid_requirements = []
    for req in requirements_source:
        item_name = req.get("skill_name", "").lower() or req.get("skill", "").lower()
        if any(kw in item_name for kw in FILTER_KEYWORDS) and len(item_name.split()) < 4:
            continue
        valid_requirements.append(req)
    return valid_requirements

def flatten_groups(reqs):
    normalized_reqs = []
    for r in reqs:
        if r.get("type") == "group":
            g_name = (r.get("group_name") or "Skill Group").lower()
            container_keywords = ["technologies", "languages", "requirements", "tools", "stack", "category", "alternative"]
            if any(kw in g_name for kw in container_keywords):
                for s in r.get("skills", []):
                    normalized_reqs.append({"type": "skill", "skill": s.get("skill")})
                continue
        normalized_reqs.append(r)
    return normalized_reqs

if __name__ == "__main__":
    # Test Data: 1 Real Skill + 1 Generic Category with 3 sub-skills + 1 Soft Skill
    dirty_data = [
        {"type": "skill", "skill": "SQL", "is_primary": True},
        {
            "type": "group", "group_name": "Web Technologies", 
            "skills": [{"skill": "HTML"}, {"skill": "CSS"}, {"skill": "JS"}]
        },
        {"type": "skill", "skill": "Communication", "is_primary": False}
    ]
    
    print("--- [VERIFY CLEAN DENOMINATOR & FLATTENING] ---")
    print(f"Original Count: {len(dirty_data)}")
    
    # Process 1: Inplace Flattening (Retriever logic)
    flattened = flatten_groups(dirty_data)
    print(f"After Flattening: {[r.get('skill', r.get('group_name')) for r in flattened]}")
    
    # Process 2: Filtering (GapCalculator logic)
    final = filter_requirements(flattened)
    print(f"Final Count (Denominator): {len(final)}")
    print(f"Final Requirements: {[r.get('skill') for r in final]}")
    
    expected_names = ["SQL", "HTML", "CSS", "JS"]
    actual_names = [r.get("skill") for r in final]
    
    if all(name in actual_names for name in expected_names) and "Communication" not in actual_names:
        print("\n✅ SUCCESS: Generic container flattened and soft skill filtered out.")
    else:
        print("\n❌ FAILURE: Logic did not correctly clean the requirements.")
