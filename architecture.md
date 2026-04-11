# 🚀 AI Career Advisor – Microservice Architecture (Upgraded - Lightweight)

## 1. Overview

### Goal

Build an AI system that:

- Parses CV
- Compares with Job Description (JD)
- Identifies skill gaps
- Recommends optimal certificates
- Simulates career path (NEW)

### Core Value

> "Know exactly what to learn to become job-ready as fast as possible"

---

## 2. Upgraded System Architecture (Lightweight)

```
[Frontend - Next.js]
        ↓
   [API Gateway - FastAPI]
        ↓
 ┌───────────────┬───────────────┬───────────────┬───────────────┬───────────────┐
 │ Auth Service  │ CV Service    │ JD Service    │ Analysis Svc  │ Recommender   │
 └───────────────┴───────────────┴───────────────┴───────────────┴───────────────┘
                                ↓
                         Simulation Service ⭐

------------------ ASYNC LAYER ------------------

            Redis (Queue + Cache)
                    ↓
      Worker (Celery + LangGraph)
                    ↓
          AI Orchestration Layer

------------------ AI LAYER ------------------

1. LLM Reasoning Layer (LangGraph)
2. Embedding Service
3. Skill Classifier
4. Skill Knowledge Graph ⭐

------------------ DATA LAYER ------------------

PostgreSQL (per service) (vector DB extension)
S3 / MinIO (file storage)
(Optional) Neo4j (skill graph)

------------------ OBSERVABILITY ------------------

OpenTelemetry + LGTM Stack
LangSmith (LLM tracing)

```

👉 **Design philosophy:** tối giản nhưng đủ mạnh cho MVP + scale vừa phải (không cần Kafka/Kubernetes)

---

## 3. Key Enhancements

### 3.1 Agentic Workflow (LangGraph)

Replace linear pipeline with state machine:

```
START
 → Extract_Text
 → Detect_Domain
 → Parse_Skills
 → Normalize_Skills
 → Enrich_Skills (knowledge graph)
 → Embed
 → Fetch_JD_candidates
 → Gap_Analysis
 → Generate_Report
END
```

---

### 3.2 Semantic Search

- Replace keyword matching with vector similarity
- Match related skills:
  - "REST API" ≈ "Backend API"

---

### 3.3 Skill Knowledge Graph ⭐

Structure:

```
Python → Backend → API → FastAPI
React → Frontend → Web
```

Use cases:

- Infer missing skills
- Suggest learning path
- Improve gap analysis accuracy

---

### 3.4 Multi-stage Gap Analysis

1. Hard Match
2. Semantic Match (vector)
3. Transferable Skills
4. Experience Weighting

Formula:

```
Gap Score =
  Vector Distance
+ Experience Gap
+ Skill Importance Weight
```

---

### 3.5 Advanced Recommendation Engine

Ranking:

```
Score =
  Relevance (vector)
+ Difficulty Match
+ Time to Learn
+ ROI (salary increase)
```

---

### 3.6 Simulation Service ⭐

Endpoint:

```
POST /simulate-career-path
```

Output example:

```
Month 1 → Learn Python
Month 2 → Learn FastAPI
Month 3 → Build project
Month 4 → Apply jobs
```

---

## 4. Services (Updated)

### 4.1 JD Service

Responsibilities:

- Crawl/import job data
- Normalize JD
- Extract skills
- Embed into pvg
- Detect trends ⭐

Pipeline:

```
Raw JD → Clean → Extract → Normalize → Embed
```

---

### 4.2 Worker (LangGraph)

Nodes:

- PDF Extractor
- OCR Fallback (PaddleOCR) ⭐
- Skill Parser (LLM)
- Skill Normalizer
- Skill Enricher (Graph)
- Vector Upsert
- Gap Analyzer
- Report Generator

Details:

- If CV is image-based or PDF scan → trigger PaddleOCR (self-hosted)
- Ensure high-accuracy text extraction before LLM parsing


---

### 4.3 Analysis Service

- Skill normalization
- Gap scoring
- Skill graph reasoning

---

### 4.4 Recommendation Service

- Semantic search (pgvector)
- Multi-factor ranking

---

### 4.5 Simulation Service (NEW)

- Generate career roadmap
- Time-based planning

---

## 5. Data Model (Extended)

### skills

```
id
name
parent_skill_id
category_id
vector_id
```

### user_skill_profile

```
user_id
skill_id
level (0-5)
years_exp
confidence_score
```

### job_skill_requirement

```
job_id
skill_id
required_level
importance_weight
```

### cv_metadata ⭐

```
cv_id
user_id
source_type (pdf | image | scanned_pdf)
parsed_with (pdf_parser | paddleocr)
is_ocr (boolean)
confidence_score
created_at
```

Purpose:

- Detect CV parsed via OCR
- Allow user to re-check accuracy
- Improve transparency & trust

job_id
skill_id
required_level
importance_weight
```

---

## 6. Vector Collections (Qdrant)

- cv_vectors
- jd_vectors
- course_vectors

---

## 7. Event-driven Design (Lightweight)

Using Redis Pub/Sub or Celery events (NO Kafka)

Events:

```
CV_UPLOADED
CV_PARSED
SKILL_EXTRACTED
EMBEDDING_DONE
GAP_CALCULATED
RECOMMENDATION_READY
```

Benefits:

- Retry từng bước
- Dễ debug
- Đủ dùng cho MVP

---

## 8. Observability

### Stack

- Loki (logs)
- Tempo (tracing)
- Prometheus (metrics)
- Grafana (dashboard)

### AI Monitoring

- Token usage
- Latency
- Hallucination rate ⭐
- Extraction accuracy ⭐

---

## 9. Scaling Strategy (2 PHASE ONLY)

### Phase 1 – MVP (Hackathon Ready 🚀)

- Redis (queue + cache)
- Single worker
- Docker Compose
- PostgreSQL với pgvector extension (tối ưu resource)
- Basic monitoring (logs + metrics)

👉 Goal: chạy được end-to-end, demo mượt

---

### Phase 2 – Scale nhẹ (Production nhỏ)

- Multiple Celery workers
- Redis cluster (optional)
- Horizontal scaling services (Docker)
- Add caching layer (Redis)
- Improve observability (full LGTM)

👉 Goal: handle vài nghìn user mà vẫn ổn

---

## 10. Key Principles

- Agentic AI (not linear pipeline)
- Semantic-first (not keyword)
- Async-first architecture
- Microservice isolation
- Lightweight-first (no over-engineering)

---

## 🎯 Positioning

> Not just a CV analyzer → A Career Copilot

---

## 11. Extra Value Enhancements ⭐

### 11.1 Feedback Loop (Learning System)

Add table:

```
user_feedback
------------
id
user_id
analysis_id
rating (1-5)
is_accurate (boolean)
missing_skills (json)
created_at
```

Use cases:

- Tune Gap Score weights over time
- Improve recommendation ranking
- Detect systematic errors in skill extraction

Future:

- Online learning (adjust weights dynamically)
- Fine-tune prompts / models

---

### 11.2 pgvector Hybrid Search (IMPORTANT)

Do NOT use pure vector search only.

Combine:

- Vector similarity (semantic)
- Metadata filtering

Example:

```
Vector: "backend python"
Filter:
  location = "Hanoi"
  salary > 1000$
```

Benefits:

- More accurate JD matching
- Better recommendation relevance
- Production-ready search behavior

---

### 11.3 CV Security & PII Handling

Since CV contains sensitive data:

Risks:

- Phone number
- Email
- Address

Solutions:

1. Pre-processing (before storage)
```
Mask PII:
John Doe → John D.
Phone → ***
```

2. Encryption

- Encrypt CV files in S3/MinIO
- Use signed URLs for access

3. Access Control

- CV belongs to user only
- Short-lived access tokens

4. Compliance mindset

- Prepare for GDPR-like rules
- Allow user to delete data

---

### 11.4 Bonus (Optional but WOW)

- Skill trend detection from JD
- Career path prediction using graph
- Personalized learning speed estimation

---

## ✅ Final Note

This system is now:

- Lightweight (no Kafka/K8s)
- Intelligent (Agent + Semantic + Graph)
- Extensible (feedback loop + hybrid search)
- Safe (PII-aware)

