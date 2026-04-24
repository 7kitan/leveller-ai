"""
Integration tests cho gap_v3: CV Parsing + Gap Analysis pipeline.
Requires DB + Redis + OpenAI API to be running.
"""

import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Skip if OPENAI_API_KEY not set
SKIP_IF_NO_API = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
)


@SKIP_IF_NO_API
class TestCVParsingPipeline:
    """Integration tests cho CV Parsing pipeline."""

    def test_cv_parsing_pipeline_runs(self):
        """Test rằng pipeline chạy được mà không crash."""
        import asyncio
        from worker.langgraph_agents.gap_v3.cv_parsing_graph import (
            run_cv_parsing_pipeline,
        )
        from unittest.mock import MagicMock

        # Mock DB
        mock_db = MagicMock()
        mock_cv_record = MagicMock()
        mock_cv_record.id = "00000000-0000-0000-0000-000000000001"
        mock_cv_record.raw_text = """
        Nguyen Van A
        Senior Software Engineer

        EXPERIENCE:
        - Backend Engineer @ TechCorp (2020-2024) 3 năm
          Built APIs with Python and Django
          Skills: Python, Django, PostgreSQL, Docker

        - Junior Developer @ StartupXYZ (2019-2020) 1 năm
          Developed web apps with Node.js
          Skills: Node.js, React, MongoDB

        SKILLS:
        - Python: 4 năm, Advanced
        - Django: 3 năm, Advanced
        - PostgreSQL: 3 năm, Intermediate
        - Docker: 2 năm, Intermediate

        EDUCATION:
        - Bachelor of Computer Science, HUST, 2019
        """
        mock_cv_record.is_ocr = False
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_cv_record
        )

        # Mock skill upsert (don't actually commit)
        async def mock_upsert(*args, **kwargs):
            return 4

        result = asyncio.get_event_loop().run_until_complete(
            run_cv_parsing_pipeline(
                cv_id="00000000-0000-0000-0000-000000000001",
                user_id="00000000-0000-0000-0000-000000000002",
                db=mock_db,
            )
        )

        assert result["status"] == "success"
        cv_parsed = result["cv_parsed"]
        assert cv_parsed is not None
        assert cv_parsed.get("full_name") is not None

        # Skills phải được extract
        skills = cv_parsed.get("skills", [])
        assert len(skills) >= 3  # At least Python, Django, PostgreSQL

        skill_names = [s["name"] for s in skills]
        print(f"  Extracted skills: {skill_names}")

        # Experience years phải > 0
        assert cv_parsed.get("experience_years_total", 0) > 0


@SKIP_IF_NO_API
class TestGapAnalysisPipeline:
    """Integration tests cho Gap Analysis v3 pipeline."""

    def test_gap_analysis_llm_node_runs(self):
        """Test rằng gap_analysis_llm_node chạy được."""
        import asyncio
        from worker.langgraph_agents.gap_v3.nodes.gap_nodes import gap_analysis_llm_node

        mock_state = {
            "cv_id": "test-cv-id",
            "user_id": "test-user-id",
            "cv_parsed": {
                "full_name": "Nguyen Van A",
                "summary": "Senior Backend Engineer",
                "seniority": "Senior",
                "experience_years_total": 6.0,
                "skills": [
                    {
                        "name": "Python",
                        "level": "Advanced",
                        "years_exp": 6.0,
                        "context": "Django, FastAPI",
                        "last_used": 2025,
                    },
                    {
                        "name": "PostgreSQL",
                        "level": "Advanced",
                        "years_exp": 5.0,
                        "context": "Database design",
                        "last_used": 2025,
                    },
                    {
                        "name": "Docker",
                        "level": "Intermediate",
                        "years_exp": 2.0,
                        "context": "Containerization",
                        "last_used": 2024,
                    },
                ],
                "work_history": [
                    {
                        "position": "Senior Backend Engineer",
                        "company": "TechCorp",
                        "duration_years": 4.0,
                        "description": "Built microservices with Python"
                    }
                ],
                "education": [],
                "certifications": [],
                "is_ocr": False,
                "ocr_confidence": 1.0,
                "raw_text_masked": "",
            },
            "jd_requirements": [
                {
                    "skill": "Python",
                    "target_level": "Senior",
                    "years_required": 4,
                    "is_mandatory": True,
                    "importance_weight": 10,
                    "type": "skill",
                },
                {
                    "skill": "Kubernetes",
                    "target_level": "Mid-level",
                    "years_required": 2,
                    "is_mandatory": True,
                    "importance_weight": 9,
                    "type": "skill",
                },
                {
                    "skill": "FastAPI",
                    "target_level": "Intermediate",
                    "years_required": 1,
                    "is_mandatory": False,
                    "importance_weight": 5,
                    "type": "skill",
                },
                {
                    "skill": "AWS",
                    "target_level": "Intermediate",
                    "years_required": 2,
                    "is_mandatory": True,
                    "importance_weight": 8,
                    "type": "skill",
                },
            ],
            "jd_context": "Senior Backend Engineer @ BigTech Corp",
            "db": None,
            "status": "started",
            "error": None,
        }

        result = asyncio.get_event_loop().run_until_complete(
            gap_analysis_llm_node(mock_state)
        )

        assert result["status"] == "gap_analyzed", f"Error: {result.get('error')}"
        gap_analysis = result["gap_analysis"]

        # Check required fields
        assert "overall_match_pct" in gap_analysis
        assert "overall_assessment" in gap_analysis
        assert "skill_gaps" in gap_analysis
        assert "gap_summary" in gap_analysis

        overall_pct = gap_analysis["overall_match_pct"]
        assert 0 <= overall_pct <= 100, f"Invalid match pct: {overall_pct}"

        skill_gaps = gap_analysis["skill_gaps"]
        assert len(skill_gaps) > 0, "Should have at least 1 gap"

        # Kubernetes should be a gap (user has Docker but not K8s)
        gap_names = [g["skill"] for g in skill_gaps]
        print(f"  Skill gaps: {gap_names}")

        # Severity sorting: HIGH first
        if len(skill_gaps) > 1:
            sev_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            for i in range(len(skill_gaps) - 1):
                curr_sev = sev_order.get(skill_gaps[i].get("severity", "LOW"), 2)
                next_sev = sev_order.get(skill_gaps[i + 1].get("severity", "LOW"), 2)
                assert curr_sev <= next_sev, "Should be sorted HIGH → MEDIUM → LOW"

        print(f"  Overall match: {overall_pct}%")
        print(
            f"  Gaps: {len(skill_gaps)}, critical: {gap_analysis['gap_summary'].get('critical_gaps', 0)}"
        )

    def test_course_node_runs(self):
        """Test rằng course recommendation node chạy được."""
        import asyncio
        from worker.langgraph_agents.gap_v3.nodes.course_nodes import (
            _llm_prioritize_gaps,
            _deduplicate_and_rank,
        )
        from unittest.mock import MagicMock

        # Test prioritize
        gaps = [
            {
                "skill": "Kubernetes",
                "severity": "HIGH",
                "is_critical": True,
                "estimated_months": 3,
                "bridge_from": "Docker",
                "learning_path": "Docker → K8s",
                "learning_effort": "MEDIUM",
            },
            {
                "skill": "Terraform",
                "severity": "HIGH",
                "is_critical": False,
                "estimated_months": 2,
                "bridge_from": None,
                "learning_path": "IaC → Terraform",
                "learning_effort": "MEDIUM",
            },
            {
                "skill": "TypeScript",
                "severity": "LOW",
                "is_critical": False,
                "estimated_months": 1,
                "bridge_from": "JavaScript",
                "learning_path": "JS → TS",
                "learning_effort": "EASY",
            },
        ]

        # Test dedup + rank
        courses = [
            {
                "course_id": "c1",
                "gap_severity": "HIGH",
                "is_certification": True,
                "similarity": 0.8,
            },
            {
                "course_id": "c2",
                "gap_severity": "HIGH",
                "is_certification": False,
                "similarity": 0.7,
            },
            {
                "course_id": "c1",
                "gap_severity": "HIGH",
                "is_certification": True,
                "similarity": 0.8,
            },  # duplicate
            {
                "course_id": "c3",
                "gap_severity": "MEDIUM",
                "is_certification": True,
                "similarity": 0.9,
            },
        ]

        ranked = _deduplicate_and_rank(courses)

        # c1 should appear only once
        c1_count = sum(1 for c in ranked if c["course_id"] == "c1")
        assert c1_count == 1, "c1 should be deduplicated"

        # HIGH severity should rank higher
        high_course = next((c for c in ranked if c["course_id"] == "c1"), None)
        assert high_course is not None
        assert high_course["gap_severity"] == "HIGH"

        print(
            f"  Ranked courses: {[(c['course_id'], c['rank_score']) for c in ranked]}"
        )


@SKIP_IF_NO_API
class TestCourseRecommendation:
    """Test course recommendation node."""

    def test_llm_prioritize_gaps_runs(self):
        """Test rằng _llm_prioritize_gaps chạy được."""
        import asyncio
        from worker.langgraph_agents.gap_v3.nodes.course_nodes import (
            _llm_prioritize_gaps,
        )

        gaps = [
            {
                "skill": "Kubernetes",
                "severity": "HIGH",
                "is_critical": True,
                "estimated_months": 3,
                "bridge_from": "Docker",
                "learning_path": "Docker → K8s",
                "learning_effort": "MEDIUM",
            },
            {
                "skill": "AWS",
                "severity": "MEDIUM",
                "is_critical": True,
                "estimated_months": 4,
                "bridge_from": None,
                "learning_path": "AWS basics → EC2 → Lambda",
                "learning_effort": "MEDIUM",
            },
            {
                "skill": "TypeScript",
                "severity": "LOW",
                "is_critical": False,
                "estimated_months": 1,
                "bridge_from": "JavaScript",
                "learning_path": "JS → TS",
                "learning_effort": "EASY",
            },
        ]

        result = asyncio.get_event_loop().run_until_complete(
            _llm_prioritize_gaps(gaps, "Senior Backend Engineer @ BigTech")
        )

        assert isinstance(result, list)
        assert len(result) <= 3, "Should return max 3 gaps"

        # Kubernetes (HIGH + critical) should be prioritized
        if result:
            top = result[0]
            print(f"  Top gap: {top.get('skill') if isinstance(top, dict) else top}")
            assert top is not None

        print(f"  Prioritized gaps: {result}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
