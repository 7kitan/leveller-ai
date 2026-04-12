# 🚀 Backend Blueprint – AI Career Advisor (Microservice Architecture)

> Cập nhật lần 2: Bổ sung **Course Schema + course_vectors**, **Multi-stage Gap Formula**, **Recommender I/O chi tiết**, **Simulation output**, **Feedback Loop**, **Skill Trend API**, và **PII Masking flow** theo `architecture.md` + `feature_overview.md`.

---

## User Review Required

> [!IMPORTANT]
> Đây là phiên bản Blueprint đã được tái phân tích hoàn chỉnh. Vui lòng **Approve** để bắt đầu giai đoạn khởi tạo code và cấu trúc thư mục thực tế.

---

## 1. Tổng Quan Microservice

Kiến trúc chia thành **6 service** hoàn toàn độc lập, giao tiếp với nhau qua API Gateway và Redis Event Bus.

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                          │
│          Upload CV (PDF/ảnh) | Import JD (text/URL)            │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP Request
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  API Gateway (FastAPI)                          │
│     Route + Auth Middleware + Rate Limit + Request Log         │
└──────┬────────┬────────┬─────────┬───────────────┬─────────────┘
       │        │        │         │               │
       ▼        ▼        ▼         ▼               ▼
  ╔════════╗ ╔══════╗ ╔═══════╗ ╔══════════╗ ╔══════════════╗
  ║  Auth  ║ ║  CV  ║ ║  JD   ║ ║ Analysis ║ ║  Recommender ║
  ║Service ║ ║ SVC  ║ ║ SVC   ║ ║  Service ║ ║   Service    ║
  ╚════════╝ ╚══════╝ ╚═══════╝ ╚══════════╝ ╚══════════════╝
       │        │        │         │               │
       └────────┴────────┴─────────┴───────────────┘
                         │ Celery Tasks
                         ▼
              ╔═══════════════════╗
              ║   Redis (Multi)   ║
              ║ • Auth Cache      ║ ← Token JWT, Session
              ║ • Task Queue      ║ ← Celery Broker/Backend
              ║ • Result Cache    ║ ← Gap Score, Recommendations
              ╚═════════╤═════════╝
                        │
              ╔═════════▼═════════╗
              ║   Worker Pool     ║
              ║ (Celery + LangGraph) ║
              ╚═════════╤═════════╝
                        │
       ┌────────────────┴────────────────┐
       ▼                                 ▼
╔═══════════════╗               ╔════════════════╗
║  PostgreSQL   ║               ║     Neo4j      ║
║  + pgvector   ║               ║  Skill Graph   ║
║ (Data + Vec)  ║               ║  + Alias Map   ║
╚═══════════════╝               ╚════════════════╝
```

---

## 2. Vai Trò Redis (Multi-tier Cache)

Redis được dùng cho **3 mục đích tách biệt**, nên cấu hình **3 database index** riêng (db=0, 1, 2):

| Redis DB | Mục đích | TTL gợi ý | Key Pattern |
|---|---|---|---|
| `db=0` | **Auth Cache** – Lưu JWT Token đã xác thực, tránh mỗi request phải query PostgreSQL. | 15 phút | `auth:token:<token_hash>` → `user_id` |
| `db=1` | **Celery Broker + Backend** – Hàng đợi Task và kết quả task từ Worker. | Tự quản | `celery-task-meta-<task_id>` |
| `db=2` | **Result Cache** – Cache kết quả Gap Analysis, Market Match % nặng tính toán. | 30 phút | `gap:<user_id>:<job_id>` |

> [!TIP]
> Ở Phase 1 MVP, Auth Service xác thực token JWT bằng **Symmetric secret key** lưu trong `.env`. Redis db=0 sẽ cache `user_id + scopes` sau lần đầu giải mã, mọi request sau trong cùng session sẽ không cần re-decode JWT cũng không query DB → **giảm latency hiệu quả**.

---

## 3. Cấu Trúc Thư Mục (Microservice)

```text
career_advisor/
├── gateway/                        # API Gateway Service
│   ├── main.py                     # FastAPI entrypoint, route proxying
│   ├── middleware/
│   │   ├── auth_middleware.py      # Verify JWT + Redis Cache lookup
│   │   └── rate_limiter.py
│   └── Dockerfile
│
├── services/
│   ├── auth_service/               # Auth Service
│   │   ├── app/
│   │   │   ├── api/endpoints/      # /register, /login, /refresh, /logout
│   │   │   ├── models/user.py
│   │   │   ├── schemas/            # Token schema, User schema
│   │   │   └── core/
│   │   │       ├── jwt.py          # Tạo/Verify JWT
│   │   │       └── redis_cache.py  # Ghi cache token vào Redis db=0
│   │   └── Dockerfile
│   │
│   ├── cv_service/                 # CV Service
│   │   ├── app/
│   │   │   ├── api/endpoints/      # /upload, /status/:id, /list
│   │   │   ├── models/cv.py
│   │   │   ├── schemas/
│   │   │   └── storage/            # MinIO/S3 client
│   │   └── Dockerfile
│   │
│   ├── jd_service/                 # JD (Job Description) Service
│   │   ├── app/
│   │   │   ├── api/endpoints/      # /import/text, /import/url, /list, /:id
│   │   │   ├── models/job.py
│   │   │   └── schemas/
│   │   └── Dockerfile
│   │
│   ├── analysis_service/           # Analysis & Gap Service
│   │   ├── app/
│   │   │   ├── api/endpoints/      # /gap, /market-fit, /simulate
│   │   │   └── core/
│   │   │       └── gap_calculator.py
│   │   └── Dockerfile
│   │
│   └── recommender_service/        # Course Recommendation Service
│       ├── app/
│       │   └── api/endpoints/      # /courses, /roadmap
│       └── Dockerfile
│
├── worker/                         # Shared Async Worker
│   ├── celery_app.py               # Celery setup (Broker: Redis db=1)
│   ├── tasks/
│   │   ├── parse_cv_task.py        # Gọi OCR → LLM → Neo4j → PG
│   │   └── parse_jd_task.py        # Gọi LLM → Neo4j → PG → pgvector
│   └── langgraph_agents/
│       ├── nodes/
│       │   ├── extract_node.py     # PDF/Text extraction
│       │   ├── llm_parse_node.py   # LLM Structured Output parsing
│       │   ├── neo4j_normalize_node.py  # Alias → Canonical skill
│       │   ├── embed_node.py       # Generate + upsert vector (pgvector)
│       │   └── gap_node.py         # Compute gap scores
│       └── graph.py                # LangGraph state machine
│
├── shared/                         # Shared libs dùng chung qua các service
│   ├── db/
│   │   ├── postgres.py             # SQLAlchemy engine factory
│   │   └── neo4j.py                # Neo4j driver singleton
│   ├── redis_client.py             # Redis connection pool
│   └── models/                     # Shared Pydantic schemas
│
└── docker-compose.yml              # Toàn bộ hạ tầng
    # Gồm: postgres, neo4j, redis, minio,
    #       gateway, auth-svc, cv-svc, jd-svc,
    #       analysis-svc, recommender-svc, worker
```

---

## 4. API Endpoints Đầy Đủ (Theo Service)

### 🔐 Auth Service – `http://auth-svc:8001`

| Method | Path | Mô tả | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Đăng ký tài khoản mới | ❌ |
| `POST` | `/auth/login` | Đăng nhập, nhận JWT Access + Refresh Token | ❌ |
| `POST` | `/auth/refresh` | Làm mới Access Token bằng Refresh Token | ❌ |
| `POST` | `/auth/logout` | Xóa cache token khỏi Redis | ✅ |
| `GET` | `/auth/me` | Lấy thông tin user hiện tại từ token | ✅ |

**Login Input / Output:**
```json
// POST /auth/login
// Input:
{ "email": "user@example.com", "password": "secret123" }

// Output:
{
  "access_token": "eyJhbGciOiJI...",
  "refresh_token": "eyJhbGci...",
  "expires_in": 900
}
```

---

### 📄 CV Service – `http://cv-svc:8002`

> [!NOTE]
> CV Upload hỗ trợ cả **PDF** và **ảnh (JPG/PNG)**. File được lưu vào **MinIO/S3**. Sau khi upload xong, Task `parse_cv_task` được đẩy vào Redis Queue.

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/cv/upload` | Upload file CV (multipart form-data) |
| `GET` | `/cv/status/{task_id}` | Kiểm tra trạng thái xử lý CV |
| `GET` | `/cv/list` | Danh sách CV của user đang đăng nhập |
| `GET` | `/cv/{cv_id}` | Kết quả CV đã phân tích |
| `DELETE` | `/cv/{cv_id}` | Xóa CV (PII compliance) |

**Upload Input / Output:**
```json
// POST /cv/upload  (multipart/form-data)
// Form fields:
{   "file": <binary .pdf hoặc .jpg>,
    "label": "CV Backend 2025"          // Optional
}

// Output (Task được tạo trong Redis Queue):
{
  "cv_id": "cv_abc123",
  "status": "processing",
  "task_id": "celery-task-xyz789",
  "message": "CV đang được xử lý, kiểm tra lại sau 30 giây"
}
```

---

### 📋 JD Service – `http://jd-svc:8003`

> Người dùng có thể **paste thẳng text JD** vào UI, hoặc nhập URL. Không bắt buộc phải có tài khoản để import (Public feature).

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/jd/import/text` | Import JD bằng văn bản thô paste vào |
| `POST` | `/jd/import/url` | Import JD bằng URL (hệ thống tự crawl) |
| `GET` | `/jd/status/{task_id}` | Kiểm tra trạng thái phân tích JD |
| `GET` | `/jd/list` | Danh sách JD trong hệ thống (Market data) |
| `GET` | `/jd/{job_id}` | Chi tiết JD đã phân tích |

**Import Text Input / Output:**
```json
// POST /jd/import/text
// Input:
{
  "raw_text": "Tuyển Fullstack NodeJS, yêu cầu 3 năm kinh nghiệm...",
  "source_label": "TopCV - Import thủ công"  // Optional
}

// Output:
{
  "job_id": "job_def456",
  "status": "processing",
  "task_id": "celery-task-parse-jd-101"
}
```

---

### 🧠 Analysis Service – `http://analysis-svc:8004`

| Method | Path | Mô tả | Cache |
|---|---|---|---|
| `POST` | `/analysis/gap` | Tính Gap giữa CV user và một JD cụ thể | Redis 30m |
| `GET` | `/analysis/market-fit/{cv_id}` | % phù hợp với toàn bộ thị trường JD hiện tại | Redis 30m |
| `POST` | `/analysis/simulate` | Mô phỏng lộ trình nghề nghiệp theo tháng | ❌ |

**Gap Analysis Input / Output:**
```json
// POST /analysis/gap
// Input:
{ "cv_id": "cv_abc123", "job_id": "job_def456" }

// Output (cached tại Redis db=2 với key gap:<cv_id>:<job_id>):
{
  "overall_match_pct": 72,
  "skill_match_pct": 85,
  "experience_match_pct": 60,
  "breakdown": {
    "met": [
      { "skill": "Node.js", "your_exp": 3, "required_exp": 2 }
    ],
    "gap": [
      { "skill": "Team Leadership", "your_exp": 0, "required_exp": 1, "weight": 4 },
      { "skill": "Docker", "your_exp": 0, "required_exp": null, "weight": 2 }
    ]
  },
  "insight": "Bạn đủ kỹ năng kỹ thuật. Điểm thiếu là Leadership và DevOps cơ bản."
}
```

**Market Fit Output:**
```json
// GET /analysis/market-fit/cv_abc123
{
  "total_jobs_in_db": 120,
  "jobs_above_70pct_match": 45,
  "market_fit_pct": 37,   // 45/120 = 37% jobs trên thị trường hiện tại phù hợp
  "top_matching_roles": ["Backend Developer", "Fullstack Developer"],
  "emerging_skills_you_lack": ["Docker", "Kubernetes", "AWS Lambda"]
}
```

---

### 🎓 Recommender Service – `http://recommender-svc:8005`

| Method | Path | Mô tả | Cache |
|---|---|---|---|
| `POST` | `/recommend/courses` | Gợi ý khóa học theo danh sách skill gap | Redis 1h |
| `GET` | `/recommend/roadmap/{cv_id}` | Lộ trình học cá nhân hóa (theo tháng) | ❌ |
| `GET` | `/recommend/trending-skills` | Kỹ năng đang nổi bật trên thị trường JD | Redis 6h |

---

## 5. Database Schema Đầy Đủ (PostgreSQL)

### 5.0 Bảng `jobs` (Job / JD Storage) ♥ QUAN TRỌNG

> [!IMPORTANT]
> Bảng chính lưu trữ JD. Cần đủ cột để hỗ trợ **filter** lương / địa điểm, **Hybrid Search** pgvector, và **trạng thái active/deactive** cho admin quản lý.

```sql
CREATE TABLE jobs (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Nhận diện nguồn (Chống duplicate, tra cứu nhanh)
  source_id                   VARCHAR(100) UNIQUE NOT NULL,
  -- Format: "<platform>_<platform_job_id>"
  -- VD: "topcv_2119168" | "linkedin_987654" | "manual_uuid"
  -- Đây là natural key để check trung thước khi crawl lại

  -- Thông tin cơ bản
  title_raw                   TEXT NOT NULL,        -- Tiêu đề gốc từ JD
  title_category              VARCHAR(100),         -- "Fullstack Developer" (LLM parse)
  domain_role                 VARCHAR(100),         -- "Team Lead", "Junior Dev"...
  company_name                VARCHAR(255),
  source_url                  TEXT,                 -- TopCV / LinkedIn URL gốc
  source_label                VARCHAR(100),         -- "topcv" | "linkedin" | "manual"
  raw_text                    TEXT,                 -- Nội dung JD thô trước parse

  -- Tài chính & kinh nghiệm (Phục vụ filter nhanh bằng SQL)
  min_salary_vnd              BIGINT,               -- Có giá trị cụ thể nếu JD nêu rõ
  max_salary_vnd              BIGINT,               -- NULL = Thỏa thuận
  required_exp_years          FLOAT,                -- Số năm kinh nghiệm tổng
  employment_type             VARCHAR(50),          -- "full-time" | "part-time" | "remote"

  -- Địa điểm (Phục vụ filter theo khu vực)
  location_raw                TEXT,                 -- Text địa chỉ gốc từ JD
  location_normalized         VARCHAR(100),         -- "Hà Nội" | "Hồ Chí Minh" | "Remote"
  location_district           VARCHAR(100),         -- "Nam Từ Liêm" (chiết tiết hơn nếu cần)

  -- Trạng thái quản lý
  status                      VARCHAR(20) NOT NULL DEFAULT 'active',
  -- CHECK (status IN ('active', 'deactive', 'draft', 'processing', 'failed'))
  -- active     = Hiện thị trong kết quả tìm kiếm
  -- deactive   = Admin tắt, không xuất hiện trong search
  -- draft      = Đang chờ dàn xết lý
  -- processing = Celery task đang chạy
  -- failed     = LLM parse lỗi, cần retry

  -- Vector Search (pgvector)
  embedding_context           TEXT,                 -- Chuỗi tóm tắt đưa và Embedding Model
  vector                      VECTOR(1536),         -- pgvector embedding của embedding_context

  -- Benefits quick-flag (Phục vụ filter UI)
  has_insurance               BOOLEAN DEFAULT FALSE,
  has_13th_month              BOOLEAN DEFAULT FALSE,
  remote_friendly             BOOLEAN DEFAULT FALSE,

  -- Metadata
  indexed_at                  TIMESTAMPTZ,          -- Khi nào vector được lưu xong
  created_at                  TIMESTAMPTZ DEFAULT NOW(),
  updated_at                  TIMESTAMPTZ DEFAULT NOW()
);
```

**Chiến lược Index cho bảng `jobs`:**
```sql
-- 0. source_id UNIQUE (Chống insert duplicate khi crawl lại - quan trọng nhất)
CREATE UNIQUE INDEX idx_jobs_source_id ON jobs (source_id);
-- Cách dùng: INSERT ... ON CONFLICT (source_id) DO UPDATE SET updated_at = NOW()
-- → Upsert an toàn, không cần query trước

-- 1. Vector search (Hybrid Search - quan trọng nhất)
CREATE INDEX idx_jobs_vector ON jobs USING hnsw (vector vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  -- Giải thích: m=16 đủ cho dataset < 100k jobs. tăng lên 32 khi scale.

-- 2. Filter theo status (Query đầu tiên ALWAYS phải WHERE status = 'active')
CREATE INDEX idx_jobs_status ON jobs (status);

-- 3. Filter theo khu vực (feature_overview 1.8: filter địa điểm)
CREATE INDEX idx_jobs_location ON jobs (location_normalized);

-- 4. Filter theo mức lương (feature_overview 1.8: filter salary)
CREATE INDEX idx_jobs_salary ON jobs (min_salary_vnd, max_salary_vnd);

-- 5. Composite: status + location + salary (Query phổ biến nhất từ UI filter)
CREATE INDEX idx_jobs_filter_combo ON jobs (status, location_normalized, min_salary_vnd);

-- 6. Tìm kiếm theo role (để trending-skills query ôi category)
CREATE INDEX idx_jobs_category ON jobs (title_category, status);

-- 7. Sắp xếp theo ngày đăng tin mới nhất
CREATE INDEX idx_jobs_created ON jobs (created_at DESC) WHERE status = 'active';
```

> [!NOTE]
> Index số 7 là **Partial Index** (WHERE status = 'active') – chỉ index những record thực sự được query, giảm 30-50% dung lượng index so với full index.

---

### 5.1 Bảng `courses` (Course Storage)

> [!IMPORTANT]
> Đây là bảng **còn thiếu hoàn toàn** trong plan cũ. Cần có để Recommender Service query và gợi ý khóa học dựa trên gap skills.

```sql
CREATE TABLE courses (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title         TEXT NOT NULL,
  description   TEXT,
  platform      VARCHAR(100),          -- "Udemy", "Coursera", "YouTube"...
  url           TEXT,
  language      VARCHAR(10),           -- "vi", "en"
  level         VARCHAR(20),           -- "Beginner", "Intermediate", "Advanced"
  duration_hours FLOAT,
  cost_usd      FLOAT DEFAULT 0,       -- 0 = free
  tags          TEXT[],                -- ["Docker", "DevOps", "CI/CD"]
  embedding_context TEXT,             -- Đoạn text để tạo vector
  vector        VECTOR(1536),          -- pgvector - embedding của embedding_context
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Index cho pgvector cosine similarity search
CREATE INDEX ON courses USING hnsw (vector vector_cosine_ops);

-- Index cho filter theo tags + level
CREATE INDEX ON courses USING GIN (tags);
-- Index theo level để filter Beginner/Advanced khi recommend
CREATE INDEX idx_courses_level ON courses (level);
-- Index theo platform để user chọn nguồn học
CREATE INDEX idx_courses_platform ON courses (platform);
```

### 5.2 Bảng `job_skill_requirement` (Đã có, bổ sung cột)

```sql
CREATE TABLE job_skill_requirement (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id           UUID REFERENCES jobs(id) ON DELETE CASCADE,
  skill_id         UUID REFERENCES skills(id),
  importance_weight INT  CHECK (importance_weight BETWEEN 1 AND 5),
  required_level   VARCHAR(20),   -- "Junior", "Middle", "Senior", "Expert"
  min_years_exp    FLOAT,         -- NULL = không chỉ định cụ thể
  is_mandatory     BOOLEAN DEFAULT TRUE
);

-- Index chính cho Gap Analysis Stage 1 (Hard Match)
CREATE INDEX idx_jsr_job_id ON job_skill_requirement (job_id);
CREATE INDEX idx_jsr_skill_id ON job_skill_requirement (skill_id);
-- Composite: query nhanh để tính tổng weight theo job
CREATE INDEX idx_jsr_job_weight ON job_skill_requirement (job_id, importance_weight DESC);
```

### 5.3 Bảng `user_feedback` (Feedback Loop)

```sql
CREATE TABLE user_feedback (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id),
  analysis_id     TEXT NOT NULL,   -- Format: "gap_<cv_id>_<job_id>"
  rating          INT CHECK (rating BETWEEN 1 AND 5),
  is_accurate     BOOLEAN,
  missing_skills  JSONB,           -- ["GraphQL", "Redis"]
  comment         TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.4 Bảng `skills` + `user_skill_profile`

```sql
CREATE TABLE skills (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR(200) NOT NULL UNIQUE,  -- Tên chuẩn (canonical)
  parent_skill_id UUID REFERENCES skills(id),   -- Hạng mục cha (Neo4j cũng lưu)
  category        VARCHAR(50),                   -- "Technology"|"Framework"|"DevOps"|"Soft Skill"
  vector          VECTOR(1536)                   -- Embedding của skill name (dùng cho Stage 2)
);

CREATE INDEX idx_skills_name      ON skills (name);           -- Lookup nhanh by name
CREATE INDEX idx_skills_category  ON skills (category);       -- Group by category
CREATE INDEX idx_skills_vector    ON skills USING hnsw (vector vector_cosine_ops); -- Stage 2


CREATE TABLE user_skill_profile (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id),
  skill_id        UUID REFERENCES skills(id),
  years_exp       FLOAT DEFAULT 0,
  level           VARCHAR(20),                   -- "Junior" | "Middle" | "Senior" | "Expert"
  confidence_score FLOAT DEFAULT 1.0,            -- 0–1: Độ tin cậy (1.0 = self-reported)
  source          VARCHAR(50) DEFAULT 'cv',      -- "cv" | "manual" | "test"
  cv_id           UUID,                          -- CV nào parse ra skill này
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index cho Gap Analysis Stage 1 (CRITICAL - query bất kỳ phân tích nào cũng JOIN bảng này)
CREATE INDEX idx_usp_user_id  ON user_skill_profile (user_id);
CREATE INDEX idx_usp_skill_id ON user_skill_profile (skill_id);
-- Composite để JOIN và lấy cả years_exp một lần
CREATE INDEX idx_usp_user_skill ON user_skill_profile (user_id, skill_id, years_exp);
```

### 5.5 Bảng `user_feedback`

```sql
CREATE TABLE user_feedback (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id),
  analysis_id     TEXT NOT NULL,
  rating          INT CHECK (rating BETWEEN 1 AND 5),
  is_accurate     BOOLEAN,
  missing_skills  JSONB,
  comment         TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Để lookup kết quả feedback theo user + chạy Feedback Loop aggregation
CREATE INDEX idx_feedback_user    ON user_feedback (user_id);
CREATE INDEX idx_feedback_created ON user_feedback (created_at DESC);
```

### 5.6 Tổng Hợp Index Chiến Lược (Query Pattern Analysis)

| Query Phổ Biến | Bảng dùng | Index sử dụng |
|---|---|---|
| Tìm jobs active theo khu vực + lương | `jobs` | `idx_jobs_filter_combo` |
| Vector search JD (Semantic Search) | `jobs` | `idx_jobs_vector` (HNSW) |
| Gap Analysis Stage 1 (Hard Match) | `user_skill_profile` × `job_skill_requirement` | `idx_usp_user_skill`, `idx_jsr_job_id` |
| Gap Analysis Stage 2 (Semantic skill) | `skills` | `idx_skills_vector` (HNSW) |
| Trending skills 30 ngày | `jobs` × `job_skill_requirement` | `idx_jobs_created`, `idx_jsr_job_id` |
| Recommend course theo skill | `courses` | HNSW vector + GIN tags + `idx_courses_level` |
| Market Fit (% JD phù hợp) | `jobs`, `job_skill_requirement` | `idx_jobs_status`, `idx_jsr_skill_id` |

### 5.7 SQL Mẫu - Các Query Thường Dùng

**1. Job Search với Hybrid Filter (Market + Filter UI):**
```sql
-- Tìm jobs active, tại Hà Nội, lương từ 20tr, kết hợp vector similarity
SELECT id, title_raw, min_salary_vnd, location_normalized,
       1 - (vector <=> $user_cv_vector) AS semantic_score
FROM jobs
WHERE status = 'active'
  AND location_normalized = 'Hà Nội'
  AND min_salary_vnd >= 20000000
ORDER BY semantic_score DESC
LIMIT 10;
```

**2. Market Fit % (Phần trăm Job phù hợp trên thị trường):**
```sql
-- Đếm bao nhiêu job user match được đủ weight
SELECT
  COUNT(*) FILTER (WHERE match_pct >= 70) AS matched_jobs,
  COUNT(*) AS total_jobs,
  ROUND(COUNT(*) FILTER (WHERE match_pct >= 70)::numeric / COUNT(*) * 100, 1) AS market_fit_pct
FROM (
  SELECT jsr.job_id,
    SUM(CASE WHEN usp.skill_id IS NOT NULL THEN jsr.importance_weight ELSE 0 END) * 100.0
    / SUM(jsr.importance_weight) AS match_pct
  FROM job_skill_requirement jsr
  JOIN jobs j ON j.id = jsr.job_id AND j.status = 'active'
  LEFT JOIN user_skill_profile usp ON usp.skill_id = jsr.skill_id AND usp.user_id = $user_id
  GROUP BY jsr.job_id
) sub;
```

**3. Trending Skills (30 ngày gần nhất):**
```sql
SELECT s.name, COUNT(DISTINCT jsr.job_id) AS job_count,
       AVG(j.min_salary_vnd) AS avg_salary
FROM job_skill_requirement jsr
JOIN jobs j      ON j.id = jsr.job_id AND j.status = 'active'
                AND j.created_at >= NOW() - INTERVAL '30 days'
JOIN skills s    ON s.id = jsr.skill_id
WHERE jsr.importance_weight >= 4   -- Chỉ lấy skill quan trọng
GROUP BY s.name
ORDER BY job_count DESC
LIMIT 20;
```

### 5.8 `cv_vectors` + `jd_vectors` + `course_vectors` (pgvector Collections)

| Collection | Stored in | Key Fields | Purpose |
|---|---|---|---|
| `cv_vectors` | Cột `vector` trong bảng `user_profiles` | cv_id, user_id | Semantic match CV vs JD |
| `jd_vectors` | Cột `vector` trong bảng `jobs` | job_id, filters (salary, location) | Hybrid search JD |
| `course_vectors` | Cột `vector` trong bảng `courses` | course_id, tags | Match skill gap → course |

---

## 6. Multi-stage Gap Analysis Formula

Đây là logic **cốt lõi** của `gap_calculator.py`, được chạy theo 4 giai đoạn tuần tự:

```text
GAP ANALYSIS PIPELINE (4 stages)

 Stage 1: HARD MATCH (SQL Query - Nhanh nhất)
 ─────────────────────────────────────────────
 So sánh trực tiếp skill_id từ user_skill_profile vs job_skill_requirement.
 → Kết quả: Danh sách skill PASS (matched) và skill FAIL (missing hoàn toàn)

 Stage 2: SEMANTIC MATCH (pgvector - Cho skill FAIL ở Stage 1)
 ──────────────────────────────────────────────────────────────
 Với mỗi skill user có, tính cosine similarity vs skill JD yêu cầu.
 Nếu similarity > 0.80 → coi là PARTIAL MATCH (không phải gap hoàn toàn)
 → VD: user có "ExpressJS" → so với "NestJS" → similarity 0.82 → cộng điểm một phần

 Stage 3: TRANSFERABLE SKILLS (Neo4j Graph Traversal)
 ──────────────────────────────────────────────────────
 Với skill thiếu còn lại, hỏi Neo4j: User có skill nào là Parent/Sibling của skill JD không?
 → VD: User biết "Python" → Neo4j biết Python BELONGS_TO Backend
        JD cần "FastAPI" → FastAPI BELONGS_TO Backend → Infer: User có nền học nhanh
 → Cộng điểm "transferability bonus"

 Stage 4: EXPERIENCE WEIGHTING
 ──────────────────────────────
 Với các skill đã PASS, kiểm tra số năm:
   Exp_penalty = max(0, (req_years - user_years) / req_years)
   → Trừ điểm nếu experience không đủ

FINAL SCORE FORMULA:
───────────────────
  Weighted_sum    = Σ (stage_score × importance_weight) cho từng skill
  Max_possible    = Σ (5 × importance_weight) cho tất cả skill JD
  overall_pct     = (Weighted_sum / Max_possible) × 100

  skill_pct       = % kỹ năng đáp ứng (Stage 1+2+3)
  experience_pct  = 100 - Σ(Exp_penalty × weight) / Max_possible × 100
  overall_match   = skill_pct × 0.6 + experience_pct × 0.4
```

> [!TIP]
> Con số `0.6` (skill) và `0.4` (experience) là trọng số mặc định. Sau khi có dữ liệu feedback thực tế (bảng `user_feedback`), hệ thống có thể **tự điều chỉnh trọng số** bằng cách phân tích correlation giữa rating người dùng và các chỉ số này.

---

## 7. JD Parsed Schema (LLM Structured Output)

Schema này là **đầu ra bắt buộc** từ `llm_parse_node.py` trong LangGraph. Sử dụng Pydantic để validate và ép kiểu trước khi lưu DB.

```json
{
  "general_metadata": {
    "title_raw": "Fullstack Team Lead (NodeJS / ReactJS) - 5 Năm Kinh Nghiệm",
    "title_category": "Fullstack Developer",
    "domain_role": "Team Lead",
    "min_salary_vnd": 30000000,
    "max_salary_vnd": null,
    "location_normalized": "Hà Nội",
    "required_general_experience_years": 5,
    "employment_type": "full-time",
    "embedding_context": "Vị trí Fullstack Team Lead NodeJS/ReactJS, cần thiết kế hệ thống, quản lý team, CI/CD, làm việc với khách hàng nước ngoài."
  },
  "skills_required": [
    {
      "skill_name_raw": "NodeJS",
      "skill_canonical": null,
      "category": "Technology",
      "importance_weight": 5,
      "min_years_exp": 5
    },
    {
      "skill_name_raw": "NestJS",
      "skill_canonical": null,
      "category": "Framework",
      "importance_weight": 4,
      "min_years_exp": null
    },
    {
      "skill_name_raw": "Team Leadership",
      "skill_canonical": null,
      "category": "Role",
      "importance_weight": 5,
      "min_years_exp": 1
    },
    {
      "skill_name_raw": "Docker",
      "skill_canonical": null,
      "category": "DevOps",
      "importance_weight": 3,
      "min_years_exp": null
    }
  ],
  "benefits_and_roi": {
    "has_insurance": true,
    "has_13th_month_salary": true,
    "has_hybrid_work": false,
    "remote_friendly": false
  }
}
```

> [!NOTE]
> `skill_canonical` ban đầu luôn là `null`. **Neo4j Normalize Node** sẽ điền vào dựa trên kết quả Cypher query alias map:
> `"NodeJS"` → lookup Neo4j → trả về `"Node.js"` → điền vào `skill_canonical`.

---

## 6. Luồng Xử Lý End-to-End

### 8.1 Luồng Upload CV (User tại Frontend) + PII Masking

```text
User chọn file PDF/ảnh tại UI
        ↓
POST /cv/upload (Gateway → CV Service)
        ↓
CV Service: Lưu file vào MinIO, tạo record cv_metadata (status=pending)
        ↓
Push Task: parse_cv_task(cv_id) → Redis Queue (db=1)
        ↓ (Async)
Worker: LangGraph Pipeline
  [1] extract_node: PDF → text hoặc ảnh → Chandra OCR 2 → text
  [2] pii_mask_node: Xóa/mask SĐT, Email, địa chỉ trước khi lưu  ← MỚI
       VD: "Bach - 0912345678" → "Bach - ***"
  [3] llm_parse_node: LLM → skills[], experience, education
  [4] neo4j_normalize_node: "nodejs" → "Node.js"
  [5] embed_node: Tạo vector từ CV summary → lưu pgvector
  [6] Update cv_metadata.status = "done"
        ↓
Frontend polling GET /cv/status/{task_id} → Hiển thị kết quả
```

### 8.2 Luồng Import JD Bằng Text (User tại Frontend)

```text
User paste text JD vào textarea tại UI
        ↓
POST /jd/import/text (Gateway → JD Service)
        ↓
JD Service: Tạo record job (status=pending), lưu raw_text
        ↓
Push Task: parse_jd_task(job_id) → Redis Queue (db=1)
        ↓ (Async)
Worker: LangGraph Pipeline
  [1] llm_parse_node: Trích xuất general_metadata + skills_required[]
  [2] neo4j_normalize_node: Chuẩn hóa skill_name → skill_canonical
  [3] PostgreSQL Insert: job_skill_requirement (từng skill + weight + exp)
  [4] embed_node: Tạo vector từ embedding_context → lưu pgvector
  [5] Update job.status = "indexed"
        ↓
Sẵn sàng cho Gap Analysis & Market Query
```

### 8.3 Luồng Gap Analysis → Recommend Courses (End-to-End)

```text
User nhấn "Phân tích" CV vs JD tại UI
        ↓
POST /analysis/gap  { cv_id, job_id }
        ↓
[Stage 1] Hard Match: SQL JOIN user_skill_profile + job_skill_requirement
[Stage 2] Semantic Match: pgvector cosine similarity cho skill FAIL
[Stage 3] Transferable: Neo4j graph traversal
[Stage 4] Exp Weighting: tính penalty theo year gap
        ↓
Cache kết quả → Redis db=2 (key: gap:<cv_id>:<job_id>, TTL 30m)
        ↓
Frontend render kết quả + nút "Gợi ý khóa học"
        ↓
POST /recommend/courses  { gap_skills: [...] }  ← Lấy từ output step trên
        ↓
Recommender: Với mỗi gap skill
  [1] Vector search: Tìm courses có embedding gần với skill_name (pgvector)
  [2] Filter: level phù hợp, cost, language
  [3] Rank: relevance_score × 0.5 + (1/duration) × 0.3 + (1/cost+1) × 0.2
        ↓
Trả về danh sách courses đã xếp hạng → Frontend hiển thị
```

### 8.4 Luồng Auth + Redis Cache

```text
User gửi request bất kỳ có JWT token
        ↓
Gateway Auth Middleware:
  [1] Check Redis db=0: key "auth:token:<hash(token)>"
      → HIT: Trả về user data ngay, KHÔNG gọi Auth Service
      → MISS: Gọi Auth Service /verify → Decode JWT
              → Lưu kết quả vào Redis db=0 (TTL 15 phút)
        ↓
Request được forward đến Service tương ứng (cv-svc, analysis-svc...)
```

---

## 7. Docker Compose Infrastructure

```yaml
services:
  postgres:    # PostgreSQL 15 + pgvector extension
  neo4j:       # Neo4j 5 – Skill Graph & Alias Map
  redis:       # Redis 7 – Auth Cache + Celery + Result Cache
  minio:       # S3-compatible object storage cho CV files
  gateway:     # API Gateway FastAPI :8000
  auth-svc:    # Auth Service :8001
  cv-svc:      # CV Service :8002
  jd-svc:      # JD Service :8003
  analysis-svc: # Analysis Service :8004
  recommender: # Recommender Service :8005
  worker:      # Celery Worker (shared)
```

---

## 8. Feature Coverage Matrix (feature_overview.md vs API)

| # | Chức Năng | Backend API | Status |
|---|---|---|---|
| 1.1 | Tải lên CV (PDF / ảnh) | `POST /cv/upload` | ✅ |
| 1.2 | Xử lý CV từ ảnh (OCR) + Cảnh báo | `extract_node` + `GET /cv/{cv_id}/parsed-result` → `is_ocr` | ✅ |
| 1.3 | Phân tích CV bằng AI | `llm_parse_node` trong Worker | ✅ |
| 1.4 | Chuẩn hóa kỹ năng | `neo4j_normalize_node` | ✅ |
| 1.5 | Suy luận kỹ năng từ Skill Graph | Neo4j BELONGS_TO traversal | ✅ |
| 1.6 | Phân tích JD (text / URL) | `POST /jd/import/text` + `POST /jd/import/url` | ✅ |
| 1.7 | So khớp kỹ năng thông minh (Semantic) | Gap Stage 2: pgvector cosine similarity | ✅ |
| 1.8 | Tìm kiếm nâng cao (lọc lương/địa điểm) | `POST /jd/search` *(thêm mục 10)* | ⚠️ Cần thêm |
| 1.9 | Phân tích Skill Gap | `POST /analysis/gap` | ✅ |
| 1.10 | Gợi ý khóa học | `POST /recommend/courses` | ✅ |
| 1.11 | Mô phỏng lộ trình nghề nghiệp | `POST /analysis/simulate` + `GET /recommend/roadmap` | ✅ |
| 2.1 | Thu thập phản hồi user | `POST /analysis/feedback` | ✅ |
| 2.2 | Cải thiện hệ thống theo phản hồi | Bảng `user_feedback` + Feedback Loop | ✅ |
| 3.1 | Bảo vệ PII | `pii_mask_node` trong LangGraph | ✅ |
| 3.2 | Minh bạch kết quả (cảnh báo OCR) | `GET /cv/{cv_id}/parsed-result` | ✅ |
| 4.1 | Xử lý nền (async) | Celery Worker + Redis Queue | ✅ |
| 4.2 | Quản lý tài khoản + lịch sử | `GET /analysis/history/{user_id}` | ✅ |
| 5.1 | Xu hướng kỹ năng thị trường | `GET /recommend/trending-skills` | ✅ |
| 5.2 | Thông tin nghề nghiệp (lương, vai trò) | market-fit + trending response | ⚠️ Cần mở rộng |

> [!WARNING]
> **Feature 1.8:** Cần bổ sung `POST /jd/search` vào JD Service (xem mục 10).
> **Feature 5.2:** Chưa có endpoint Salary Insight riêng theo role – có thể mở rộng trending-skills response.

---

## 9. Frontend Routes (Next.js 14 App Router)

### 9.1 Auth (Public)

| Route | File | Backend API |
|---|---|---|
| `/login` | `app/(auth)/login/page.tsx` | `POST /auth/login` |
| `/register` | `app/(auth)/register/page.tsx` | `POST /auth/register` |

### 9.2 Dashboard (Protected)

| Route | File | Mô tả | Backend API |
|---|---|---|---|
| `/dashboard` | `app/(app)/dashboard/page.tsx` | Overview: Market fit %, Trending skills | `/analysis/market-fit/{cv_id}`, `/recommend/trending-skills` |
| `/dashboard/history` | `app/(app)/dashboard/history/page.tsx` | Lịch sử phân tích Gap | `GET /analysis/history/{user_id}` |

### 9.3 CV Management

| Route | File | Mô tả | Backend API |
|---|---|---|---|
| `/cv` | `app/(app)/cv/page.tsx` | Danh sách CV | `GET /cv/list` |
| `/cv/upload` | `app/(app)/cv/upload/page.tsx` | Upload CV: PDF / ảnh | `POST /cv/upload` |
| `/cv/[cv_id]` | `app/(app)/cv/[cv_id]/page.tsx` | Chi tiết CV đã parse | `GET /cv/{cv_id}/parsed-result` |
| `/cv/[cv_id]/verify` | `app/(app)/cv/[cv_id]/verify/page.tsx` | Xác minh kết quả OCR (Feature 3.2) | `GET /cv/{cv_id}/parsed-result` |

### 9.4 Job Market / JD

| Route | File | Mô tả | Backend API |
|---|---|---|---|
| `/jobs` | `app/(app)/jobs/page.tsx` | Danh sách JD + filter lương/địa điểm | `POST /jd/search` |
| `/jobs/import` | `app/(app)/jobs/import/page.tsx` | Import JD: paste text hoặc URL | `POST /jd/import/text` / `/url` |
| `/jobs/[job_id]` | `app/(app)/jobs/[job_id]/page.tsx` | Chi tiết JD | `GET /jd/{job_id}` |
| `/jobs/[job_id]/analyze` | `app/(app)/jobs/[job_id]/analyze/page.tsx` | Gap CV vs JD này | `POST /analysis/gap` |

### 9.5 Gap Analysis

| Route | File | Mô tả | Backend API |
|---|---|---|---|
| `/analysis` | `app/(app)/analysis/page.tsx` | Chọn CV + JD để phân tích | `POST /analysis/gap` |
| `/analysis/[id]` | `app/(app)/analysis/[id]/page.tsx` | Kết quả Gap: met/gap + insight | `POST /analysis/gap` (cached) |
| `/analysis/[id]/feedback` | `app/(app)/analysis/[id]/feedback/page.tsx` | Đánh giá kết quả | `POST /analysis/feedback` |
| `/analysis/market` | `app/(app)/analysis/market/page.tsx` | % JD thị trường phù hợp | `GET /analysis/market-fit/{cv_id}` |

### 9.6 Learning Path & Recommend

| Route | File | Mô tả | Backend API |
|---|---|---|---|
| `/learn` | `app/(app)/learn/page.tsx` | Khóa học theo Gap hiện tại | `POST /recommend/courses` |
| `/learn/roadmap` | `app/(app)/learn/roadmap/page.tsx` | Lộ trình học theo tháng | `GET /recommend/roadmap/{cv_id}` |
| `/learn/trending` | `app/(app)/learn/trending/page.tsx` | Kỹ năng xu hướng + lương | `GET /recommend/trending-skills` |
| `/simulate` | `app/(app)/simulate/page.tsx` | Mô phỏng lộ trình nghề nghiệp | `POST /analysis/simulate` |

### 9.7 Admin (Protected – Role Admin)

| Route | File | Mô tả | Backend API |
|---|---|---|---|
| `/admin/jobs` | `app/(admin)/jobs/page.tsx` | Quản lý JD: active/deactive | `GET /jd/list` + `PATCH /jd/{job_id}/status` |
| `/admin/jobs/import` | `app/(admin)/jobs/import/page.tsx` | Import hàng loạt | `POST /jd/import/text` |
| `/admin/skills` | `app/(admin)/skills/page.tsx` | Quản lý Skill + Alias Neo4j | — |

> [!NOTE]
> Tất cả routes `(app)` và `(admin)` yêu cầu `Authorization: Bearer <token>`. Khi `is_ocr = true` → Frontend **bắt buộc** hiển thị banner cảnh báo + link `/cv/{cv_id}/verify`.

---

## 10. API Còn Thiếu (Từ Coverage Matrix)

### `POST /jd/search` – JD Service (Feature 1.8)

```json
// Input:
{
  "query_text": "fullstack nodejs senior",
  "filters": {
    "location": "Hà Nội",
    "min_salary": 20000000,
    "max_salary": 50000000,
    "employment_type": "full-time",
    "remote_friendly": false
  },
  "page": 1,
  "page_size": 20
}
// Output:
{
  "total": 85,
  "results": [
    {
      "job_id": "uuid",
      "source_id": "topcv_2119168",
      "title": "Fullstack Developer",
      "company": "YANSOFT",
      "min_salary_vnd": 30000000,
      "location": "Hà Nội",
      "semantic_score": 0.91,
      "top_skills_required": ["Node.js", "React", "Docker"]
    }
  ]
}
```

### `GET /cv/{cv_id}/parsed-result` – CV Service (Feature 1.2 + 3.2)

```json
{
  "cv_id": "cv_abc123",
  "is_ocr": true,
  "ocr_confidence": 0.87,
  "warning": "CV được đọc từ ảnh, có thể có sai sót.",
  "skills": [{ "name": "Node.js", "years_exp": 3, "level": "Senior" }],
  "education": [{ "degree": "Cử nhân", "major": "KTPM", "school": "Bách Khoa" }],
  "experience_years_total": 4
}
```

### `GET /analysis/history/{user_id}` – Analysis Service (Feature 4.2)

```json
{
  "history": [
    {
      "analysis_id": "gap_cv123_job456",
      "job_title": "Fullstack Team Lead",
      "overall_match_pct": 72,
      "analyzed_at": "2026-04-10T13:00:00Z"
    }
  ]
}
```

### `PATCH /jd/{job_id}/status` – JD Service (Admin)

```json
// Input:  { "status": "deactive" }
// Output: { "job_id": "uuid", "status": "deactive", "updated_at": "..." }
```

