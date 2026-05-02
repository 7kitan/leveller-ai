"""
Result Normalizer - Normalize analysis result_json to consistent format.

Handles backward compatibility with old data format:
- Old format: overall_match_pct (radar-based), llm_overall_match_pct (LLM)
- New format: overall_match_pct (LLM), radar_match_pct (radar-based)
"""

from typing import Dict, Any
import logging

logger = logging.getLogger("result_normalizer")


def normalize_analysis_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize analysis result to new consistent format.
    
    Transformations:
    1. If llm_overall_match_pct exists and overall_match_pct is 0 or missing:
       - Use llm_overall_match_pct as overall_match_pct
    2. Remove llm_overall_match_pct from response (deprecated)
    3. Ensure all required fields exist with defaults
    
    Args:
        result: Raw result_json from database
        
    Returns:
        Normalized result dict
    """
    if not isinstance(result, dict):
        return result
    
    # Make a copy to avoid mutating original
    normalized = result.copy()
    
    # ── Backward compatibility: Handle old format ────────────────────────────
    llm_match = normalized.get("llm_overall_match_pct")
    overall_match = normalized.get("overall_match_pct", 0)
    
    # If we have llm_overall_match_pct but overall_match_pct is 0 or missing,
    # use llm_overall_match_pct as the primary overall_match_pct
    if llm_match is not None and (overall_match == 0 or overall_match is None):
        normalized["overall_match_pct"] = float(llm_match)
        logger.info(
            f"Normalized old format: llm_overall_match_pct={llm_match} "
            f"-> overall_match_pct={llm_match}"
        )
    
    # Remove deprecated field
    if "llm_overall_match_pct" in normalized:
        del normalized["llm_overall_match_pct"]
    
    # ── Ensure required fields exist ──────────────────────────────────────────
    defaults = {
        "overall_match_pct": 0.0,
        "potential_match_pct": 0.0,
        "radar_match_pct": None,
        "soft_skills_match_pct": None,
        "overall_assessment": "",
        "strengths": [],
        "weaknesses": [],
        "skill_gaps": [],
        "gap_summary": {},
        "match_breakdown": {},
        "transferable_insights": [],
        "course_recommendations": [],
        "career_roadmap": {},
        "market_sentiment": None,
    }
    
    for key, default_value in defaults.items():
        if key not in normalized:
            normalized[key] = default_value
    
    return normalized
