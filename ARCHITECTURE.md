# Kiến Trúc Hệ Thống: Phân Tích Khoảng Trống Kỹ Năng & Gợi Ý Chứng Chỉ (Leveller.ai)

Leveller.ai là nền tảng chuyên sâu về **Phân Tích Khoảng Trống Kỹ Năng (Skill Gap Analysis)** và **Gợi Ý Lộ Trình Chứng Chỉ (Certificate Suggestion)**. Hệ thống được xây dựng trên kiến trúc Microservices hiện đại, kết hợp sức mạnh của AI Reasoning và Vector Search để tối ưu hóa lộ trình sự nghiệp.

---

## 1. Tổng Quan Hệ Thống

Hệ thống tập trung giải quyết bài toán:
- **Phân tích Năng lực (Profile Parsing)**: Trích xuất chính xác bộ kỹ năng và kinh nghiệm từ CV (hỗ trợ OCR cho file scan/ảnh).
- **Phân tích Khoảng trống (Gap Analysis)**: So khớp năng lực hiện tại với yêu cầu chi tiết từ **Job Description (JD)** bằng LLM Reasoning và Vector Similarity để chỉ ra các kỹ năng còn thiếu.
- **Gợi ý Chứng chỉ & Lộ trình (Recommendations)**: Đề xuất các chứng chỉ chuyên môn, khóa học và project thực tế phù hợp nhất để lấp đầy khoảng trống kỹ năng.

---

## 2. Kiến Trúc Dịch Vụ (Microservices)

Hệ thống bao gồm các dịch vụ chính chạy độc lập trong Docker containers:

### A. API Gateway
- **Công nghệ**: FastAPI / Uvicorn.
- **Vai trò**: Điểm tiếp nhận duy nhất cho mọi request từ Frontend. Thực hiện định tuyến (routing) đến các service nội bộ và xử lý CORS.

### B. Core Services
- **Auth Service**: Quản lý người dùng, đăng ký, đăng nhập (JWT) và phân quyền (RBAC).
- **CV Service**: Quản lý hồ sơ CV, lưu trữ metadata và trạng thái xử lý.
- **JD Service**: Quản lý mô tả công việc (Job Descriptions) và dữ liệu thị trường.
- **Analysis Service**: "Bộ não" tính toán. Chứa logic tính toán Match Score, Growth Potential và Skill Gaps.
- **Recommender Service**: Thực hiện Vector Search để tìm kiếm khóa học (Courses) và công việc (Jobs) tương quan nhất.
- **Admin Service**: Cung cấp các công cụ quản trị, nạp dữ liệu (seeding), cấu hình hệ thống và theo dõi logs.

---

## 3. Hệ Thống Xử Lý Bất Đồng Bộ (Workers)

Sử dụng **Celery** và **Redis** để xử lý các tác vụ nặng mà không làm nghẽn giao diện:

- **worker_analysis**: Thực hiện phân tích AI chuyên sâu, tính toán roadmap.
- **worker_parsing**: Chuyên trách bóc tách CV (Parsing) sử dụng LangGraph và LLM.
- **worker_crawler**: Cào dữ liệu từ các nguồn bên ngoài (TopCV, Coursera).
- **worker_email**: Gửi thông báo, xác nhận qua email.
- **worker_benchmark**: Đánh giá hiệu năng và độ chính xác của các mô hình AI.

---

## 4. Công Nghệ AI & Dữ Liệu

### A. AI Orchestration (LangGraph)
Hệ thống không gọi LLM một cách đơn lẻ mà sử dụng **LangGraph** để điều phối các tác vụ phức tạp (ví dụ: Parsing CV qua nhiều bước kiểm định).

### B. Vector Search (pgvector)
- Sử dụng extension `pgvector` trên PostgreSQL để lưu trữ và tìm kiếm vector embeddings (1536 chiều từ OpenAI).
- Cho phép tìm kiếm ngữ nghĩa (Semantic Search) thay vì chỉ tìm theo từ khóa chính xác.

### C. LLM Engines
- **GPT-4o**: Sử dụng cho các tác vụ cần độ chính xác cao nhất (Parsing CV).
- **GPT-4o-mini**: Sử dụng cho các tác vụ phân tích nhanh và tiết kiệm chi phí.

---

## 5. Luồng Dữ Liệu (Data Flow)

### 5. Luồng Dữ Liệu & Hành trình Người dùng (User Journey)

![Leveller.ai User Flow](./user_flow.svg)

1.  **Ingestion**: Người dùng upload CV (PDF/Image/Docx).
2.  **Parsing**: Worker sử dụng OCR (Chandra Engine) và LLM (via LiteLLM) để chuyển đổi CV thành JSON.
3.  **JD Selection**: Người dùng lựa chọn Job Description (JD) mục tiêu hoặc hệ thống gợi ý JD phù hợp.
4.  **Skill Matching**: So khớp bộ kỹ năng từ CV với yêu cầu của JD đã chọn sử dụng **LLM Reasoning** để đánh giá mức độ tương quan sâu về ngữ nghĩa, trình độ và kinh nghiệm thực tế.
5.  **Gap Analysis**: Xác định các kỹ năng còn thiếu (Skill Gaps) mà người dùng cần bổ sung để đạt yêu cầu của JD.
6.  **Recommendation**: Tìm kiếm các khóa học (Courses) phù hợp nhất thông qua **Vector Similarity** (Semantic Search) để lấp đầy chính xác các khoảng trống kỹ năng đã xác định.
7.  **Analytics**: Tính toán Match Score, Growth Potential và phân tích mức độ phổ biến/nhu cầu của các kỹ năng đó trên thị trường lao động.
8.  **Presentation**: Trả kết quả về Frontend hiển thị Radar Chart, Skill Roadmap và biểu đồ so sánh.

---

## 6. Kiến Trúc Chi Tiết (Technical Deep-Dive)

### 6.1. AI Core & LiteLLM Integration
Hệ thống sử dụng **LiteLLM** làm lớp trừu tượng (Abstraction Layer) cho toàn bộ các cuộc gọi AI. Điều này mang lại các lợi thế:
-   **Multi-Provider**: Hỗ trợ đồng thời OpenAI, Google Gemini, Anthropic, DeepSeek, Groq.
-   **Model Registry**: Quản lý tập trung các model từ đời cũ đến các model mới nhất năm 2026 (GPT-5.5, Gemini 3.1).
-   **Automatic Fallback**: Tự động chuyển đổi sang model dự phòng nếu model chính bị lỗi hoặc hết hạn mức (Quota).
-   **Quota Management**: Kiểm soát lượng token tiêu thụ theo từng người dùng trong ngày.

### 6.1. AI Inference Hub (Chandra Engine) - *Thành phần Tùy chọn*
Đây là service chuyên biệt xử lý các tác vụ AI nặng (Heavy Lifting):
-   **Multimodal OCR**: Sử dụng các model thị giác máy tính (Computer Vision) để đọc hiểu CV từ mọi định dạng (PDF, PNG, JPG, Docx).
-   **Layout Analysis**: Phân tích cấu trúc tài liệu để đảm bảo trích xuất đúng thông tin theo từng khối (Kinh nghiệm, Kỹ năng, Học vấn).
-   **Resilience & Fallback**: Được thiết kế là thành phần **Tùy chọn (Optional)**. Trong trường hợp không cấu hình Chandra Hub, **CV Service** sẽ tự động kích hoạt **PDF Library Fallback** để trích xuất văn bản trực tiếp từ các file PDF chuẩn, đảm bảo hệ thống vẫn hoạt động ổn định.
-   **Standalone Service**: Chạy độc lập để tối ưu hóa tài nguyên GPU/CPU tách biệt với API Gateway.

### 6.2. Worker & Queue System (Celery)
Hệ thống phân tách tác vụ qua các Queue riêng biệt để tối ưu hiệu suất:
-   **`analysis` queue**: Xử lý tính toán Gap Analysis (LangGraph Orchestrator).
-   **`cv_parsing` queue**: Chuyên trách bóc tách CV bằng OCR và LLM.
-   **`market_stats` queue**: Chạy các tác vụ Crawler (TopCV, Coursera) và tính toán thống kê thị trường hàng ngày.
-   **`benchmark` queue**: Đánh giá hiệu suất và độ chính xác của các model AI.

### 6.3. Sơ Đồ Kiến Trúc (Architecture Diagrams)

#### A. Sơ đồ hệ thống (Premium Architecture Diagram)
Sơ đồ mô tả các thành phần microservices, workers và hạ tầng AI:

![Leveller.ai Architecture](./system_architecture.svg)

#### B. Sơ đồ logic (Mermaid Fallback)
Sơ đồ này mô tả các thành phần cốt lõi của hệ thống dưới dạng text-based:

```mermaid
graph LR
    User((User)) --> FE[Frontend]
    FE <--> BE[Backend/API]
    BE <--> DB[(Database)]
    BE <--> AI[AI Agent/LLM]
    AI <--> Ext[External Services]
```

#### B. Sơ đồ chi tiết (Technical Deep-Dive)
Chi tiết các dịch vụ và cơ sở hạ tầng thực tế:

```mermaid
graph TD
    User((User))
    Web[Frontend - Next.js]
    Gateway[Backend/API - FastAPI]
    
    subgraph "Core Microservices"
        AuthSvc[Auth Service]
        CVSvc[CV Service]
        JDSvc[JD Service]
        AnalSvc[Analysis Service]
    end
    
    subgraph "Worker Infrastructure (Celery)"
        Broker[(Redis Broker)]
        
        subgraph "Queues"
            Q_Anal[Analysis Queue]
            Q_CV[CV Parsing Queue]
            Q_Crawler[Crawler/Market Queue]
        end
        
        subgraph "Workers"
            W_Anal[Analysis Worker]
            W_CV[CV Parsing Worker]
            W_Crawler[Crawler Worker]
        end
    end
    
    subgraph "AI Inference Hub"
        Chandra[Chandra OCR Engine]
    end

    subgraph "AI Agent/LLM (LiteLLM)"
        LiteLLM[LiteLLM Routing]
        Models[OpenAI, Gemini, Claude]
    end
    
    subgraph "Database Layer"
        Postgres[(PostgreSQL + pgvector)]
        Redis[(Redis Cache)]
    end
    
    subgraph "External Services"
        Ext_C[Coursera]
        Ext_T[TopCV]
    end

    User <--> Web
    Web <--> Gateway
    Gateway <--> AuthSvc
    Gateway <--> CVSvc
    Gateway <--> JDSvc
    Gateway <--> AnalSvc
    
    AnalSvc -- "Enqueue Task" --> Broker
    CVSvc -- "Enqueue Task" --> Broker
    
    Broker --> Q_Anal --> W_Anal
    Broker --> Q_CV --> W_CV
    Broker --> Q_Crawler --> W_Crawler
    
    W_Anal -- "LangGraph Flow" --> LiteLLM
    W_CV -- "Send Image/PDF" --> Chandra
    Chandra -- "OCR Result" --> W_CV
    W_CV -- "Refine JSON" --> LiteLLM
    W_Crawler -- "Skill Extraction" --> LiteLLM
    
    LiteLLM --> Models
    
    W_Anal <--> Postgres
    W_Crawler <--> Postgres
    W_Crawler -- "Scrape" --> Ext_C
    W_Crawler -- "Scrape" --> Ext_T
    
    W_Anal <--> Redis
    W_Crawler <--> Redis
```

---

## 7. Danh Mục Công Nghệ (Tech Stack)

| Thành phần | Công nghệ |
| :--- | :--- |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy |
| **Frontend** | Next.js 14, TypeScript, TailwindCSS |
| **Asynchronous** | Celery, Redis |
| **Database** | PostgreSQL + pgvector |
| **AI/LLM** | OpenAI, Gemini, Claude, LiteLLM, LangGraph |
| **DevOps** | Docker, Docker Compose |
| **OCR** | Chandra Engine |

---

*© 2026 Leveller.ai - 078 Team - A20 AI Thực Chiến*
