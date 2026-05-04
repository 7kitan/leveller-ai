"""
gap_v3 states: TypedDict definitions cho toàn bộ v3 pipeline.
"""

from typing import TypedDict, List, Dict, Any, Optional


# ─── CV Parsing States (Pipeline 1) ────────────────────────────────────


class CVParsedData(TypedDict, total=False):
    """Structured CV data — parse 1 lần, lưu vào DB, dùng nhiều lần."""

    full_name: str
    summary: str
    seniority: str  # Junior / Mid-level / Senior / Expert
    experience_years_total: float

    skills: List[Dict]  # [{name, level, years_exp, last_used, context}]
    work_history: List[
        Dict
    ]  # [{position, company, duration_years, description}]
    education: List[Dict]  # [{degree, institution, year, field}]
    certifications: List[Dict]  # [{name, issuer, year}]

    # Metadata
    is_ocr: bool
    ocr_confidence: float
    raw_text_masked: str  # Đã mask PII


class CVParsingState(TypedDict):
    """State cho CV Parsing pipeline."""

    cv_id: str
    user_id: str
    db: Any

    raw_text: Optional[str]
    is_ocr: bool
    cv_parsed: Optional[CVParsedData]
    status: str
    error: Optional[str]
    file_path: Optional[str]


# ─── Gap Analysis States (Pipeline 2) ──────────────────────────────────


class SkillGap(TypedDict, total=False):
    skill: str
    severity: str  # HIGH | MEDIUM | LOW
    is_critical: bool
    status: str  # GAP | PARTIAL
    current_level: Optional[str]
    required_level: str
    years_gap: float
    bridge_from: Optional[str]
    learning_effort: str  # EASY | MEDIUM | HARD | EXPERT
    estimated_months: float
    learning_path: str


class GapSummary(TypedDict, total=False):
    total_gaps: int
    critical_gaps: int
    soft_gaps: int
    estimated_total_months: float
    blocking_skills: List[str]


class GapAnalysisResult(TypedDict, total=False):
    """Output của Gap Analysis Agent — optimized v3 (gap + prioritize merged)."""

    overall_match_pct: float
    overall_assessment: str
    strengths: List[str]
    weaknesses: List[str]
    skill_gaps: List[SkillGap]  # Sorted by priority (severity, is_critical, estimated_months)
    gap_summary: GapSummary
    transferable_insights: List[str]
    jd_context: str


class CourseRecommendation(TypedDict, total=False):
    """Output của Course Recommendation Agent."""

    course_id: str
    title: str
    platform: str
    url: str
    level: str
    provider: str
    duration_hours: float
    is_certification: bool
    cost_usd: float
    tags: List[str]
    similarity: float
    rank_score: float
    gap_skill: str
    gap_severity: str
    gap_learning_path: str
    gap_estimated_months: float
    is_critical: bool
    selection_reason: str


class CareerRoadmap(TypedDict, total=False):
    """Output của Roadmap Synthesis Agent."""

    stages: List[
        Dict
    ]  # [{stage, focus, duration_weeks, skills_acquired, courses_taken, milestones}]
    total_weeks: int
    total_hours: float
    summary: str


class GapAnalysisStateV3(TypedDict):
    """Main state cho toàn bộ Gap Analysis v3 pipeline."""

    # Input
    cv_id: str
    user_id: str
    jd_text: Optional[str]
    job_id: Optional[str]
    jd_context: str
    lang: str # 'vi' or 'en'
    db: Any

    # Stage 1: CV loaded from DB
    cv_parsed: Optional[CVParsedData]
    cv_timestamp: Optional[int]  # Unix timestamp for cache invalidation
    jd_timestamp: Optional[int]  # Unix timestamp for cache invalidation

    # Stage 2: JD extracted
    jd_requirements: Optional[List[Dict]]
    jd_parsed: Optional[Dict]

    # Stage 3: Gap Analysis
    gap_analysis: Optional[GapAnalysisResult]

    # Stage 4: Course Recommendation
    course_recommendations: Optional[List[CourseRecommendation]]
    youtube_videos: Optional[List[Dict]] # Thêm hỗ trợ YouTube videos

    # Stage 5: Roadmap
    career_roadmap: Optional[CareerRoadmap]

    # Output
    final_report: Optional[Dict]
    status: str
    error: Optional[str]
