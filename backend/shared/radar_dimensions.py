"""
Radar Chart Dimension Mapping for Gap Analysis

Maps detailed skill categories into 5 core dimensions matching frontend expectations:
1. Technical Skills - Programming languages, core technologies
2. Soft Skills - Communication, leadership, teamwork
3. Tools & Frameworks - Frameworks, development tools, methodologies
4. Domain Knowledge - Business domain, industry-specific knowledge
5. Certifications - Certificates, qualifications, credentials
"""

from typing import Dict, List, Set
from collections import defaultdict

# ─── Soft Skill Categories ───────────────────────────────────────────────────

SOFT_SKILL_CATEGORIES = {
    "Communication",
    "Leadership", 
    "Teamwork",
    "Problem Solving",
    "Time Management",
    "Adaptability"
}

# ─── Radar Dimension Mapping (5 Dimensions matching frontend) ────────────────

RADAR_DIMENSIONS = {
    "Technical Skills": {
        "categories": [
            "Programming Language",
            "Scripting Language",
            "Web Technology",
            "Database",
            "Database Technology",
            "Database Language",
            "Query Language",
            "Caching & Queue",
            "Cache",
            "Cloud Platform",
            "Cloud Service",
            "Cloud Technology",
            "DevOps & CI/CD",
            "Containerization",
            "DevOps",
            "DevOps Tool",
            "Security",
            "Security Tool",
            "Security Technology",
            "Machine Learning",
            "Data Science",
            "Big Data Technology",
            "AI Tool",
            "Model",
            "NLP Task",
            "LLM Task",
        ],
        "description": "Core programming languages, databases, cloud platforms, and technical skills",
        "icon": "💻",
        "priority": 1
    },
    
    "Soft Skills": {
        "categories": [
            "Communication",
            "Leadership",
            "Teamwork",
            "Problem Solving",
            "Time Management",
            "Adaptability"
        ],
        "description": "Communication, leadership, teamwork, and interpersonal skills",
        "icon": "🤝",
        "priority": 2
    },
    
    "Tools & Frameworks": {
        "categories": [
            "Framework",
            "Library",
            "Frontend Framework",
            "Backend Framework",
            "Mobile Framework",
            "JavaScript Library",
            "Testing Framework",
            "Build Tool",
            "Development Tool",
            "Tool",
            "Version Control",
            "Methodology",
            "Collaboration Tool",
            "Design Tool",
            "Project Management Tool",
            "Reporting Tool",
            "Operating System",
            "Web Server",
            "Load Balancer Tool",
            "Networking Tool",
            "Firewall Tool",
            "Endpoint Protection Tool",
            "SIEM Tool",
        ],
        "description": "Frameworks, development tools, methodologies, and practices",
        "icon": "🛠️",
        "priority": 3
    },
    
    "Domain Knowledge": {
        "categories": [
            "Technical Knowledge",
            "Architecture",
            "System",
            "API Technology",
            "Concept",
            "Programming Concept",
            "Design",
            "Performance Optimization",
            "Accessibility",
            "State Management",
            "Analytical Technique",
            "LMS Concept",
            "Networking Concept",
            "Networking",
            "Standard",
            "Development",
            "Style Sheet Language",
            "Markup Language",
        ],
        "description": "Domain-specific knowledge, architecture, system design, and concepts",
        "icon": "📚",
        "priority": 4
    },
    
    "Certifications": {
        "categories": [
            "Certification",
            "Certificate",
            "Credential",
            "Qualification",
            "License",
        ],
        "description": "Professional certifications, credentials, and qualifications",
        "icon": "🎓",
        "priority": 5
    }
}


def get_radar_dimension(category: str) -> str:
    """
    Map a detailed skill category to its radar dimension.
    
    Args:
        category: Detailed category name (e.g., "Programming Language", "Communication")
    
    Returns:
        Radar dimension name (e.g., "Core Programming", "Soft Skills")
        Returns "Other" if category not found in mapping
    """
    for dimension, config in RADAR_DIMENSIONS.items():
        if category in config["categories"]:
            return dimension
    return "Other"


def calculate_radar_scores(
    cv_skills: List[Dict],
    jd_skills: List[Dict]
) -> Dict:
    """
    Calculate radar chart scores for CV vs JD comparison (5 DIMENSIONS matching frontend).
    
    Dimensions:
    1. Technical Skills - Programming languages, databases, cloud, security
    2. Soft Skills - Communication, leadership, teamwork
    3. Tools & Frameworks - Frameworks, dev tools, methodologies
    4. Domain Knowledge - Architecture, system design, concepts
    5. Certifications - Professional certifications and credentials
    
    Args:
        cv_skills: List of skills from CV
            [{"skill_name": "Python", "category": "Programming Language", ...}, ...]
        jd_skills: List of skills from JD
            [{"skill_name": "Python", "category": "Programming Language", ...}, ...]
    
    Returns:
        {
            "dimensions": ["Technical Skills", "Soft Skills", "Tools & Frameworks", "Domain Knowledge", "Certifications"],
            "cv_scores": [85, 70, 95, 80, 50],
            "jd_scores": [100, 100, 100, 100, 100],
            "match_percentages": [85, 70, 95, 80, 50],
            "overall_match": 76,
            "dimension_details": {
                "Technical Skills": {
                    "cv_skills": ["python", "postgresql"],
                    "jd_skills": ["python", "postgresql", "redis"],
                    "matched": ["python", "postgresql"],
                    "missing": ["redis"],
                    "extra": [],
                    "match_rate": 0.67,
                    "priority": 1,
                    "icon": "💻"
                },
                ...
            }
        }
    """
    # Group skills by radar dimension
    cv_by_dimension = defaultdict(set)
    jd_by_dimension = defaultdict(set)
    
    for skill in cv_skills:
        dimension = get_radar_dimension(skill.get('category', ''))
        # Skip only "Other" category
        if dimension and dimension != "Other":
            cv_by_dimension[dimension].add(skill['skill_name'].lower())
    
    for skill in jd_skills:
        dimension = get_radar_dimension(skill.get('category', ''))
        # Skip only "Other" category
        if dimension and dimension != "Other":
            jd_by_dimension[dimension].add(skill['skill_name'].lower())
    
    # Calculate scores for each dimension
    dimensions = []
    cv_scores = []
    match_percentages = []
    dimension_details = {}
    
    for dimension, config in sorted(
        RADAR_DIMENSIONS.items(),
        key=lambda x: x[1]["priority"]
    ):
        cv_set = cv_by_dimension[dimension]
        jd_set = jd_by_dimension[dimension]
        
        if len(jd_set) == 0:
            # No requirements in this dimension
            match_rate = 1.0
            match_pct = 100
        else:
            # Calculate match percentage
            matched = cv_set & jd_set
            match_rate = len(matched) / len(jd_set)
            match_pct = round(match_rate * 100, 1)
        
        dimensions.append(dimension)
        cv_scores.append(match_pct)
        match_percentages.append(match_pct)
        
        # Detailed breakdown
        matched_skills = sorted(cv_set & jd_set)
        missing_skills = sorted(jd_set - cv_set)
        extra_skills = sorted(cv_set - jd_set)
        
        dimension_details[dimension] = {
            "cv_skills": sorted(cv_set),
            "jd_skills": sorted(jd_set),
            "matched": matched_skills,
            "missing": missing_skills,
            "extra": extra_skills,
            "match_rate": round(match_rate, 2),
            "match_percentage": match_pct,
            "priority": config["priority"],
            "icon": config["icon"],
            "description": config["description"],
            "skill_count": {
                "cv": len(cv_set),
                "jd": len(jd_set),
                "matched": len(matched_skills),
                "missing": len(missing_skills)
            }
        }
    
    # Calculate overall match
    total_jd_skills = sum(len(jd_by_dimension[d]) for d in dimensions)
    total_matched = sum(
        len(cv_by_dimension[d] & jd_by_dimension[d])
        for d in dimensions
    )
    overall_match = round(
        (total_matched / total_jd_skills * 100) if total_jd_skills > 0 else 100,
        1
    )
    
    return {
        "dimensions": dimensions,
        "cv_scores": cv_scores,
        "jd_scores": [100] * len(dimensions),  # JD is always 100% (baseline)
        "match_percentages": match_percentages,
        "overall_match": overall_match,
        "dimension_details": dimension_details,
        "summary": {
            "total_jd_skills": total_jd_skills,
            "total_matched": total_matched,
            "total_missing": total_jd_skills - total_matched,
            "dimensions_count": len(dimensions)
        }
    }


def get_priority_gaps(radar_data: Dict, threshold: float = 70.0) -> List[Dict]:
    """
    Get priority gaps (dimensions with match < threshold).
    
    Args:
        radar_data: Output from calculate_radar_scores()
        threshold: Match percentage threshold (default: 70%)
    
    Returns:
        List of dimensions with gaps, sorted by priority
        [
            {
                "dimension": "Specialized Technical Skills",
                "match_percentage": 50,
                "gap": 50,
                "missing_skills": ["Microservices", "API Gateway"],
                "priority": 5,
                "severity": "high"
            },
            ...
        ]
    """
    gaps = []
    
    for dimension, details in radar_data["dimension_details"].items():
        match_pct = details["match_percentage"]
        
        if match_pct < threshold:
            gap = 100 - match_pct
            
            # Determine severity
            if match_pct < 50:
                severity = "high"
            elif match_pct < 70:
                severity = "medium"
            else:
                severity = "low"
            
            gaps.append({
                "dimension": dimension,
                "match_percentage": match_pct,
                "gap": gap,
                "missing_skills": details["missing"],
                "missing_count": len(details["missing"]),
                "priority": details["priority"],
                "severity": severity,
                "icon": details["icon"]
            })
    
    # Sort by severity (high first), then by gap size
    severity_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda x: (severity_order[x["severity"]], -x["gap"]))
    
    return gaps


def format_radar_summary(radar_data: Dict) -> str:
    """
    Format radar chart data into human-readable summary.
    
    Args:
        radar_data: Output from calculate_radar_scores()
    
    Returns:
        Formatted text summary
    """
    lines = []
    lines.append(f"Overall Match: {radar_data['overall_match']}%")
    lines.append("")
    
    for dimension in radar_data["dimensions"]:
        details = radar_data["dimension_details"][dimension]
        match_pct = details["match_percentage"]
        icon = details["icon"]
        
        # Status indicator
        if match_pct >= 80:
            status = "🟢 STRONG"
        elif match_pct >= 60:
            status = "🟡 MODERATE"
        else:
            status = "🔴 NEEDS WORK"
        
        lines.append(f"{status} {icon} {dimension}: {match_pct}%")
        
        if details["missing"]:
            lines.append(f"  Missing: {', '.join(details['missing'][:3])}")
            if len(details["missing"]) > 3:
                lines.append(f"  ... and {len(details['missing']) - 3} more")
        
        lines.append("")
    
    return "\n".join(lines)


# ─── Example Usage ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Example CV skills
    cv_skills = [
        {"skill_name": "Python", "category": "Programming Language"},
        {"skill_name": "JavaScript", "category": "Programming Language"},
        {"skill_name": "React", "category": "Frontend Framework"},
        {"skill_name": "PostgreSQL", "category": "Database"},
        {"skill_name": "Redis", "category": "Cache"},
        {"skill_name": "Docker", "category": "Containerization"},
        {"skill_name": "Git", "category": "Version Control"},
    ]
    
    # Example JD skills
    jd_skills = [
        {"skill_name": "Python", "category": "Programming Language"},
        {"skill_name": "JavaScript", "category": "Programming Language"},
        {"skill_name": "TypeScript", "category": "Programming Language"},
        {"skill_name": "React", "category": "Frontend Framework"},
        {"skill_name": "PostgreSQL", "category": "Database"},
        {"skill_name": "MongoDB", "category": "Database"},
        {"skill_name": "Docker", "category": "Containerization"},
        {"skill_name": "Kubernetes", "category": "Containerization"},
        {"skill_name": "Git", "category": "Version Control"},
        {"skill_name": "Microservices", "category": "Architecture"},
        {"skill_name": "API Gateway", "category": "API Technology"},
    ]
    
    # Calculate radar scores
    radar_data = calculate_radar_scores(cv_skills, jd_skills)
    
    print("=== Radar Chart Data ===")
    print(f"Overall Match: {radar_data['overall_match']}%")
    print()
    
    for i, dimension in enumerate(radar_data["dimensions"]):
        print(f"{dimension}: {radar_data['match_percentages'][i]}%")
    
    print()
    print("=== Priority Gaps ===")
    gaps = get_priority_gaps(radar_data)
    for gap in gaps:
        print(f"{gap['severity'].upper()}: {gap['dimension']} ({gap['match_percentage']}%)")
        print(f"  Missing: {', '.join(gap['missing_skills'][:3])}")
    
    print()
    print("=== Summary ===")
    print(format_radar_summary(radar_data))
