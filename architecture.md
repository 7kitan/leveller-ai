# AI Career Advisor — System Architecture Document

> **Project:** `backend/` — `C:\Users\bach\Documents\Project\Team078\backend`
> **Database:** PostgreSQL (with pgvector), Redis, Celery (async worker)
> **LLM:** OpenAI GPT-4o-mini via `openai` SDK
> **Embedding:** OpenAI `text-embedding-3-small` (1536 dims)

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                          │
│   Upload CV → Select Job → View Gap Analysis → Career Roadmap        │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ HTTP
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│               GATEWAY  (gateway/main.py — FastAPI)                  │
│   Reverse proxy — routes to microservices by service_name header    │
│   Auth middleware injects X-User-ID, X-Is-Admin headers            │
└──────┬──────┬──────────┬──────────────┬──────────────────────────┘
       │      │          │              │
       ▼      ▼          ▼              ▼
   auth-svc cv-svc   jd-svc    analysis-svc  recommend-svc
  (auth)   (CV)     (Jobs)     (Gap Analysis)  (Courses)
  :8000    :8000    :8000        :8000          :8000
```

### Service Routing (Gateway)

| Service Name | Target URL | Routes |
|---|---|---|
| `auth` | `auth-service:8000/auth/` | Login, register, user profile |
| `user` | `auth-service:8000/auth/` | User management |
| `cv` | `cv-service:8000` | Upload CV, list, skills CRUD |
| `jd` | `jd-service:8000` | Job search, JD management |
| `analysis` | `analysis-service:8000` | Gap analysis, feedback, roadmap |
| `recommend` | `recommender-service:8000` | Course CRUD, trending skills |

---

## 2. API Reference

### 2.1 Auth Service (`services/auth_service/main.py`)

> Port: `:8000` | Gateway prefix: `/auth/`

#### `POST /auth/register`
```json
Request:  { "email": "user@example.com", "password": "..." }
Response: { "user_id": "uuid", "email": "...", "is_active": true }
```

#### `POST /auth/login`
```json
Request:  { "email": "...", "password": "..." }
Response: { "user_id": "uuid", "email": "...", "is_admin": false }
```

---

### 2.2 CV Service (`services/cv_service/main.py`)

> Port: `:8000` | Gateway prefix: `/cv/`
> **Auth:** `X-User-ID` header (required)

#### `POST /cv/upload`
```
Request:  multipart/form-data — file: PDF/DOCX
Response: { "cv_id": "uuid", "parser_id": "task_uuid", "status": "processing" }

Behavior:
  • Checks file_hash (SHA256) → duplicate detection
  • If duplicate & completed → returns parsed data immediately
  • Dispatches Celery task: worker.tasks.cv_parsing_v3_task.run_cv_parsing
  • Feature flag: USE_LLM_GAP_AGENT_V3=true → v3 pipeline, false → legacy
```

#### `GET /cv/list`
```json
Response: [
  { "id": "uuid", "full_name": "...", "status": "completed", "created_at": "..." }
]
```

#### `GET /cv/{cv_id}`
```json
Response: {
  "id": "uuid",
  "full_name": "...",
  "skills": [{ "id": "uuid", "name": "Python", "experience_years": 3, "level": "Mid-level" }],
  "work_history": [...],
  "education": [...],
  "certifications": [...],
  "seniority": "Senior",
  "experience_years_total": 5,
  "is_ocr": false,
  "ocr_confidence": 0.95,
  "ocr_warning": null,           // null | "⚠️ CV này được xử lý từ ảnh/scan..."
  "cv_parsed": { ... }          // Full structured CV data (v3)
}
```

#### `GET /cv/status/{task_id}`
```json
Response: {
  "task_id": "...",
  "status": "completed" | "processing" | "failed",
  "result": { ... }              // Full CV data if completed
}
```

#### `POST /cv/finalize`
```json
Request: {
  "id": "cv_uuid",
  "skills": [{ "name": "Python", "experience_years": 3, "level": "Mid-level", "category": "Technology" }],
  "user_info": { "full_name": "...", "total_exp_years": 5 }
}
Response: { "message": "Portfolio updated successfully" }
```

#### `GET /cv/{cv_id}/analysis/history`
```json
Response: [
  { "id": "uuid", "match_score": 72, "created_at": "..." }
]
```

---

### 2.3 JD Service (`services/jd_service/main.py`)

> Port: `:8000` | Gateway prefix: `/jd/`

#### `GET /jd/jobs`
```json
Query: ?q=python&location=HCM&page=1&limit=20
Response: {
  "items": [
    {
      "id": "uuid",
      "title_raw": "Senior Python Engineer",
      "company_name": "FPT Software",
      "min_salary_vnd": 20000000,
      "max_salary_vnd": 40000000,
      "location_raw": "Ho Chi Minh City",
      "similarity": 0.87,          // pgvector similarity (JD vs CV skills)
      "skills_required": ["Python", "Django", "PostgreSQL"]
    }
  ],
  "total": 142,
  "page": 1,
  "pages": 8
}
```

#### `GET /jd/jobs/{job_id}`
```json
Response: {
  "id": "uuid",
  "title_raw": "Senior Python Engineer",
  "company_name": "FPT Software",
  "raw_text": "...",
  "skills_required": [...],
  "extracted_requirements_json": [    // ← PRE-EXTRACTED requirements
    { "type": "skill", "skill": "Python", "target_level": "Senior", "years_required": 3 },
    { "type": "group", "group_name": "Frontend", "group_strategy": "exclusive",
      "skills": [
        { "skill": "ReactJS", "target_level": "Mid-level", "years_required": 2 },
        { "skill": "VueJS", "target_level": "Mid-level", "years_required": 2 }
      ]
    }
  ]
}
```

#### `GET /jd/jobs/search` (Vector search)
```json
Query: ?q=backend+python+senior&limit=10
Response: { "items": [...], "total": N }
```

---

### 2.4 Analysis Service (`services/analysis_service/main.py`)

> Port: `:8000` | Gateway prefix: `/analysis/`
> **Auth:** `X-User-ID` header (required)

#### `POST /analysis/gap` ⭐ Main Gap Analysis
```json
Request: {
  "cv_id": "uuid",
  "job_id": "uuid" | null,     // OR
  "jd_text": "string" | null    // user can paste JD instead
}
Response: { "task_id": "celery_task_uuid", "status": "processing" }

Behavior:
  • Validates CV status == "completed"
  • Dispatches: worker.tasks.analysis_tasks.run_gap_analysis
  • USE_LLM_GAP_AGENT=true → v3 LangGraph pipeline
  • USE_LLM_GAP_AGENT=false → legacy AdvancedGapEngine
```

#### `GET /analysis/status/{task_id}`
```json
Response: { "status": "completed" | "processing",
            "result": { ... } }   // Full gap analysis report if completed
```

#### `GET /analysis/user/latest`
```json
Response: {
  "overall_match_pct": 72,
  "overall_assessment": "Bạn phù hợp ở mức khá...",
  "strengths": ["Python expertise", "FastAPI experience"],
  "weaknesses": ["Missing Kubernetes"],
  "skill_gaps": [
    { "skill": "Kubernetes", "severity": "HIGH", "required_level": "Mid-level",
      "estimated_months": 3, "learning_path": "Tìm hiểu container..." }
  ],
  "top_gaps": [...],                    // TOP 3 prioritized gaps
  "course_recommendations": [...],
  "career_roadmap": {
    "stages": [
      { "stage": 1, "focus": "Kubernetes",
        "duration_weeks": 4, "skills_acquired": ["Docker", "K8s"],
        "milestones": [{"week": 1, "milestone": "..."}] }
    ],
    "total_weeks": 12, "total_hours": 40,
    "summary": "Lộ trình học trong 12 tuần..."
  },
  "cv_parsed": {...}
}
```

#### `GET /analysis/user/history`
```json
Query: ?limit=20
Response: [{ "id": "uuid", "match_score": 72, "created_at": "..." }]
```

#### `GET /analysis/market-fit`
```json
Response: {
  "matched_jobs": 5,
  "market_fit_pct": 72,
  "total_jobs": 1420,
  "courses": [...]               // Forwarded from latest analysis
}
```

#### `POST /analysis/feedback` (Spec 2.1 — Feedback Loop)
```json
Request: {
  "analysis_id": "uuid",
  "rating": 4,                  // 1-5
  "is_accurate": true,
  "missing_skills": ["Docker"],
  "comment": "Tốt nhưng thiếu..."
}
Response: { "message": "Feedback submitted", "feedback_id": "uuid" }
```

#### `GET /analysis/user/feedback-history`
```json
Response: [{ "id": "uuid", "rating": 4, "is_accurate": true, "comment": "..." }]
```

#### `POST /analysis/simulate` (Spec 1.11 — Career Simulation)
```json
Request: {
  "cv_id": "uuid",
  "selected_course_ids": ["uuid1", "uuid2", "uuid3"],
  "job_id": "uuid" | null
}
Response: {
  "virtual_skills_gained": ["Docker", "K8s", "AWS"],
  "estimated_duration_hours": 40,
  "estimated_duration_weeks": 4,
  "career_roadmap": { ... },
  "method": "llm_synthesized"
}
```

---

### 2.5 Recommender Service (`services/recommender_service/main.py`)

> Port: `:8000` | Gateway prefix: `/recommend/`
> **Admin:** `X-Is-Admin: true` header (for admin-only routes)

#### `POST /recommend/courses`
```json
Request: {
  "gap_skills": [
    { "skill_name": "Kubernetes", "target_level": "Mid-level",
      "gap_type": "MISSING", "severity": "HIGH" }
  ]
}
Response: [
  {
    "id": "course_uuid",
    "title": "Docker & Kubernetes: The Practical Guide",
    "platform": "Coursera",
    "level": "Intermediate",
    "provider": "Academind",
    "duration_hours": 23,
    "is_certification": false,
    "cost_usd": 12.0,
    "rank_score": 0.847,
    "similarity": 0.82,
    "gap_skill": "Kubernetes",
    "gap_severity": "HIGH"
  }
]
```

#### `GET /recommend/trending-skills`
```json
Query: ?days=30&limit=20
Response: [
  { "skill_name": "Python", "job_count": 342, "avg_min_salary_vnd": 20000000,
    "roles": ["Data Engineer", "Backend Dev"] }
]
```

#### `GET /recommend/admin/courses`
```json
Query: ?limit=20&offset=0&q=kubernetes
Response: {
  "items": [...], "total": 300, "limit": 20, "offset": 0,
  "page": 1, "pages": 15
}
```

#### `POST /recommend/admin/courses`
```json
Request: {
  "title": "Kubernetes Masterclass",
  "url": "https://coursera.org/...",
  "platform": "Coursera",
  "level": "Intermediate",
  "provider": "Google Cloud",
  "duration_hours": 40,
  "is_certification": true,
  "cost_usd": 49.0,
  "tags": ["Kubernetes", "Docker", "DevOps"],
  "skills_raw": ["K8s", "Container", "Orchestration"],
  "modules": ["Intro", "Pods", "Services", "Deployments"]
}
Response: { ... }  // Created course with auto-generated vector embedding
```

#### `DELETE /recommend/admin/courses/{course_id}`
```json
Response: { "message": "Deleted successfully" }
```

---

## 3. Database Schema

### 3.1 Entity-Relationship Diagram

```
users
  ├── id (PK UUID)
  ├── email (unique)
  ├── hashed_password
  ├── full_name
  ├── is_admin
  ├── last_analysis_id (FK → user_analysis.id)
  │
  ▼
user_cvs
  ├── id (PK UUID)
  ├── user_id (FK → users.id)
  ├── file_id (MinIO key)
  ├── full_name, summary, raw_text (OCR output)
  ├── cv_parsed_json (JSONB)        ← Structured CV data (v3)
  ├── cv_parsed_at
  ├── status: processing | completed | failed
  └── file_hash (SHA256, dedup)
         │
         ▼
  user_skill_profiles
    ├── id (PK UUID)
    ├── user_id, cv_id (FK → user_cvs.id)
    ├── skill_id (FK → skills.id)
    ├── years_exp, level, last_used_year
    ├── vector (1536)
    └── confidence_score, source
         │
         ▼
  user_work_experiences
  user_education
  user_certifications

jobs
  ├── id (PK UUID)
  ├── source_id (unique — from scraping/import)
  ├── title_raw, company_name, location_raw
  ├── raw_text                      ← Full JD text
  ├── min/max_salary_vnd
  ├── required_exp_years
  ├── vector (1536)                  ← pgvector
  ├── extracted_requirements_json    ← PRE-EXTRACTED requirements (JSONB)
  │     [
  │       { "type": "skill", "skill": "Python", "target_level": "Senior" },
  │       { "type": "group", "group_name": "Frontend", "strategy": "exclusive",
  │         "skills": [ { "skill": "ReactJS", ... }, ... ] }
  │     ]
  └── skills_required → job_skill_requirement (M:N via join table)

skills
  ├── id (PK UUID)
  ├── name (unique)
  ├── category
  ├── parent_skill_id (self-ref FK)
  └── vector (1536)

courses
  ├── id (PK UUID)
  ├── title, description
  ├── source_platform, source_id, external_uuid
  ├── provider, platform, url
  ├── level (Beginner|Intermediate|Advanced)
  ├── is_certification, duration_hours, cost_usd
  ├── languages (JSONB)
  ├── tags (ARRAY[text])            ← ["Docker", "Kubernetes", "DevOps"]
  ├── skills_raw (JSONB)           ← ["K8s", "Container"]
  ├── modules (JSONB)               ← ["Intro to K8s", "Pods", "Services"]
  ├── outcomes (JSONB)
  ├── embedding_context (Text)       ← Rich text for vector
  └── vector (1536)                  ← pgvector

user_analysis
  ├── id (PK UUID)
  ├── user_id (FK → users.id)
  ├── cv_id (FK → user_cvs.id)
  ├── job_id (FK → jobs.id, nullable)
  ├── match_score (float)
  ├── result_json (JSONB)           ← Full report (gap + courses + roadmap)
  └── created_at

user_feedback
  ├── id (PK UUID)
  ├── user_id, analysis_id
  ├── rating (1-5), is_accurate
  ├── missing_skills (JSONB)
  └── comment
```

---

## 4. Gap Analysis Pipeline (v3 — LangGraph)

### 4.1 Full Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CELERY TASK ENTRY                                 │
│         worker/tasks/analysis_tasks.py                              │
│         run_gap_analysis(user_id, cv_id, job_id?, jd_text?)         │
└──────────────┬──────────────────────────────────────────────────────┘
               │
     ┌─────────▼──────────────────────────────────────────┐
     │  [STEP 1] Validate CV                               │
     │  Query UserCV → check status == "completed"         │
     │  Load cv_parsed_json from DB                        │
     └─────────┬──────────────────────────────────────────┘
               │ cv_parsed_json OK
     ┌─────────▼──────────────────────────────────────────┐
     │  [STEP 2] Resolve JD (3-path cascade)              │
     │                                                   │
     │  Path A: job_id provided  ──→ query Job.extracted_requirements_json │
     │                          ──→ jd_text = job.raw_text              │
     │  Path B: jd_text provided ──→ use as-is                       │
     │  Path C: neither ────────────→ infer from CV via LLM             │
     └─────────┬──────────────────────────────────────────┘
               │
     ┌─────────▼──────────────────────────────────────────┐
     │  [STEP 3] Run Gap Analysis (v3 or Legacy)           │
     │  USE_LLM_GAP_AGENT=true → run_gap_analysis_v3()      │
     │  USE_LLM_GAP_AGENT=false → calculate_gap_v2()       │
     └───────────────────┬──────────────────────────────────┘
                         │ LangGraph async pipeline
     ┌───────────────────▼──────────────────────────────────┐
     │         LANGGRAPH PIPELINE (gap_v3)                  │
     │         orchestrator.py                              │
     │                                                   │
     │  ┌─────────────┐    ┌──────────────────┐           │
     │  │  load_cv    │───▶│  gap_analysis    │           │
     │  │ (load from  │    │  (2 LLM calls    │           │
     │  │  DB)       │    │  total: PATH A/B) │           │
     │  └─────────────┘    └────────┬─────────┘           │
     │                              │                     │
     │            ┌─────────────────▼─────────┐          │
     │            │  course_agent              │          │
     │            │  • vector search (pgvector) │          │
     │            │  • unified LLM call       │          │
     │            │    (courses + roadmap)     │          │
     │            └─────────────┬──────────────┘          │
     │                          │                       │
     │            ┌─────────────▼──────────────┐          │
     │            │  roadmap (pass-through)    │          │
     │            │  (roadmap already built   │          │
     │            │   in course_agent)       │          │
     │            └─────────────┬──────────────┘          │
     │                          │                       │
     │            ┌─────────────▼──────────────┐          │
     │            │  finalize                  │          │
     │            │  • merge final_report     │          │
     │            │  • cache to Redis        │          │
     │            │  • persist UserAnalysis │          │
     │            └─────────────┬──────────────┘          │
     └─────────────────────────┼───────────────────────────┘
                               │ final_report dict
     ┌─────────────────────────▼───────────────────────────┐
     │  [STEP 4] Persist to DB                          │
     │  UserAnalysis(result_json=final_report)         │
     │  User.last_analysis_id = new_analysis.id        │
     └──────────────────────────────────────────────────┘
```

### 4.2 LangGraph Node Details

#### Node 1: `load_cv_parsed_data_node`

```python
async def load_cv_parsed_data_node(state):
    """
    1. Query UserCV from DB
    2. If cv_parsed_json exists → use it
    3. If not → trigger CV parsing pipeline (v3) as fallback
    """
    # Input:  cv_id, db
    # Output: cv_parsed (CVParsedData), status

    if cv_parsed_json:
        return { "cv_parsed": cv_parsed_json, "status": "cv_loaded" }
    else:
        # Trigger cv_parsing_graph.run_cv_parsing_pipeline()
        return { "cv_parsed": parsed, "status": "cv_loaded" }
```

#### Node 2: `extract_jd_node` (DEPRECATED)

Skipped — logic merged into `gap_analysis_llm_node`.

#### Node 3: `gap_analysis_llm_node` ⭐ **LLM Call #1**

```
┌─────────────────────────────────────────────────────────┐
│  PATH A: job_id → extracted_requirements_json exists     │
│  ───────────────────────────────────────────────────────│
│  pre_jd_requirements = job.extracted_requirements_json  │
│  → SKIP LLM extraction                                │
│  → _build_gap_only_prompt(cv_text, requirements)       │
│  → Single LLM call: Gap Analysis + top_gaps           │
│  LLM Output: { gap_analysis: { skill_gaps, top_gaps } │
└─────────────────────────────────────────────────────────┘
                         OR
┌─────────────────────────────────────────────────────────┐
│  PATH B: jd_text (paste) or no pre-extraction          │
│  ───────────────────────────────────────────────────────│
│  Redis cache check: gap_v3_combined:{cv_id}:{jd_hash}   │
│  Cache HIT → return cached result                       │
│  Cache MISS → _build_merged_gap_prompt(cv_text, jd_text)│
│  → Single LLM call: JD extract + Gap Analysis + top_gaps│
│  LLM Output: { jd_parsed, gap_analysis: { skill_gaps, │
│                top_gaps, strengths, weaknesses } }    │
└─────────────────────────────────────────────────────────┘
```

**Optimized Output Schema:**
```json
{
  "jd_parsed": {
    "job_title": "Senior Python Engineer",
    "requirements": [
      { "type": "skill", "skill": "Python", "target_level": "Senior",
        "years_required": 3, "is_mandatory": true, "importance_weight": 9 }
    ]
  },
  "gap_analysis": {
    "overall_match_pct": 72,
    "overall_assessment": "Bạn phù hợp ở mức khá...",
    "match_breakdown": { "Technical Skills": 68, "Experience": 75, "Soft Skills": 80 },
    "strengths": ["Python 5 năm kinh nghiệm"],
    "weaknesses": ["Thiếu Kubernetes"],
    "skill_gaps": [
      { "skill": "Kubernetes", "required_level": "Mid-level",
        "severity": "HIGH", "is_critical": true,
        "estimated_months": 3, "learning_path": "..." }
    ],
    "top_gaps": [TOP_3_gaps],          ← ← ← INLINE (no extra LLM call)
    "transferable_insights": ["..."]
  }
}
```

#### Node 4: `course_recommendation_llm_node` ⭐ **LLM Call #2**

```
Input:  top_gaps (from state), all_skill_gaps
                 │
        ┌────────▼─────────────────────────────┐
        │  Vector Search per gap (pgvector)   │
        │  3 gaps × 12 candidates = ~36      │
        │  SELECT: id, title, level, provider, │
        │          tags, skills_raw, modules, │
        │          is_certification, sim, ... │
        └────────┬─────────────────────────────┘
                 │ all_candidates (~36)
        ┌────────▼──────────────────────────────────────────┐
        │  Unified LLM Call (1 call, ALL gaps at once)       │
        │  _llm_select_courses_and_roadmap_unified()        │
        │                                                   │
        │  Prompt includes:                                 │
        │    • All gaps with required_level, severity        │
        │    • All candidates with: title, level, tags,      │
        │      skills_raw, modules, cert, sim, cost           │
        │                                                   │
        │  Tasks:                                           │
        │    1. Select best courses (cert > level > free)   │
        │    2. Build roadmap (stages, milestones)          │
        │                                                   │
        │  Output:                                          │
        │    { selected_courses: [...], career_roadmap: {} }│
        └────────┬──────────────────────────────────────────┘
                 │
        ┌────────▼────────────────────────────────────┐
        │  Deduplicate + Rank (severity × formula)      │
        │  rank = sev × (sim×0.6 + cert×0.15 +         │
        │           level_bonus + hard_match×0.1)        │
        └──────────────────────────────────────────────┘
```

#### Node 5: `roadmap_synthesis_node` (PASS-THROUGH)

Roadmap đã được build trong Node 4 → chỉ pass qua.

#### Node 6: `finalize_report_node`

```python
final_report = {
    "overall_match_pct": float,
    "overall_assessment": str,
    "strengths": [...],
    "weaknesses": [...],
    "skill_gaps": [...],
    "top_gaps": [...],
    "match_breakdown": {...},
    "transferable_insights": [...],
    "jd_context": str,
    "course_recommendations": [
        {
            "course_id": "uuid", "title": "...",
            "platform": "Coursera", "level": "Intermediate",
            "provider": "Academind",
            "duration_hours": 23.0, "is_certification": false,
            "cost_usd": 12.0,
            "tags": ["Docker", "K8s"],
            "skills_raw": ["Container"],
            "similarity": 0.82,
            "rank_score": 0.847,
            "gap_skill": "Kubernetes",
            "gap_severity": "HIGH",
            "gap_estimated_months": 3,
            "gap_learning_path": "...",
            "is_critical": true,
            "selection_reason": "..."
        }
    ],
    "career_roadmap": {
        "stages": [...],
        "total_weeks": 12,
        "total_hours": 40,
        "summary": "..."
    },
    "cv_parsed": {...},
    "notes": [
        "Analysis Method: LLM Holistic v3 Optimized (2 LLM calls total)",
        "CV parsed=Trần Văn A",
        "JD context=Senior Python Engineer @ FPT Software",
        "Courses recommended=5"
    ]
}
```

---

## 5. Course Recommendation System

### 5.1 Vector Search Flow

```
gap_skill = "Kubernetes"
target_level = "Mid-level"
                  │
                  ▼
         ┌──────────────────┐
         │ Build search_text  │
         │ "Kubernetes Mid-level course tutorial"
         │ get_embedding(search_text) → 1536-dim vector
         └────────┬───────────┘
                  │ pgvector query
                  ▼
┌─────────────────────────────────────────────┐
│  SQL: SELECT ... WHERE vector <=> :vec > 0.60│
│  ORDER BY similarity DESC LIMIT 12            │
│                                             │
│  Columns fetched:                            │
│    id, title, platform, url, level,          │
│    provider, duration_hours, is_certification, │
│    cost_usd, tags,                          │
│    skills_raw, modules, outcomes,            │ ← ← FETCHED for ranking
│    embedding_context, similarity            │
└─────────────┬───────────────────────────────┘
              │ ~12 courses
              ▼
     ┌──────────────────┐
     │ Deduplicate      │
     │ + Rank formula   │
     └────────┬─────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  Rank Formula (optimized):                  │
│                                             │
│  rank = severity_w × (                    │
│      sim × 0.6    ← vector similarity      │
│    + cert × 0.15  ← certification bonus    │
│    + level × 0.05 ← level match bonus     │
│    + hard × 0.10  ← hard match bonus      │
│  )                                         │
│                                             │
│  Hard Match Bonus:                          │
│    skill_name found in tags/skills_raw/modules │
│    (substring match, +0.1)                  │
│                                             │
│  Level Match:                                │
│    LevelMapper.to_score(level) → 1-5        │
│    diff = course_score - target_score        │
│    diff >= 0 → +0.05 (meets or exceeds)   │
│    diff < 0  → diff × 0.1 (penalize)      │
└─────────────┬───────────────────────────────┘
              │ ranked courses
              ▼
      Top courses returned
      + sent to LLM for final selection
```

### 5.2 LevelMapper

```python
# backend/shared/level_mapper.py
LevelMapper.LEVEL_MAP = {
    "beginner": 1, "basic": 1, "intern": 1, "novice": 1,
    "junior": 2, "low": 2,
    "middle": 3, "intermediate": 3, "mid": 3, "mid-level": 3,
    "senior": 4, "advanced": 4, "high": 4,
    "expert": 5, "lead": 5, "specialist": 5
}
LevelMapper.calculate_gap(user_level, required_level)
# → Returns: required - user (positive = gap)
```

---

## 6. CV Parsing Pipeline (v3)

```
Upload CV File
    │
    ▼
Celery Task: run_cv_parsing_v3_task
    │
    ├── Save file to /app/data/cv_uploads/{cv_id}.{ext}
    ├── Create UserCV(status="processing")
    └── commit
    │
    ▼
LangGraph: cv_parsing_graph.py
    │
    ├── Node 1: extract_raw_text
    │     • Read file (PDF/DOCX)
    │     • OCR if needed (pdfminer.six / pytesseract)
    │     • PII masking (mask_pii)
    │     • Cache raw_text in DB
    │
    ├── Node 2: parse_cv_llm_node
    │     • LLM: GPT-4o-mini → JSON
    │     • Output schema: skills, work_history, education,
    │       certifications, seniority, experience_years_total
    │     • PII masking on all text fields
    │
    ├── Node 3: persist_cv_node
    │     • UserCV.cv_parsed_json = parsed_data
    │     • UserCV.status = "completed"
    │     • UserCV.full_name = parsed.full_name
    │     • commit
    │
    └── Return: cv_parsed dict
```

---

## 7. JD Extraction (RequirementRetriever — 4-Layer Cache)

```
jd_text input
    │
    ├── Layer 1: Exact Hash Match
    │     sha256(jd_text)[:16] → source_id = "cache_{hash}"
    │     Query: SELECT ... WHERE source_id = "cache_{hash}"
    │     ✓ HIT → return extracted_requirements_json
    │     ✗ DIRTY CACHE (legacy 2-year defaults) → re-extract
    │
    ├── Layer 2: Keyword FTS Match
    │     Query: SELECT ... WHERE to_tsvector(raw_text) @@ plainto_tsquery(jd_text)
    │     ✓ HIT (rank > 0.5) → return extracted_requirements_json
    │
    ├── Layer 3: Semantic Vector Match
    │     get_embedding(jd_text) → 1536-dim
    │     Query: WHERE 1 - (vector <=> :vec) > 0.97
    │     ✓ HIT → return extracted_requirements_json
    │
    └── Layer 4: AI Extraction (LLM)
          Prompt: "Extract technical skills from JD..."
          Output: { requirements: [...] }
          → Save to cache Layer 1 (source_id = cache_{hash})
          → return requirements
```

---

## 8. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `USE_LLM_GAP_AGENT` | `true` | v3 LangGraph vs Legacy engine |
| `GAP_LLM_MODEL` | `gpt-4o-mini` | LLM model for gap analysis |
| `GAP_VECTOR_SIM_THRESHOLD` | `0.60` | Min pgvector similarity |
| `GAP_REDIS_CACHE` | `true` | Enable Redis result caching |
| `GAP_CACHE_TTL` | `1800` | Cache TTL (30 min) |
| `JD_EXTRACT_CACHE_TTL` | `3600` | JD extraction cache (1h) |
| `GAP_PII_MASKING` | `true` | Mask personal info in logs |

---

## 9. LLM Call Summary

| Pipeline | LLM Call | Purpose |
|---|---|---|
| **v3 Gap** (Path A) | `gap_analysis_from_requirements` | Gap analysis using pre-extracted requirements |
| **v3 Gap** (Path B) | `gap_analysis_combined` | JD extract + Gap analysis (1 call) |
| **v3 Course** | `select_courses_and_roadmap_unified` | Select courses + Build roadmap (1 call) |
| **v3 CV Parsing** | `parse_cv_structured` | Extract structured CV from raw text |
| **Legacy Gap** | `calculate_gap_v2` | Vector similarity + scoring |
| **JD Extract** | `extract_requirements_from_text` | Extract requirements from JD text |
| **JD Infer** | `infer_market_requirements` | Infer requirements from CV skills |
| **Course Embedding** | `text-embedding-3-small` | Course vector embedding (non-LLM API) |

---

## 10. Feature Flags

| Flag | Default | Description |
|---|---|---|
| `USE_LLM_GAP_AGENT` | `true` | Use LangGraph v3 vs Legacy |
| `USE_LLM_GAP_AGENT_V3` | `true` | CV parsing v3 vs legacy |
| `GAP_REDIS_CACHE` | `true` | Cache gap analysis results |
| `GAP_PII_MASKING` | `true` | Mask PII in logs |
| `JD_USE_VECTOR_SEARCH` | `true` | Use pgvector for JD search |

---

## 11. Cached Redis Keys

| Key Pattern | TTL | Content |
|---|---|---|
| `gap_v3_combined:{cv_id}:{jd_hash}` | 30 min | Combined gap analysis result |
| `gap:{cv_id}:{job_id}` | 30 min | Final report (from finalize) |
| `jd_extract:{text_hash}` | 1h | Extracted JD requirements |

---

## 12. Project Structure

```
backend/
├── gateway/
│   ├── main.py                  # FastAPI reverse proxy + auth middleware
│   └── auth_middleware.py       # JWT validation, inject X-User-ID
│
├── services/
│   ├── auth_service/main.py     # Auth: login, register
│   ├── cv_service/main.py       # CV: upload, parse, skills CRUD
│   ├── jd_service/main.py      # JD: search, job management
│   ├── analysis_service/
│   │   ├── main.py             # Analysis: gap, feedback, simulate
│   │   ├── gap_calculator.py   # GapCalculator + RequirementRetriever
│   │   └── engine/
│   │       ├── retriever.py    # 4-layer JD requirement extractor
│   │       ├── matcher.py      # Skill name normalization + alias
│   │       ├── scorer.py       # Legacy gap scoring
│   │       └── advanced_gap_engine.py  # Legacy vector matching
│   └── recommender_service/
│       └── main.py             # Course CRUD + /recommend/courses
│
├── worker/
│   ├── celery_app.py           # Celery app config
│   ├── tasks/
│   │   ├── analysis_tasks.py   # run_gap_analysis Celery task
│   │   ├── cv_parsing_v3_task.py
│   │   └── crawler_tasks.py
│   └── langgraph_agents/gap_v3/
│       ├── orchestrator.py     # LangGraph entry + graph definition
│       ├── states.py           # TypedDict state schemas
│       ├── config.py           # Feature flags + thresholds
│       └── nodes/
│           ├── gap_nodes.py     # load_cv, gap_analysis (PATH A/B)
│           ├── course_nodes.py  # course_agent + unified LLM + vector search
│           ├── finalize_nodes.py # finalize + roadmap (pass-through)
│           └── cv_parsing_nodes.py
│
├── shared/
│   ├── models.py               # SQLAlchemy models (all tables)
│   ├── database.py             # get_db session, engine
│   ├── redis_client.py         # Redis result_cache
│   ├── llm_utils.py           # get_embedding, get_chat_completion
│   ├── level_mapper.py        # LevelMapper (1-5 scale)
│   ├── taxonomy_service.py    # Neo4j skill taxonomy
│   ├── schemas.py             # Pydantic schemas
│   └── scrapers/
│       └── topcv.py           # TopCV job scraper
│
├── scripts/
│   ├── seed_coursera_300.py  # Seed 300 Coursera courses + embeddings
│   ├── seed_data.py           # Legacy seed
│   └── setup_db.py            # DB migration
│
└── tests/
    ├── test_gap_v3_integration.py
    └── test_gap_v3_formatters.py
```
