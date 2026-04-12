import json
from typing import List, Dict, Any

# Mocking the normalization logic from retriever.py
def normalize_requirements(reqs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    import re
    normalized_reqs = []
    for r in reqs:
        if r.get("type") == "group":
            sub_skills = []
            for s in r.get("skills", []):
                sub_skills.append({
                    "skill": s.get("skill"),
                    "target_level": s.get("target_level") or "Mid-level",
                    "years_required": s.get("years_required") or 2
                })
            normalized_reqs.append({
                "type": "group",
                "group_name": r.get("group_name") or "Skill Group",
                "group_strategy": r.get("group_strategy") or "exclusive",
                "skills": sub_skills,
                "is_primary": r.get("is_primary") if r.get("is_primary") is not None else True,
                "importance_weight": r.get("importance_weight") or 5
            })
        else:
            s_name = r.get("skill") or r.get("name")
            if not s_name: continue
            
            # HEURISTIC FALLBACK: Split skills with slashes into an "OR" group if LLM missed it
            if "/" in s_name and any(c.isalpha() for c in s_name):
                parts = []
                if "(" in s_name and ")" in s_name:
                    match = re.search(r'\((.*)\)', s_name)
                    if match:
                        inside = match.group(1)
                        parts = [p.strip() for p in inside.split("/") if p.strip()]
                
                if not parts:
                    parts = [p.strip() for p in s_name.split("/") if p.strip()]
                
                if len(parts) > 1:
                    sub_skills = []
                    for p in parts:
                        p_clean = re.sub(r'[()\[\]{}]', '', p).strip()
                        if not p_clean: continue
                        sub_skills.append({
                            "skill": p_clean,
                            "target_level": r.get("target_level") or "Mid-level",
                            "years_required": r.get("years_required") or 2
                        })
                    normalized_reqs.append({
                        "type": "group",
                        "group_name": f"{s_name} (Combined)",
                        "group_strategy": "exclusive",
                        "skills": sub_skills,
                        "is_primary": r.get("is_primary") if r.get("is_primary") is not None else True,
                        "importance_weight": r.get("importance_weight") or 5
                    })
                    continue

            normalized_reqs.append({
                "type": "skill",
                "skill": s_name,
                "target_level": r.get("target_level") or "Mid-level",
                "years_required": r.get("years_required") or 2,
                "is_primary": r.get("is_primary") if r.get("is_primary") is not None else True,
                "importance_weight": r.get("importance_weight") or 5
            })
    return normalized_reqs

if __name__ == "__main__":
    # Test Data based on user's problematic output
    test_data = [
        {
            "skill": "VueJS/ReactJS",
            "target_level": "Mid-level",
            "years_required": 5,
            "is_primary": True
        },
        {
            "skill": "Database (SQL/NoSQL)",
            "target_level": "Mid-level",
            "years_required": 3,
            "is_primary": False
        }
    ]

    result = normalize_requirements(test_data)
    print(json.dumps(result, indent=2))
