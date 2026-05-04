-- Migration: Populate Initial Benchmark Test Sets and Sample Test Cases
-- Purpose: Create sample test sets for CV parsing, gap analysis, and course recommendation

-- ============================================================================
-- 1. CV PARSING TEST SET
-- ============================================================================

INSERT INTO llm_test_sets (id, name, description, flow_type, is_active, created_at)
VALUES (
    '00000000-0000-0000-0001-000000000001',
    'CV Parsing - Quality Benchmark',
    'Test set for evaluating CV parsing accuracy across different CV formats and quality levels',
    'cv_parsing_v3',
    true,
    NOW()
);

-- Sample Test Case 1: High Quality CV (Easy)
INSERT INTO llm_test_cases (id, test_set_id, input_data, reference_output, metadata, created_at)
VALUES (
    '00000000-0000-0000-0001-000000000101',
    '00000000-0000-0000-0001-000000000001',
    '{
        "cv_id": "PLACEHOLDER_CV_ID_1",
        "force_reparse": true,
        "description": "High quality PDF CV with clear structure"
    }',
    '{
        "status": "success",
        "full_name": "Nguyễn Văn A",
        "summary": "Experienced Backend Developer with 5 years in Python and Django",
        "seniority": "Mid-level",
        "experience_years_total": 5.0,
        "skills": [
            {"name": "Python", "category": "Programming Language", "experience_years": 5.0, "level": "Senior"},
            {"name": "Django", "category": "Framework", "experience_years": 4.0, "level": "Mid-level"},
            {"name": "PostgreSQL", "category": "Database", "experience_years": 3.0, "level": "Mid-level"}
        ],
        "work_history": [
            {
                "position": "Backend Developer",
                "company": "Tech Company A",
                "duration_years": 3.0,
                "description": "Developed REST APIs using Django"
            }
        ],
        "education": [
            {"degree": "Bachelor of Computer Science", "institution": "University of Technology", "year": 2018}
        ],
        "certifications": ["AWS Certified Developer"]
    }',
    '{
        "difficulty": "easy",
        "tags": ["high_quality", "structured", "vietnamese"],
        "expected_score": 0.95
    }',
    NOW()
);

-- Sample Test Case 2: OCR CV with spacing issues (Hard)
INSERT INTO llm_test_cases (id, test_set_id, input_data, reference_output, metadata, created_at)
VALUES (
    '00000000-0000-0000-0001-000000000102',
    '00000000-0000-0000-0001-000000000001',
    '{
        "cv_id": "PLACEHOLDER_CV_ID_2",
        "force_reparse": true,
        "description": "OCR CV with character spacing issues"
    }',
    '{
        "status": "success",
        "full_name": "Trần Thị B",
        "summary": "Frontend Developer specializing in React and TypeScript",
        "seniority": "Junior",
        "experience_years_total": 2.0,
        "skills": [
            {"name": "React", "category": "Framework", "experience_years": 2.0, "level": "Junior"},
            {"name": "TypeScript", "category": "Programming Language", "experience_years": 1.5, "level": "Junior"}
        ],
        "work_history": [
            {
                "position": "Frontend Developer",
                "company": "Startup XYZ",
                "duration_years": 2.0,
                "description": "Built responsive web applications"
            }
        ],
        "education": [],
        "certifications": []
    }',
    '{
        "difficulty": "hard",
        "tags": ["ocr", "spacing_issues", "vietnamese"],
        "expected_score": 0.75
    }',
    NOW()
);

-- ============================================================================
-- 2. GAP ANALYSIS TEST SET (PATH A - From Requirements)
-- ============================================================================

INSERT INTO llm_test_sets (id, name, description, flow_type, is_active, created_at)
VALUES (
    '00000000-0000-0000-0002-000000000001',
    'Gap Analysis - Requirements Match',
    'Test set for evaluating gap analysis accuracy when JD requirements are pre-parsed',
    'gap_analysis_from_requirements',
    true,
    NOW()
);

-- Sample Test Case 1: Perfect Match (Easy)
INSERT INTO llm_test_cases (id, test_set_id, input_data, reference_output, metadata, created_at)
VALUES (
    '00000000-0000-0000-0002-000000000101',
    '00000000-0000-0000-0002-000000000001',
    '{
        "cv_id": "PLACEHOLDER_CV_ID_1",
        "job_id": "PLACEHOLDER_JOB_ID_1",
        "jd_requirements": [
            {
                "skill": "Python",
                "target_level": "Mid-level",
                "years_required": 3,
                "is_mandatory": true,
                "importance_weight": 10,
                "is_group": false
            },
            {
                "skill": "Django",
                "target_level": "Mid-level",
                "years_required": 2,
                "is_mandatory": true,
                "importance_weight": 8,
                "is_group": false
            }
        ]
    }',
    '{
        "gap_analysis": {
            "overall_match_pct": 95.0,
            "potential_match_pct": 95.0,
            "overall_assessment": "Ứng viên phù hợp cao với vị trí. Có đầy đủ kỹ năng yêu cầu.",
            "match_breakdown": {
                "Technical Skills": 95.0,
                "Soft Skills": 100.0,
                "Tools & Frameworks": 90.0,
                "Domain Knowledge": 100.0,
                "Certifications": 100.0
            },
            "strengths": ["Python expertise", "Django framework experience"],
            "weaknesses": [],
            "skill_gaps": [],
            "transferable_insights": ["Strong backend development background"]
        }
    }',
    '{
        "difficulty": "easy",
        "tags": ["perfect_match", "backend"],
        "expected_score": 0.95
    }',
    NOW()
);

-- Sample Test Case 2: Partial Match with Gaps (Medium)
INSERT INTO llm_test_cases (id, test_set_id, input_data, reference_output, metadata, created_at)
VALUES (
    '00000000-0000-0000-0002-000000000102',
    '00000000-0000-0000-0002-000000000001',
    '{
        "cv_id": "PLACEHOLDER_CV_ID_2",
        "job_id": "PLACEHOLDER_JOB_ID_2",
        "jd_requirements": [
            {
                "skill": "React",
                "target_level": "Senior",
                "years_required": 5,
                "is_mandatory": true,
                "importance_weight": 10,
                "is_group": false
            },
            {
                "skill": "Docker",
                "target_level": "Intermediate",
                "years_required": 2,
                "is_mandatory": true,
                "importance_weight": 8,
                "is_group": false
            },
            {
                "skill": "Kubernetes",
                "target_level": "Intermediate",
                "years_required": 2,
                "is_mandatory": false,
                "importance_weight": 5,
                "is_group": false
            }
        ]
    }',
    '{
        "gap_analysis": {
            "overall_match_pct": 55.0,
            "potential_match_pct": 75.0,
            "overall_assessment": "Ứng viên có nền tảng React tốt nhưng thiếu kinh nghiệm DevOps. Cần học: Docker, Kubernetes.",
            "match_breakdown": {
                "Technical Skills": 50.0,
                "Soft Skills": 100.0,
                "Tools & Frameworks": 40.0,
                "Domain Knowledge": 80.0,
                "Certifications": 0.0
            },
            "strengths": ["React development", "Frontend expertise"],
            "weaknesses": ["Limited DevOps experience", "No container orchestration"],
            "skill_gaps": [
                {
                    "skill": "Docker",
                    "category": "Tools & Frameworks",
                    "is_group": false,
                    "alternative_skills": [],
                    "required_level": "Intermediate",
                    "severity": "High",
                    "is_critical": true,
                    "estimated_months": 3,
                    "reasoning": "Docker là kỹ năng bắt buộc cho vị trí này",
                    "learning_path": "Học Docker cơ bản, thực hành containerization"
                },
                {
                    "skill": "Kubernetes",
                    "category": "Tools & Frameworks",
                    "is_group": false,
                    "alternative_skills": [],
                    "required_level": "Intermediate",
                    "severity": "Medium",
                    "is_critical": false,
                    "estimated_months": 4,
                    "reasoning": "Kubernetes không bắt buộc nhưng là lợi thế",
                    "learning_path": "Học K8s sau khi thành thạo Docker"
                }
            ],
            "transferable_insights": ["Frontend skills can help with DevOps UI tools"]
        }
    }',
    '{
        "difficulty": "medium",
        "tags": ["partial_match", "devops_gap", "frontend"],
        "expected_score": 0.85
    }',
    NOW()
);

-- ============================================================================
-- 3. GAP ANALYSIS MERGED TEST SET (PATH B - JD Extract + Analysis)
-- ============================================================================

INSERT INTO llm_test_sets (id, name, description, flow_type, is_active, created_at)
VALUES (
    '00000000-0000-0000-0003-000000000001',
    'Gap Analysis - Full Pipeline',
    'Test set for evaluating JD extraction + gap analysis in one call',
    'gap_analysis_merged',
    true,
    NOW()
);

-- Sample Test Case 1: Structured JD (Easy)
INSERT INTO llm_test_cases (id, test_set_id, input_data, reference_output, metadata, created_at)
VALUES (
    '00000000-0000-0000-0003-000000000101',
    '00000000-0000-0000-0003-000000000001',
    '{
        "cv_id": "PLACEHOLDER_CV_ID_1",
        "job_id": "PLACEHOLDER_JOB_ID_1",
        "jd_text": "Senior Backend Developer\n\nRequirements:\n- 5+ years Python experience\n- 3+ years Django/Flask\n- PostgreSQL, Redis\n- Docker, Kubernetes\n- AWS experience preferred"
    }',
    '{
        "jd_parsed": {
            "job_title": "Senior Backend Developer",
            "requirements": [
                {
                    "skill": "Python",
                    "target_level": "Senior",
                    "years_required": 5,
                    "is_mandatory": true,
                    "importance_weight": 10,
                    "is_group": false
                },
                {
                    "skill": "Django",
                    "target_level": "Mid-level",
                    "years_required": 3,
                    "is_mandatory": true,
                    "importance_weight": 8,
                    "is_group": true,
                    "group_strategy": "any_one",
                    "alternative_skills": ["Django", "Flask"]
                },
                {
                    "skill": "PostgreSQL",
                    "target_level": "Mid-level",
                    "years_required": 2,
                    "is_mandatory": true,
                    "importance_weight": 7,
                    "is_group": false
                }
            ]
        },
        "gap_analysis": {
            "overall_match_pct": 90.0,
            "skill_gaps": []
        }
    }',
    '{
        "difficulty": "easy",
        "tags": ["structured_jd", "backend", "skill_groups"],
        "expected_score": 0.90
    }',
    NOW()
);

-- Sample Test Case 2: Unstructured JD with Vietnamese (Hard)
INSERT INTO llm_test_cases (id, test_set_id, input_data, reference_output, metadata, created_at)
VALUES (
    '00000000-0000-0000-0003-000000000102',
    '00000000-0000-0000-0003-000000000001',
    '{
        "cv_id": "PLACEHOLDER_CV_ID_2",
        "job_id": "PLACEHOLDER_JOB_ID_2",
        "jd_text": "Chúng tôi đang tìm kiếm Frontend Developer có kinh nghiệm. Ứng viên cần thành thạo React hoặc Vue, biết TypeScript là lợi thế. Có kinh nghiệm với Git, CI/CD. Ưu tiên ứng viên có ít nhất 3 năm kinh nghiệm."
    }',
    '{
        "jd_parsed": {
            "job_title": "Frontend Developer",
            "requirements": [
                {
                    "skill": "React",
                    "target_level": "Mid-level",
                    "years_required": 3,
                    "is_mandatory": true,
                    "importance_weight": 10,
                    "is_group": true,
                    "group_strategy": "any_one",
                    "alternative_skills": ["React", "Vue"]
                },
                {
                    "skill": "TypeScript",
                    "target_level": "Intermediate",
                    "years_required": 1,
                    "is_mandatory": false,
                    "importance_weight": 5,
                    "is_group": false
                },
                {
                    "skill": "Git",
                    "target_level": "Intermediate",
                    "years_required": 2,
                    "is_mandatory": true,
                    "importance_weight": 7,
                    "is_group": false
                }
            ]
        },
        "gap_analysis": {
            "overall_match_pct": 70.0,
            "skill_gaps": [
                {
                    "skill": "TypeScript",
                    "required_level": "Intermediate",
                    "severity": "Low",
                    "estimated_months": 2
                }
            ]
        }
    }',
    '{
        "difficulty": "hard",
        "tags": ["unstructured_jd", "vietnamese", "frontend", "skill_groups"],
        "expected_score": 0.80
    }',
    NOW()
);

-- ============================================================================
-- 4. COURSE RECOMMENDATION TEST SET
-- ============================================================================

INSERT INTO llm_test_sets (id, name, description, flow_type, is_active, created_at)
VALUES (
    '00000000-0000-0000-0004-000000000001',
    'Course Recommendation - Quality',
    'Test set for evaluating course recommendation and roadmap generation',
    'course_recommendation',
    true,
    NOW()
);

-- Sample Test Case 1: Single Gap with Relevant Courses (Easy)
INSERT INTO llm_test_cases (id, test_set_id, input_data, reference_output, metadata, created_at)
VALUES (
    '00000000-0000-0000-0004-000000000101',
    '00000000-0000-0000-0004-000000000001',
    '{
        "gaps": [
            {
                "skill": "Docker",
                "required_level": "Intermediate",
                "severity": "High",
                "estimated_months": 3
            }
        ],
        "course_candidates": [
            {
                "course_id": "PLACEHOLDER_COURSE_1",
                "title": "Docker Mastery: Complete Toolset",
                "platform": "Udemy",
                "skills": ["Docker", "Docker Compose", "Containerization"]
            },
            {
                "course_id": "PLACEHOLDER_COURSE_2",
                "title": "Node.js Complete Guide",
                "platform": "Udemy",
                "skills": ["Node.js", "Express", "MongoDB"]
            }
        ],
        "youtube_candidates": [
            {
                "video_id": "PLACEHOLDER_VIDEO_1",
                "title": "Docker Tutorial for Beginners",
                "channel_name": "TechWorld with Nana"
            }
        ]
    }',
    '{
        "selected_courses": [
            {
                "course_id": "PLACEHOLDER_COURSE_1",
                "video_id": null,
                "gap_skills": ["Docker"],
                "selection_reason": "Khóa học này dạy Docker từ cơ bản đến nâng cao, phù hợp với yêu cầu Intermediate level",
                "stage": 1
            },
            {
                "course_id": null,
                "video_id": "PLACEHOLDER_VIDEO_1",
                "gap_skills": ["Docker"],
                "selection_reason": "Video miễn phí giúp làm quen với Docker trước khi học khóa chính",
                "stage": 1
            }
        ],
        "career_roadmap": {
            "stages": [
                {
                    "stage": 1,
                    "focus": "Docker Fundamentals",
                    "duration_weeks": 4,
                    "skills_acquired": ["Docker", "Containerization"],
                    "courses_taken": ["Docker Mastery: Complete Toolset"],
                    "milestones": [
                        {"week": 1, "milestone": "Hiểu khái niệm container và image"},
                        {"week": 2, "milestone": "Tạo và chạy containers"},
                        {"week": 3, "milestone": "Docker Compose multi-container apps"},
                        {"week": 4, "milestone": "Deploy ứng dụng với Docker"}
                    ]
                }
            ],
            "total_weeks": 4,
            "total_hours": 40,
            "summary": "Lộ trình 4 tuần để thành thạo Docker từ cơ bản đến triển khai thực tế"
        }
    }',
    '{
        "difficulty": "easy",
        "tags": ["single_gap", "relevant_courses", "docker"],
        "expected_score": 0.95,
        "evaluation_criteria": {
            "course_relevance": "Must select Docker course, not Node.js",
            "no_hallucination": "Should not select Node.js course for Docker gap",
            "roadmap_quality": "Logical 4-week progression"
        }
    }',
    NOW()
);

-- Sample Test Case 2: Multiple Gaps with Limited Courses (Medium)
INSERT INTO llm_test_cases (id, test_set_id, input_data, reference_output, metadata, created_at)
VALUES (
    '00000000-0000-0000-0004-000000000102',
    '00000000-0000-0000-0004-000000000001',
    '{
        "gaps": [
            {
                "skill": "Kubernetes",
                "required_level": "Intermediate",
                "severity": "High",
                "estimated_months": 4
            },
            {
                "skill": "Terraform",
                "required_level": "Beginner",
                "severity": "Medium",
                "estimated_months": 2
            },
            {
                "skill": "AWS",
                "required_level": "Intermediate",
                "severity": "High",
                "estimated_months": 3
            }
        ],
        "course_candidates": [
            {
                "course_id": "PLACEHOLDER_COURSE_3",
                "title": "Kubernetes for Absolute Beginners",
                "platform": "Udemy",
                "skills": ["Kubernetes", "K8s", "Container Orchestration"]
            },
            {
                "course_id": "PLACEHOLDER_COURSE_4",
                "title": "AWS Certified Solutions Architect",
                "platform": "Udemy",
                "skills": ["AWS", "EC2", "S3", "Lambda"]
            }
        ],
        "youtube_candidates": []
    }',
    '{
        "selected_courses": [
            {
                "course_id": "PLACEHOLDER_COURSE_3",
                "video_id": null,
                "gap_skills": ["Kubernetes"],
                "selection_reason": "Khóa học Kubernetes phù hợp cho người mới bắt đầu",
                "stage": 2
            },
            {
                "course_id": "PLACEHOLDER_COURSE_4",
                "video_id": null,
                "gap_skills": ["AWS"],
                "selection_reason": "Khóa AWS giúp đạt Intermediate level",
                "stage": 1
            }
        ],
        "career_roadmap": {
            "stages": [
                {
                    "stage": 1,
                    "focus": "AWS Cloud Fundamentals",
                    "duration_weeks": 6,
                    "skills_acquired": ["AWS", "EC2", "S3"],
                    "courses_taken": ["AWS Certified Solutions Architect"],
                    "milestones": [
                        {"week": 2, "milestone": "Hiểu AWS core services"},
                        {"week": 4, "milestone": "Deploy ứng dụng lên EC2"},
                        {"week": 6, "milestone": "Thi chứng chỉ AWS"}
                    ]
                },
                {
                    "stage": 2,
                    "focus": "Kubernetes Container Orchestration",
                    "duration_weeks": 8,
                    "skills_acquired": ["Kubernetes", "K8s"],
                    "courses_taken": ["Kubernetes for Absolute Beginners"],
                    "milestones": [
                        {"week": 2, "milestone": "Hiểu K8s architecture"},
                        {"week": 4, "milestone": "Deploy apps với K8s"},
                        {"week": 8, "milestone": "Production-ready K8s"}
                    ]
                }
            ],
            "total_weeks": 14,
            "total_hours": 120,
            "summary": "Lộ trình 14 tuần: AWS trước, sau đó Kubernetes. Terraform sẽ học sau khi thành thạo 2 kỹ năng này."
        }
    }',
    '{
        "difficulty": "medium",
        "tags": ["multiple_gaps", "limited_courses", "devops"],
        "expected_score": 0.85,
        "evaluation_criteria": {
            "course_relevance": "Must match courses to correct gaps",
            "no_hallucination": "Should acknowledge Terraform has no course",
            "roadmap_quality": "Logical progression: AWS → K8s"
        }
    }',
    NOW()
);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE llm_test_sets IS 'Benchmark test sets for evaluating LLM prompt quality';
COMMENT ON TABLE llm_test_cases IS 'Individual test cases with input data and expected outputs';
COMMENT ON COLUMN llm_test_cases.input_data IS 'JSON input for the flow (cv_id, job_id, etc.)';
COMMENT ON COLUMN llm_test_cases.reference_output IS 'Ground truth output for evaluation';
COMMENT ON COLUMN llm_test_cases.metadata IS 'Test metadata: difficulty, tags, expected_score, evaluation_criteria';

-- ============================================================================
-- NOTES FOR USAGE
-- ============================================================================

-- To use these test sets:
-- 1. Replace PLACEHOLDER_CV_ID_* with actual CV IDs from your database
-- 2. Replace PLACEHOLDER_JOB_ID_* with actual job IDs
-- 3. Replace PLACEHOLDER_COURSE_* with actual course IDs
-- 4. Replace PLACEHOLDER_VIDEO_* with actual YouTube video IDs
-- 5. Run benchmark via API: POST /admin/benchmarks/run

-- Example query to update placeholders:
-- UPDATE llm_test_cases 
-- SET input_data = jsonb_set(input_data, '{cv_id}', '"actual-uuid-here"')
-- WHERE input_data->>'cv_id' = 'PLACEHOLDER_CV_ID_1';
