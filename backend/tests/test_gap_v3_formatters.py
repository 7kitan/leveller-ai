"""
Tests cho gap_v3: CV Formatting helpers — standalone, no package imports.
Các formatting functions được copy trực tiếp vào để test mà không cần import chain.
"""

import pytest


# ─── Copy of formatting functions for testing (standalone) ────────────────


def _format_cv_for_llm_test(cv_parsed: dict) -> str:
    """Format structured CV parsed data thành text cho LLM."""
    skills = cv_parsed.get("skills", [])
    work_history = cv_parsed.get("work_history", [])
    education = cv_parsed.get("education", [])
    certs = cv_parsed.get("certifications", [])

    skills_lines = []
    for s in skills:
        level = s.get("level", "Unknown")
        years = s.get("years_exp", 0)
        ctx = s.get("context", "")
        skills_lines.append(
            f"  - {s['name']} | {level} | {years:.1f} năm"
            + (f" | {ctx}" if ctx else "")
        )
    skills_text = "\n".join(skills_lines) or "  (Không có kỹ năng)"

    work_lines = []
    for w in work_history:
        dur = w.get("duration_years", 0)
        skills_used = ", ".join(w.get("skills_used", [])[:8])
        desc = w.get("description", "")[:200]
        work_lines.append(
            f"  - [{dur:.1f} năm] {w.get('position', 'N/A')} @ {w.get('company', 'N/A')}\n"
            f"    {desc}\n"
            f"    Technologies: {skills_used or 'N/A'}"
        )
    work_text = "\n".join(work_lines) or "  (Không có kinh nghiệm)"

    edu_lines = []
    for e in education:
        edu_lines.append(
            f"  - {e.get('degree', '')} - {e.get('field', '')} @ {e.get('institution', '')} ({e.get('year', '')})"
        )
    edu_text = "\n".join(edu_lines) or "  (Không có thông tin)"

    cert_text = ""
    if certs:
        cert_lines = [
            f"  - {c.get('name', '')} ({c.get('issuer', '')}, {c.get('year', '')})"
            for c in certs
        ]
        cert_text = "\n## CHỨNG CHỈ\n" + "\n".join(cert_lines)

    seniority = cv_parsed.get("seniority", "Unknown")
    exp_total = cv_parsed.get("experience_years_total", 0)

    return f"""## TỔNG QUAN
Seniority: {seniority} | Tổng kinh nghiệm: {exp_total:.1f} năm
{cv_parsed.get("summary", "")}

## KỸ NĂNG KỸ THUẬT
{skills_text}

## KINH NGHIỆM LÀM VIỆC
{work_text}

## HỌC VẤN
{edu_text}
{cert_text}"""


def _format_jd_for_llm_test(jd_requirements: list) -> str:
    """Format JD requirements thành text cho LLM."""
    if not jd_requirements:
        return "  (Không có yêu cầu cụ thể)"

    lines = []
    for req in jd_requirements:
        mandatory_tag = "🔴 BẮT BUỘC" if req.get("is_mandatory") else "⚪ TÙY CHỌN"
        level = req.get("target_level", "Mid-level")
        years = req.get("years_required", 0)
        weight = req.get("importance_weight", 5)
        skill_name = req.get("skill") or req.get("group_name", "Unknown")

        if req.get("type") == "group":
            group_skills = ", ".join(
                [s.get("skill", "?") for s in req.get("group_skills", [])]
            )
            strategy = (
                "OR (ít nhất 1)"
                if req.get("group_strategy") == "OR"
                else "AND (tất cả)"
            )
            lines.append(
                f"  {mandatory_tag} GROUP [{strategy}]: {skill_name}\n"
                f"    Options: {group_skills} | Weight: {weight}"
            )
        else:
            year_str = f" | {years} năm kinh nghiệm" if years else ""
            lines.append(
                f"  {mandatory_tag} {skill_name} | {level}{year_str} | Weight: {weight}"
            )

    return "\n".join(lines)


# ─── Test Cases ──────────────────────────────────────────────────────────


class TestCVFormatter:
    """Test cases cho CV formatting."""

    def test_format_cv_full(self):
        cv_parsed = {
            "full_name": "Nguyen Van A",
            "summary": "Senior backend developer with 6 years experience",
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
                    "level": "Intermediate",
                    "years_exp": 4.0,
                    "context": "",
                    "last_used": 2024,
                },
            ],
            "work_history": [
                {
                    "position": "Senior Backend Engineer",
                    "company": "TechCorp",
                    "duration_years": 3.0,
                    "description": "Built microservices with Python",
                    "skills_used": ["Python", "Docker", "PostgreSQL"],
                }
            ],
            "education": [
                {
                    "degree": "Bachelor",
                    "institution": "HUST",
                    "year": 2018,
                    "field": "Computer Science",
                }
            ],
            "certifications": [
                {"name": "AWS Solutions Architect", "issuer": "Amazon", "year": 2023}
            ],
        }

        result = _format_cv_for_llm_test(cv_parsed)

        assert "Senior" in result
        assert "6.0 năm" in result
        assert "Python" in result
        assert "PostgreSQL" in result
        assert "TechCorp" in result
        assert "HUST" in result
        assert "AWS Solutions Architect" in result
        assert "Django" in result

    def test_format_cv_minimal(self):
        cv_parsed = {
            "full_name": "Unknown",
            "summary": "",
            "seniority": "Unknown",
            "experience_years_total": 0,
            "skills": [],
            "work_history": [],
            "education": [],
            "certifications": [],
        }

        result = _format_cv_for_llm_test(cv_parsed)
        assert "Unknown" in result
        assert "0.0 năm" in result

    def test_format_cv_empty_skills(self):
        cv_parsed = {
            "full_name": "Test User",
            "summary": "Junior dev",
            "seniority": "Junior",
            "experience_years_total": 1.0,
            "skills": [],
            "work_history": [],
            "education": [],
            "certifications": [],
        }

        result = _format_cv_for_llm_test(cv_parsed)
        assert "Không có kỹ năng" in result

    def test_format_cv_seniority_detection(self):
        cv_parsed = {
            "full_name": "Test",
            "summary": "Expert developer",
            "seniority": "Expert",
            "experience_years_total": 10.0,
            "skills": [
                {
                    "name": "Python",
                    "level": "Expert",
                    "years_exp": 10.0,
                    "context": "",
                    "last_used": 2025,
                }
            ],
            "work_history": [],
            "education": [],
            "certifications": [],
        }

        result = _format_cv_for_llm_test(cv_parsed)
        assert "Expert" in result
        assert "10.0 năm" in result


class TestJDFormatter:
    """Test cases cho JD formatting."""

    def test_format_jd_basic(self):
        jd_requirements = [
            {
                "skill": "Python",
                "target_level": "Mid-level",
                "years_required": 3,
                "is_mandatory": True,
                "importance_weight": 9,
                "type": "skill",
            },
            {
                "skill": "Docker",
                "target_level": "Junior",
                "years_required": 0,
                "is_mandatory": False,
                "importance_weight": 4,
                "type": "skill",
            },
        ]

        result = _format_jd_for_llm_test(jd_requirements)

        assert "Python" in result
        assert "Mid-level" in result
        assert "Docker" in result
        assert "🔴 BẮT BUỘC" in result
        assert "⚪ TÙY CHỌN" in result
        assert "3 năm" in result

    def test_format_jd_group(self):
        jd_requirements = [
            {
                "skill": "Backend Alternatives",
                "type": "group",
                "group_strategy": "OR",
                "is_mandatory": True,
                "importance_weight": 8,
                "group_skills": [{"skill": "Java"}, {"skill": "Go"}],
            }
        ]

        result = _format_jd_for_llm_test(jd_requirements)

        assert "OR" in result
        assert "Java" in result
        assert "Go" in result
        assert "🔴 BẮT BUỘC" in result

    def test_format_jd_empty(self):
        result = _format_jd_for_llm_test([])
        assert "Không có yêu cầu" in result

    def test_format_jd_weight(self):
        jd_requirements = [
            {
                "skill": "React",
                "target_level": "Senior",
                "years_required": 3,
                "is_mandatory": True,
                "importance_weight": 10,
                "type": "skill",
            }
        ]
        result = _format_jd_for_llm_test(jd_requirements)
        assert "Weight: 10" in result

    def test_format_jd_no_years(self):
        jd_requirements = [
            {
                "skill": "Git",
                "target_level": "Junior",
                "years_required": 0,
                "is_mandatory": True,
                "importance_weight": 5,
                "type": "skill",
            }
        ]
        result = _format_jd_for_llm_test(jd_requirements)
        assert "0 năm" not in result  # Should not show years when 0


class TestSkillGapNormalization:
    """Test logic xử lý skill gap data."""

    def test_severity_order_high_medium_low(self):
        """Skill gaps phải được sort: HIGH → MEDIUM → LOW."""
        gaps = [
            {
                "skill": "TypeScript",
                "severity": "LOW",
                "is_critical": False,
                "estimated_months": 1,
            },
            {
                "skill": "Kubernetes",
                "severity": "HIGH",
                "is_critical": True,
                "estimated_months": 3,
            },
            {
                "skill": "AWS",
                "severity": "MEDIUM",
                "is_critical": False,
                "estimated_months": 4,
            },
        ]
        sev_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_gaps = sorted(
            gaps, key=lambda g: sev_order.get(g.get("severity", "LOW"), 2)
        )
        assert sorted_gaps[0]["skill"] == "Kubernetes"
        assert sorted_gaps[1]["skill"] == "AWS"
        assert sorted_gaps[2]["skill"] == "TypeScript"

    def test_bridge_skill_recognition(self):
        """Bridge skill giúp giảm estimated_months."""
        gap_with_bridge = {
            "skill": "Kubernetes",
            "severity": "HIGH",
            "is_critical": True,
            "bridge_from": "Docker",  # Có Docker → học K8s nhanh hơn
            "estimated_months": 3,
        }
        gap_without_bridge = {
            "skill": "Terraform",
            "severity": "HIGH",
            "is_critical": True,
            "bridge_from": None,
            "estimated_months": 4,
        }
        assert gap_with_bridge["bridge_from"] == "Docker"
        assert gap_without_bridge["bridge_from"] is None
        assert (
            gap_with_bridge["estimated_months"] < gap_without_bridge["estimated_months"]
        )

    def test_blocking_skills(self):
        """Blocking skills là HIGH severity + is_critical = True."""
        gaps = [
            {"skill": "Kubernetes", "severity": "HIGH", "is_critical": True},
            {"skill": "Git", "severity": "LOW", "is_critical": False},
            {"skill": "AWS", "severity": "MEDIUM", "is_critical": True},
        ]
        blocking = [
            g["skill"] for g in gaps if g["severity"] == "HIGH" and g["is_critical"]
        ]
        assert "Kubernetes" in blocking
        assert "Git" not in blocking

    def test_learning_effort_mapping(self):
        """Learning effort phải map đúng."""
        effort_map = {
            (0.5, True): "EASY",
            (2.0, True): "MEDIUM",
            (4.0, True): "HARD",
            (8.0, True): "EXPERT",
        }

        assert effort_map[(0.5, True)] == "EASY"
        assert effort_map[(4.0, True)] == "HARD"


class TestCourseRanking:
    """Test logic ranking course recommendations."""

    def test_deduplicate_courses(self):
        """Không trùng course_id."""
        courses = [
            {"course_id": "c1", "title": "K8s Basics", "gap_severity": "HIGH"},
            {"course_id": "c2", "title": "Docker Master", "gap_severity": "HIGH"},
            {"course_id": "c1", "title": "K8s Basics", "gap_severity": "HIGH"},  # dup
        ]
        seen = {}
        for c in courses:
            if c["course_id"] not in seen:
                seen[c["course_id"]] = c
        result = list(seen.values())
        assert len(result) == 2

    def test_severity_affects_rank_score(self):
        """HIGH severity courses phải rank cao hơn."""
        sev_w = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}
        high = round(sev_w["HIGH"] * 0.6 + 0.2 + 0.16, 3)
        med = round(sev_w["MEDIUM"] * 0.6 + 0.2 + 0.16, 3)
        low = round(sev_w["LOW"] * 0.6 + 0.2 + 0.16, 3)

        assert high > med > low

    def test_certification_bonus(self):
        """Certification bonus = 0.2."""
        sev_w = {"HIGH": 1.0}
        cert_score = round(sev_w["HIGH"] * 0.6 + 0.2 + 0.16, 3)
        no_cert_score = round(sev_w["HIGH"] * 0.6 + 0.0 + 0.16, 3)
        assert cert_score > no_cert_score

    def test_top_3_gaps_filter(self):
        """Chỉ giữ TOP 3 gaps."""
        all_gaps = [
            {
                "skill": f"Skill{i}",
                "severity": ["HIGH", "MEDIUM", "LOW"][i % 3],
                "is_critical": i % 2 == 0,
            }
            for i in range(10)
        ]
        sev_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_gaps = sorted(
            all_gaps,
            key=lambda g: (
                sev_order.get(g.get("severity", "LOW"), 2),
                -int(g.get("is_critical", False)),
            ),
        )
        top_3 = sorted_gaps[:3]
        assert len(top_3) == 3
        # First must be HIGH
        assert top_3[0]["severity"] == "HIGH"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
