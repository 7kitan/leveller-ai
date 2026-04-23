# AI Career Advisor (Lumix AI) — Kiến trúc hệ thống

> **Dự án:** Nền tảng Tư vấn Sự nghiệp dựa trên AI
> **Công nghệ lõi:** Next.js, FastAPI, PostgreSQL (pgvector), Redis, Celery, LangGraph, OpenAI GPT-4o.

---

## 1. Tóm tắt dự án

Lumix AI là một nền tảng tư vấn sự nghiệp AI tiên tiến, tận dụng các Mô hình Ngôn ngữ Lớn (LLM) và Tìm kiếm Vector để cung cấp hướng dẫn nghề nghiệp cá nhân hóa. Hệ thống bóc tách CV của người dùng, phân tích khoảng cách kỹ năng so với các mô tả công việc (JD) thực tế, và tạo ra lộ trình học tập tùy chỉnh kèm theo các đề xuất khóa học.

---

## 2. Kiến trúc tổng thể

Hệ thống tuân theo kiến trúc microservices, được điều phối bởi một API Gateway tập trung và vận hành bởi một pipeline xử lý AI bất đồng bộ.

```mermaid
graph TD
    User([Người dùng / Quản trị viên]) <--> Frontend[Frontend - Next.js]
    Frontend <--> Gateway[API Gateway - FastAPI]
    
    subgraph Services [Lớp Microservices]
        Gateway <--> AuthSvc[Dịch vụ Auth]
        Gateway <--> CVSvc[Dịch vụ CV]
        Gateway <--> JDSvc[Dịch vụ JD]
        Gateway <--> AnalysisSvc[Dịch vụ Analysis]
        Gateway <--> RecommendSvc[Dịch vụ Recommender]
        Gateway <--> AdminSvc[Dịch vụ Admin]
    end
    
    subgraph Data [Lớp Dữ liệu & Message]
        Services <--> DB[(PostgreSQL + pgvector)]
        Services <--> Cache[(Redis)]
        Services <--> Storage[Lưu trữ File Local/MinIO]
        AnalysisSvc & CVSvc -.-> Queue{Hàng đợi tác vụ Celery}
    end
    
    subgraph AI [Trung tâm AI Inference]
        Queue <--> Worker[Celery Workers]
        Worker <--> LangGraph[LangGraph Orchestrator]
        LangGraph <--> LLM[[OpenAI GPT-4o-mini]]
    end
```

---

## 3. Các thành phần cốt lõi

### 3.1 API Gateway
- **Công nghệ chính:** FastAPI
- **Nhiệm vụ:** Điều hướng (Reverse proxying), quản lý CORS, và tiêm (inject) thông tin xác thực.
- **Bảo mật:** Xác thực token JWT và tiêm các header `X-User-ID`, `X-User-Email`, và `X-Is-Admin` vào các yêu cầu gửi đến các microservice phía sau.

### 3.2 Microservices
| Dịch vụ | Nhiệm vụ chính |
|---|---|
| **Auth Service** | Đăng ký, đăng nhập, quản lý hồ sơ người dùng và cấp phát JWT. |
| **CV Service** | Tải lên file CV, quản lý bóc tách và CRUD hồ sơ kỹ năng. |
| **JD Service** | Thu thập JD, nhập JD thủ công và tìm kiếm việc làm dựa trên vector. |
| **Analysis Service** | Điều phối phân tích khoảng cách, tạo lộ trình sự nghiệp và vòng lặp phản hồi. |
| **Recommender Service** | Quản lý cơ sở dữ liệu khóa học và công cụ đề xuất ngữ nghĩa. |
| **Admin Service** | Cài đặt hệ thống, giám sát và các quyền điều khiển quản trị. |

---

## 4. Kiến trúc dữ liệu

### 4.1 Sơ đồ thực thể - quan hệ (ERD)

```mermaid
erDiagram
    USERS ||--o{ USER_CVS : "tải lên"
    USERS ||--o{ USER_ANALYSIS : "yêu cầu"
    USER_CVS ||--o{ USER_SKILL_PROFILE : "chứa"
    USER_CVS ||--o{ USER_WORK_EXPERIENCES : "chi tiết"
    USER_CVS ||--o{ USER_ANALYSIS : "được phân tích trong"
    JOBS ||--o{ JOB_SKILL_REQUIREMENT : "yêu cầu"
    JOBS ||--o{ USER_ANALYSIS : "được so sánh với"
    SKILLS ||--o{ USER_SKILL_PROFILE : "định nghĩa"
    SKILLS ||--o{ JOB_SKILL_REQUIREMENT : "cần thiết cho"
    USER_ANALYSIS ||--o{ USER_FEEDBACK : "nhận"

    USERS {
        uuid id PK
        string email UK
        string hashed_password
        boolean is_admin
        uuid last_analysis_id FK
    }
    USER_CVS {
        uuid id PK
        uuid user_id FK
        string status "processing|completed|failed"
        jsonb cv_parsed_json
        string file_hash
    }
    JOBS {
        uuid id PK
        text title_raw
        text raw_text
        jsonb extracted_requirements_json
        vector vector_1536
    }
    COURSES {
        uuid id PK
        string title
        string level
        jsonb tags
        vector vector_1536
    }
    USER_ANALYSIS {
        uuid id PK
        uuid user_id FK
        uuid cv_id FK
        uuid job_id FK
        float match_score
        jsonb result_json
    }
```

---

## 5. AI Pipelines (v3 — LangGraph)

Nền tảng sử dụng các tác nhân AI (AI Agents) tinh vi được điều phối qua LangGraph để thực hiện suy luận toàn diện.

### 5.1 Pipeline bóc tách CV (CV Parsing)
Chuyển đổi tài liệu PDF/Ảnh thô thành hồ sơ JSON có cấu trúc.
1. **Trích xuất**: Phương pháp hybrid (Trích xuất văn bản trực tiếp → Fallback OCR).
2. **Ẩn danh PII**: Che các thông tin nhạy cảm trước khi xử lý bằng LLM.
3. **Bóc tách LLM**: GPT-4o-mini trích xuất kỹ năng, kinh nghiệm và học vấn vào định dạng có cấu trúc.
4. **Chuẩn hóa**: Ánh xạ các kỹ năng vào danh mục kỹ năng nội bộ.

### 5.2 Pipeline Phân tích Khoảng cách & Lộ trình
Quy trình tối ưu hóa với 2 lần gọi LLM để đạt độ chính xác và hiệu suất tối đa.

```mermaid
sequenceDiagram
    participant Worker as Celery Worker
    participant LG as LangGraph Orchestrator
    participant LLM as OpenAI GPT-4o
    participant DB as PostgreSQL (pgvector)

    Worker->>LG: Bắt đầu run_gap_analysis_v3
    LG->>LG: Node: load_cv (Lấy dữ liệu từ DB)
    
    alt LLM Call #1: Phân tích
        LG->>LLM: Node: gap_analysis_llm
        Note over LLM: Bóc tách JD + Phân tích Gap + Xác định Top Gap
        LLM-->>LG: {match_score, skill_gaps, top_gaps}
    end

    LG->>DB: Tìm kiếm Vector cho các Top Gap
    DB-->>LG: Các khóa học ứng viên (~36)

    alt LLM Call #2: Đề xuất & Lộ trình
        LG->>LLM: Node: course_agent
        Note over LLM: Chọn khóa học tốt nhất + Tổng hợp lộ trình
        LLM-->>LG: {selected_courses, career_roadmap}
    end

    LG->>LG: Node: finalize (Gộp kết quả & Lưu Cache)
    LG->>Worker: Báo cáo cuối cùng
```

---

## 6. Môi trường & Hạ tầng

### 6.1 Chiến lược triển khai
- **Container hóa**: Docker & Docker Compose.
- **Workers**: Các worker Celery xử lý các tác vụ AI nặng một cách bất đồng bộ.
- **Caching**: Lưu trữ đệm Redis đa lớp cho các phản hồi từ LLM và kết quả phân tích khoảng cách.

### 6.2 Các cờ cấu hình chính
| Cờ (Flag) | Mặc định | Mục đích |
|---|---|---|
| `USE_LLM_GAP_AGENT` | `true` | Kích hoạt phân tích v3 LangGraph thay vì engine vector cũ. |
| `GAP_LLM_MODEL` | `gpt-4o-mini` | Chỉ định mô hình suy luận chính. |
| `GAP_CACHE_TTL` | `1800` | Thời gian lưu cache Redis cho kết quả phân tích (30 phút). |
| `GAP_PII_MASKING` | `true` | Đảm bảo quyền riêng tư dữ liệu trong log và prompt LLM. |

---

## 7. Cấu trúc thư mục dự án

```text
backend/
├── gateway/         # FastAPI Gateway & Auth Middleware
├── services/        # Các Microservice theo domain
│   ├── auth_service/
│   ├── cv_service/
│   ├── jd_service/
│   ├── analysis_service/
│   └── recommender_service/
├── worker/          # Celery Worker & LangGraph Agents
│   ├── tasks/       # Định nghĩa các tác vụ chạy nền
│   └── langgraph_agents/
│       └── gap_v3/  # Đồ thị phân tích Gap toàn diện
├── shared/          # DB Models, LLM Utils, Shared Schemas
└── scripts/         # Scripts gieo dữ liệu (Seeder) & Migration
```
