# 📊 GAP ANALYSIS v3.0 — LLM-Centric Holistic Gap Analysis
## Phân tích & Kế hoạch Kiến trúc (Không Neo4j, Full Context)

> **Dự án:** AI Career Advisor (Team078)
> **Phiên bản:** v3.0 — LLM-Centric, Holistic Reasoning

---

## MỤC LỤC

1. [Triết lý thiết kế](#1-triết-lý-thiết-kế)
2. [Tổng quan kiến trúc mới](#2-tổng-quan-kiến-trúc-mới)
3. [Kiến trúc chi tiết từng Agent](#3-kiến-trúc-chi-tiết-từng-agent)
4. [Data Model — CV Parsed Structure](#4-data-model--cv-parsed-structure)
5. [Gap Analysis Agent — Single LLM Full Context](#5-gap-analysis-agent--single-llm-full-context)
6. [Course Recommendation Agent](#6-course-recommendation-agent)
7. [Data Flow tổng thể](#7-data-flow-tổng-thể)
8. [Gap so với spec & impl cũ](#8-gap-so-với-spec--impl-cũ)
9. [Lộ trình triển khai](#9-lộ-trình-triển-khai)

---

## 1. Triết lý thiết kế

### 1.1 Vấn đề với kiến trúc cũ

```
Kiến trúc cũ: Multi-stage skill-by-skill pipeline
═════════════════════════════════════════════════════════

JD text
  │ Split thành list requirements
  ▼
Stage 1: Exact match (skill_id)
  │ ↓ miss
Stage 2: Vector cosine (pgvector)
  │ ↓ miss
Stage 3: Neo4j transferable (graph traversal) ← phức tạp, dễ fail
  │ ↓ miss
Stage 4: Experience × Level × Recency multiplier
  ▼
Final Score
```

**Vấn đề cốt lõi:**
- Tính từng skill một → mất ngữ cảnh tổng thể
- Neo4j không đáng tin cậy (ít data, relationship không đầy đủ)
- "Transferable" suy luận thủ công bằng graph → LLM làm tốt hơn tự động
- Điểm số bị chia nhỏ → không phản ánh độ phù hợp thực sự
- Vector similarity không hiểu ngữ cảnh JD (VD: "Kubernetes" trong JD startup ≠ trong JD enterprise)

### 1.2 Triết lý mới — LLM Holistic Reasoning

```
Triết lý mới: Single LLM reasoning trên toàn bộ context
═════════════════════════════════════════════════════════

CV (đã parsed, structured) + JD (đã extract)
  │
  │  ← Đưa toàn bộ vào 1 LLM call
  ▼
┌─────────────────────────────────────────────┐
│           LLM GAP ANALYSIS AGENT            │
│                                             │
│  "Dựa trên TOÀN BỘ CV + TOÀN BỘ JD,         │
│   hãy phân tích sự phù hợp tổng thể          │
│   và đưa ra gap analysis toàn diện"          │
│                                             │
│  LLM hiểu:                                  │
│  • Ngữ cảnh công việc (startup vs enterprise)│
│  • Experience summary (6 năm backend)       │
│  • Transferable skills tự nhiên             │
│  • Severity thực sự (job critical vs nice)   │
│  • Learning path realistic                  │
└─────────────────────────────────────────────┘
  │
  ▼
Structured Gap Report
  │ (LLM chọn courses luôn)
  ▼
Course Recommendation
  │
  ▼
Career Roadmap
```

**Ưu điểm của LLM Holistic:**
- Hiểu ngữ cảnh toàn cục (6 năm Python backend → học Go nhanh hơn người mới)
- Suy luận transferable tự nhiên, không cần graph database
- Đánh giá severity theo thực tế job market, không theo công thức
- Đưa ra learning path có ý nghĩa thực tế
- Đơn giản hóa: bỏ hoàn toàn Neo4j, pgvector matching stage

### 1.3 So sánh 3 phiên bản

| Khía cạnh | v1 (Vector Engine) | v2 (Multi-Agent + Neo4j) | **v3 (LLM-Centric)** |
|---|---|---|---|
| Gap calculation | skill-by-skill, vector cosine | 3-tier + Neo4j Stage 3 | **Single LLM holistic reasoning** |
| Neo4j | Không dùng | Dùng cho transferable | **Bỏ hoàn toàn** |
| pgvector | Dùng cho matching | Dùng cho matching | **Chỉ dùng cho course search** |
| Course lookup | ILIKE text | Vector search + LLM select | **LLM chọn trực tiếp** |
| Latency | ~0.5s (fast) | ~3-5s (LLM) | **~3-5s (1 LLM call)** |
| Accuracy | Medium (rule-based) | High (Neo4j help) | **High (LLM reasoning)** |
| Độ phức tạp | Thấp | Cao (nhiều stage) | **Thấp (2 agent)** |
| Maintenance | Dễ | Khó (nhiều dep) | **Dễ (LLM + prompt)** |

---

## 2. Tổng quan kiến trúc mới

### 2.1 Hai pipeline chính

```
PIPELINE 1: CV PARSING (chạy 1 lần khi user upload CV)
════════════════════════════════════════════════════════════
CV file (PDF/image)
  │
  ▼
┌──────────────────────────────────────┐
│  CV Parsing Pipeline (LangGraph)      │
│                                      │
│  Node 1: OCR / Direct extract        │
│  Node 2: LLM structured parsing      │ ← Tạo CVParsedData
│  Node 3: Skill extraction + normalize│
│  Node 4: PII masking + validation    │
│  Node 5: Persist to DB              │
└──────────────────────────────────────┘
  │
  ▼
Database: user_cvs + cv_parsed_data (JSON col)
  ← Lưu structured CV để dùng lại nhiều lần

PIPELINE 2: GAP ANALYSIS (chạy mỗi khi user chọn JD)
════════════════════════════════════════════════════════════
Trigger: User chọn JD hoặc paste JD text
  │
  ▼
┌──────────────────────────────────────┐
│  Gap Analysis Pipeline (LangGraph)    │
│                                      │
│  Node 1: Load CV parsed data         │
│  Node 2: Extract JD requirements      │ ← LLM
│  Node 3: Gap Analysis (FULL CONTEXT) │ ← LLM HOLISTIC
│  Node 4: Course recommendation       │ ← LLM guided
│  Node 5: Roadmap synthesis           │ ← LLM
│  Node 6: Cache + persist            │
└──────────────────────────────────────┘
  │
  ▼
UserAnalysis result_json
```

### 2.2 Knowledge Layer đơn giản hóa

```
KNOWLEDGE LAYER v3.0
═════════════════════

PostgreSQL
├── user_cvs (raw_text, cv_parsed_json)
│   └── cv_parsed_json: structured CV (skills[], work_history[], education[])
├── jobs (raw_text, extracted_requirements_json)
│   └── extracted_requirements_json: list[skill dict]
├── courses (title, tags[], vector[1536], level, platform, cert)
├── user_analysis (result_json) ← final report
└── user_feedback (rating, is_accurate, missing_skills)

Redis
├── db=0: Auth session
├── db=1: Celery queue
├── db=2: Gap result cache (TTL 30 phút) ← dùng lại
└── db=3: LLM response cache

← KHÔNG CÓ Neo4j
```

### 2.3 Orchestration Layer

```
ORCHESTRATOR (LangGraph — Gap v3)
════════════════════════════════════

State = {
  cv_id, user_id, jd_text, job_id, jd_context,
  cv_parsed: CVParsedData,         ← từ DB (parsed rồi)
  jd_requirements: List[Dict],    ← từ JD extract node
  gap_analysis: GapAnalysis,       ← từ LLM holistic
  course_recommendations: List,    ← từ LLM guided
  roadmap: CareerRoadmap,          ← từ LLM
  final_report: Dict,
  status, error
}

Flow:
  ┌──────────────┐   ┌──────────────┐   ┌───────────────────┐
  │ load_cv_data │ → │ extract_jd   │ → │ gap_analysis_llm  │
  │ (Node 1)     │   │ (Node 2)     │   │ (Node 3) HOLISTIC │
  └──────────────┘   └──────────────┘   └─────────┬─────────┘
                                                 │
                                                 ▼
                                 ┌───────────────────────────┐
                                 │ course_recommendation_llm │
                                 │ (Node 4) LLM-guided       │
                                 └─────────┬─────────────────┘
                                           │
                                           ▼
                                 ┌───────────────────────────┐
                                 │ roadmap_synthesis_llm    │
                                 │ (Node 5) LLM-driven       │
                                 └─────────┬─────────────────┘
                                           │
                                           ▼
                                 ┌───────────────────────────┐
                                 │ finalize_report          │
                                 │ (Node 6) cache + persist  │
                                 └───────────────────────────┘
```

---

## 3. Kiến trúc chi tiết từng Agent

### 3.1 Pipeline 1: CV Parsing Agent

**Mục tiêu:** Parse CV → structured data → lưu vào DB (chạy 1 lần)

```python
# ─── worker/langgraph_agents/gap_v3/nodes/cv_parsing_nodes.py ──────────

class CVParsingState(TypedDict):
    cv_id: str
    user_id: str
    raw_text: str             # Raw text từ OCR/direct extract
    is_ocr: bool              # Cờ báo CV được xử lý từ ảnh
    cv_parsed: Optional[CVParsedData]  # Structured output
    status: str
    error: Optional[str]


class CVParsedData(TypedDict, total=False):
    """Structured CV data — lưu vào DB để dùng lại."""
    full_name: str
    summary: str
    seniority: str             # Junior / Mid-level / Senior / Expert
    experience_years_total: float

    skills: List[Dict]         # [{name, level, years_exp, last_used, context}]
    work_history: List[Dict]   # [{position, company, duration_years, description, skills_used}]
    education: List[Dict]      # [{degree, institution, year, field}]
    certifications: List[Dict]  # [{name, issuer, year}]

    # Metadata
    is_ocr: bool
    ocr_confidence: float
    raw_text_masked: str       # Đã mask PII, dùng cho LLM


async def ocr_or_extract_node(state: CVParsingState) -> CVParsingState:
    """
    Node 1: Trích xuất text từ CV file.
    Ưu tiên dùng hybrid strategy đã có (direct → OCR fallback).
    """
    cv_id = state["cv_id"]
    db = state["db"]

    cv_record = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
    if not cv_record:
        return {**state, "error": "CV not found", "status": "failed"}

    # Nếu đã có raw_text trong DB (từ bước upload), dùng lại
    if cv_record.raw_text and len(cv_record.raw_text) > 100:
        return {**state, "raw_text": cv_record.raw_text, "is_ocr": False, "status": "text_extracted"}

    # Nếu chưa có → gọi hybrid extraction
    file_path = cv_record.file_path  # Từ file storage
    result = await extract_cv_hybrid(file_path)

    return {
        **state,
        "raw_text": result.get("raw_text", ""),
        "is_ocr": result.get("is_ocr", False),
        "status": "text_extracted"
    }


async def llm_parse_cv_node(state: CVParsingState) -> CVParsingState:
    """
    Node 2: Dùng LLM parse raw text → structured CVParsedData.
    Đây là bước quan trọng nhất — tạo structured data để dùng lại nhiều lần.
    """
    raw_text = state["raw_text"]
    is_ocr = state.get("is_ocr", False)

    if not raw_text:
        return {**state, "error": "Empty raw text", "status": "failed"}

    # PII mask trước khi gửi LLM
    masked_text = mask_pii(raw_text)

    prompt = f"""Bạn là chuyên gia phân tích CV kỹ thuật. Parse CV sau thành JSON có cấu trúc.

## CV:
{masked_text}

## Nguyên tắc:
1. Trích xuất TẤT CẢ kỹ năng kỹ thuật (không phải soft skills)
2. Với mỗi kỹ năng: ghi rõ level (Beginner/Intermediate/Advanced/Expert), số năm kinh nghiệm
3. Work history: ghi rõ technologies/tools dùng tại mỗi vị trí
4. Nếu CV từ OCR (flag is_ocr=True): ưu tiên độ chính xác, đánh dấu confidence thấp
5. Seniority: đoán dựa trên tổng năm kinh nghiệm + mô tả công việc

## Output Schema:
{{
  "full_name": "<tên đầy đủ, hoặc 'Không xác định'>",
  "summary": "<tóm tắt chuyên nghiệp 2-3 câu>",
  "seniority": "Junior | Mid-level | Senior | Expert",
  "experience_years_total": <số năm kinh nghiệm tổng>,
  "skills": [
    {{
      "name": "<tên kỹ năng>",
      "level": "Beginner | Intermediate | Advanced | Expert",
      "years_exp": <số năm>,
      "last_used": <năm gần nhất dùng, null nếu không biết>,
      "context": "<mô tả ngắn cách dùng kỹ năng này>"
    }}
  ],
  "work_history": [
    {{
      "position": "<tên vị trí>",
      "company": "<công ty>",
      "duration_years": <số năm>,
      "description": "<mô tả công việc, dự án, technologies dùng>",
      "skills_used": ["<skill1>", "<skill2>"]
    }}
  ],
  "education": [
    {{
      "degree": "<bằng cấp>",
      "institution": "<trường>",
      "year": <năm tốt nghiệp>,
      "field": "<ngành>"
    }}
  ],
  "certifications": [
    {{
      "name": "<tên chứng chỉ>",
      "issuer": "<tổ chức cấp>",
      "year": <năm>
    }}
  ],
  "ocr_confidence": <0.0-1.0, đánh giá độ chính xác của parse>
}}

CHỈ trả về JSON hợp lệ. Nếu CV không có thông tin, dùng null hoặc []."""

    result = await _llm_json_completion(prompt, "")
    parsed: CVParsedData = {
        "full_name": result.get("full_name") or "",
        "summary": result.get("summary") or "",
        "seniority": result.get("seniority") or "Unknown",
        "experience_years_total": float(result.get("experience_years_total") or 0),
        "skills": result.get("skills") or [],
        "work_history": result.get("work_history") or [],
        "education": result.get("education") or [],
        "certifications": result.get("certifications") or [],
        "is_ocr": is_ocr,
        "ocr_confidence": float(result.get("ocr_confidence") or (0.5 if is_ocr else 1.0)),
        "raw_text_masked": masked_text
    }

    return {**state, "cv_parsed": parsed, "status": "parsed"}


async def persist_cv_data_node(state: CVParsingState) -> CVParsingState:
    """
    Node 3: Lưu cv_parsed vào DB.
    Lưu dưới dạng JSON column trong user_cvs hoặc bảng riêng.
    """
    db = state["db"]
    cv_id = state["cv_id"]
    parsed: CVParsedData = state["cv_parsed"]

    if not parsed:
        return {**state, "status": "failed", "error": "No parsed data"}

    cv_record = db.query(UserCV).filter(UserCV.id == uuid.UUID(cv_id)).first()
    if cv_record:
        cv_record.cv_parsed_json = parsed           # JSON col
        cv_record.experience_years_total = parsed.get("experience_years_total", 0)
        cv_record.status = "completed"
        db.commit()

    # Upsert skills vào skills table + user_skill_profile
    await _upsert_skills(parsed.get("skills", []), cv_id, db)

    logger.info(f"CV Parsed & Persisted: {cv_id}, {len(parsed.get('skills', []))} skills")
    return {**state, "status": "persisted"}
```

**Tại sao parse CV lưu lại?**
- CV được parse **1 lần** → dùng cho **nhiều lần** gap analysis (mỗi JD khác nhau)
- Structured data → không cần re-parse mỗi lần
- `cv_parsed_json` column lưu trong `user_cvs` table
- Skills được upsert vào `skills` + `user_skill_profile` table

---

### 3.2 Pipeline 2: Gap Analysis Agent

**Mục tiêu:** LLM tính gap TỔNG QUAN từ FULL CV + FULL JD context

```python
# ─── worker/langgraph_agents/gap_v3/nodes/gap_nodes.py ───────────────

class GapAnalysisStateV3(TypedDict):
    cv_id: str
    user_id: str
    jd_text: Optional[str]
    job_id: Optional[str]
    jd_context: str
    db: Any

    # From DB (parsed CV)
    cv_parsed: Optional[CVParsedData]

    # From JD extract
    jd_requirements: Optional[List[Dict]]
    jd_parsed: Optional[Dict]

    # Output
    gap_analysis: Optional[GapAnalysisResult]
    course_recommendations: Optional[List[Dict]]
    career_roadmap: Optional[Dict]
    final_report: Optional[Dict]
    status: str
    error: Optional[str]


async def load_cv_parsed_data_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    Node 1: Load CV parsed data từ DB.
    → Không cần re-parse CV mỗi lần.
    """
    db = state["db"]
    cv_id = state["cv_id"]

    cv_record = db.query(UserCV).filter(
        UserCV.id == uuid.UUID(cv_id)
    ).first()

    if not cv_record:
        return {**state, "error": "CV not found", "status": "failed"}

    parsed = cv_record.cv_parsed_json  # Đọc từ JSON col
    if not parsed:
        # Fallback: gọi CV parsing pipeline
        parsed = await _run_cv_parsing_pipeline(cv_id, state["user_id"], db)

    logger.info(f"Loaded CV parsed data: {len(parsed.get('skills', []))} skills, "
               f"{len(parsed.get('work_history', []))} work entries")

    return {**state, "cv_parsed": parsed, "status": "cv_loaded"}


async def extract_jd_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    Node 2: Extract JD requirements bằng LLM.
    Tương tự RequirementRetriever._ai_extract() nhưng chuẩn hóa output.
    """
    jd_text = state.get("jd_text") or ""

    # Thử cache trước
    cache_key = f"jd_extracted:{hashlib.md5(jd_text.encode()).hexdigest()[:16]}"
    cached = result_cache.get(cache_key)
    if cached:
        jd_parsed = json.loads(cached)
        return {**state, "jd_parsed": jd_parsed, "jd_requirements": jd_parsed.get("requirements", []), "status": "jd_extracted"}

    prompt = f"""Bạn là chuyên gia tuyển dụng kỹ thuật. Trích xuất yêu cầu từ JD sau.

## Job Description:
{jd_text}

## Quy tắc:
1. Chỉ trích xuất kỹ năng KỸ THUẬT (không phải soft skills, spoken languages)
2. Với mỗi skill: ghi rõ target level, số năm kinh nghiệm yêu cầu, có bắt buộc không
3. Nếu JD nói "hiểu Docker" → level=Junior, years=0
4. Nếu JD nói "3 năm Kubernetes" → level=Mid-level, years=3
5. Nếu có alternative (VD: "Java or Kotlin") → tạo OR group
6. Đánh dấu weight: bắt buộc=8-10, tùy chọn=3-5

## Output:
{{
  "job_title": "<tên vị trí>",
  "company_context": "<mô tả công ty, ngành nếu có>",
  "requirements": [
    {{
      "skill": "<tên skill>",
      "target_level": "Junior | Mid-level | Senior | Expert",
      "years_required": <số năm, 0 nếu không nói>,
      "is_mandatory": true|false,
      "importance_weight": <1-10>,
      "type": "skill | group",
      "group_skills": [<nếu là group>],
      "group_strategy": "AND | OR"
    }}
  ],
  "overall_requirements_count": <tổng số skills>
}}

CHỈ trả về JSON hợp lệ."""

    result = await _llm_json_completion(prompt, state.get("jd_context", ""))

    jd_parsed = {
        "job_title": result.get("job_title", state.get("jd_context", "")),
        "company_context": result.get("company_context", ""),
        "requirements": result.get("requirements") or [],
        "overall_requirements_count": result.get("overall_requirements_count", 0)
    }

    # Cache
    result_cache.setex(cache_key, 3600, json.dumps(jd_parsed))

    return {**state, "jd_parsed": jd_parsed, "jd_requirements": jd_parsed["requirements"], "status": "jd_extracted"}


async def gap_analysis_llm_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    Node 3: CORE — LLM tính gap TỔNG QUAN từ FULL context.

    Đây là điểm khác biệt cốt lõi so với v1/v2:
    → Không chia nhỏ từng skill
    → Đưa TOÀN BỘ CV + TOÀN BỘ JD vào 1 LLM call
    → LLM suy luận holistic về sự phù hợp tổng thể
    """
    logger.info("--- [GAP v3] HOLISTIC GAP ANALYSIS NODE ---")

    cv_parsed: CVParsedData = state["cv_parsed"]
    jd_requirements = state.get("jd_requirements", [])
    jd_context = state.get("jd_context", state.get("jd_parsed", {}).get("job_title", ""))

    # Format CV cho LLM (từ structured data)
    cv_formatted = _format_cv_for_llm(cv_parsed)

    # Format JD cho LLM
    jd_formatted = _format_jd_for_llm(jd_requirements)

    system_prompt = """Bạn là chuyên gia phân tích sự phù hợp nghề nghiệp cấp cao.
Nguyên tắc:
1. Đánh giá DỰA TRÊN NGỮ CẢNH TOÀN CỤC — không chỉ liệt kê skill đơn lẻ
2. Nhận diện "transferable skills" một cách TỰ NHIÊN: nếu user có Python 5 năm, học FastAPI trong 2-4 tuần
3. Phân biệt GAP "thực sự" (cần học dài hạn) vs GAP "mềm" (có nền tảng, học nhanh)
4. Severity đánh theo: job impact × learning effort × market demand
5. Đưa ra learning path CỤ THỂ: từng bước, có ước tính thời gian
6. Luôn viết bằng tiếng Việt."""

    user_prompt = f"""## ===== HỒ SƠ ỨNG VIÊN (PARSED) =====
{cv_formatted}

## ===== YÊU CẦU CÔNG VIỆC =====
{jd_formatted}

## ===== NHIỆM VỤ =====
Phân tích toàn diện sự phù hợp và đưa ra JSON:

{{
  "overall_match_pct": <0-100, đánh giá TỔNG THỂ>,
  "overall_assessment": "<nhận xét tổng thể 2-3 câu, dựa trên ngữ cảnh thực tế>",

  "strengths": [
    "<điểm mạnh cụ thể dựa trên work history + seniority, có bằng chứng>"
  ],
  "weaknesses": [
    "<điểm yếu cụ thể, có giải thích tại sao là yếu tố cản trở>"
  ],

  "skill_gaps": [
    {{
      "skill": "<tên skill>",
      "severity": "HIGH | MEDIUM | LOW",
      "is_critical": true|false,
      "status": "GAP | PARTIAL",
      "current_level": "<level hiện tại của user, null nếu không có>",
      "required_level": "<level JD yêu cầu>",
      "years_gap": <số năm thiếu, 0 nếu không có kinh nghiệm>,
      "bridge_from": "<skill đã có mà có thể chuyển đổi, null nếu không có>",
      "learning_effort": "EASY (<1 tháng) | MEDIUM (1-3 tháng) | HARD (3-6 tháng) | EXPERT (>6 tháng)",
      "estimated_months": <số tháng học realistic>,
      "learning_path": "<lộ trình cụ thể, VD: Docker basics → K8s intro → K8s advanced>"
    }}
  ],

  "gap_summary": {{
    "total_gaps": <số>,
    "critical_gaps": <số severity HIGH>,
    "soft_gaps": <số severity MEDIUM/LOW có bridge skill>,
    "estimated_total_months": <tổng tháng học tất cả gaps>,
    "blocking_skills": ["<skill nghiêm trọng nhất, không học thì không được nhận>"
  }},

  "transferable_insights": [
    "<điểm mạnh có thể chuyển đổi, ví dụ: '5 năm Python backend → học Go/FastAPI trong 2-4 tuần'>"
  ]
}}

QUAN TRỌNG:
- sort skill_gaps theo severity: HIGH → MEDIUM → LOW
- bridge_from chỉ ghi khi CÓ transferable skill tự nhiên
- learning_path phải CỤ THỂ: tên tool/khoá học cụ thể
- CHỈ trả về JSON hợp lệ""" ""

    result = await _llm_json_completion(system_prompt, user_prompt, jd_context)

    gap_analysis: GapAnalysisResult = {
        "overall_match_pct": float(result.get("overall_match_pct", 0)),
        "overall_assessment": result.get("overall_assessment", ""),
        "strengths": result.get("strengths") or [],
        "weaknesses": result.get("weaknesses") or [],
        "skill_gaps": result.get("skill_gaps") or [],
        "gap_summary": result.get("gap_summary") or {},
        "transferable_insights": result.get("transferable_insights") or [],
        "jd_context": jd_context
    }

    logger.info(f"  Gap analysis done: {gap_analysis['overall_match_pct']}% match, "
               f"{len(gap_analysis['skill_gaps'])} gaps, "
               f"blocking: {gap_analysis['gap_summary'].get('blocking_skills', [])}")

    return {**state, "gap_analysis": gap_analysis, "status": "gap_analyzed"}


def _format_cv_for_llm(cv_parsed: CVParsedData) -> str:
    """Format structured CV parsed data thành text cho LLM."""
    skills = cv_parsed.get("skills", [])
    work_history = cv_parsed.get("work_history", [])
    education = cv_parsed.get("education", [])
    certs = cv_parsed.get("certifications", [])

    # Skills
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

    # Work history
    work_lines = []
    for w in work_history:
        dur = w.get("duration_years", 0)
        skills_used = ", ".join(w.get("skills_used", [])[:8])
        work_lines.append(
            f"  - [{dur:.1f} năm] {w.get('position', 'N/A')} @ {w.get('company', 'N/A')}\n"
            f"    {w.get('description', '')[:200]}\n"
            f"    Technologies: {skills_used}"
        )
    work_text = "\n".join(work_lines) or "  (Không có kinh nghiệm)"

    # Education
    edu_lines = []
    for e in education:
        edu_lines.append(
            f"  - {e.get('degree', '')} - {e.get('field', '')} @ {e.get('institution', '')} ({e.get('year', '')})"
        )
    edu_text = "\n".join(edu_lines) or "  (Không có thông tin)"

    # Certifications
    cert_text = ""
    if certs:
        cert_lines = [f"  - {c.get('name', '')} ({c.get('issuer', '')}, {c.get('year', '')})"
                     for c in certs]
        cert_text = "\n## CHỨNG CHỈ\n" + "\n".join(cert_lines)

    seniority = cv_parsed.get("seniority", "Unknown")
    exp_total = cv_parsed.get("experience_years_total", 0)

    return f"""## TỔNG QUAN
Seniority: {seniority} | Tổng kinh nghiệm: {exp_total:.1f} năm
{ cv_parsed.get('summary', '') }

## KỸ NĂNG KỸ THUẬT
{skills_text}

## KINH NGHIỆM LÀM VIỆC
{work_text}

## HỌC VẤN
{edu_text}
{cert_text}"""


def _format_jd_for_llm(jd_requirements: List[Dict]) -> str:
    """Format JD requirements thành text cho LLM."""
    if not jd_requirements:
        return "  (Không có yêu cầu cụ thể)"

    lines = []
    for req in jd_requirements:
        mandatory_tag = "🔴 BẮT BUỘC" if req.get("is_mandatory") else "⚪ TÙY CHỌN"
        level = req.get("target_level", "Mid-level")
        years = req.get("years_required", 0)
        weight = req.get("importance_weight", 5)
        skill_name = req.get("skill", req.get("group_name", "Unknown"))

        if req.get("type") == "group":
            group_skills = ", ".join([s.get("skill", "?") for s in req.get("group_skills", [])])
            strategy = "OR (cần ít nhất 1)" if req.get("group_strategy") == "OR" else "AND (cần tất cả)"
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


# ─── Type definitions ────────────────────────────────────────────────────

class GapAnalysisResult(TypedDict, total=False):
    overall_match_pct: float
    overall_assessment: str
    strengths: List[str]
    weaknesses: List[str]
    skill_gaps: List["SkillGap"]
    gap_summary: "GapSummary"
    transferable_insights: List[str]
    jd_context: str


class SkillGap(TypedDict, total=False):
    skill: str
    severity: str               # HIGH | MEDIUM | LOW
    is_critical: bool
    status: str                # GAP | PARTIAL
    current_level: Optional[str]
    required_level: str
    years_gap: float
    bridge_from: Optional[str]
    learning_effort: str        # EASY | MEDIUM | HARD | EXPERT
    estimated_months: float
    learning_path: str


class GapSummary(TypedDict, total=False):
    total_gaps: int
    critical_gaps: int
    soft_gaps: int
    estimated_total_months: float
    blocking_skills: List[str]
```

---

## 4. Data Model — CV Parsed Structure

### 4.1 Database Schema Changes

```python
# ─── shared/models.py — Thêm CVParsedData model ─────────────────────────

# Option A: JSON column trong user_cvs (đơn giản nhất)
class UserCV(Base):
    # ... existing fields ...
    cv_parsed_json = Column(JSON)     # ← THÊM MỚI: structured CV data
    cv_parsed_at = Column(DateTime)   # ← THÊM MỚI: timestamp

# Option B: Tạo bảng riêng (nếu muốn query phức tạp hơn)
class CVParsedData(Base):
    __tablename__ = "cv_parsed_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cv_id = Column(UUID(as_uuid=True), ForeignKey("user_cvs.id", ondelete="CASCADE"))
    full_name = Column(String(255))
    summary = Column(Text)
    seniority = Column(String(20))
    experience_years_total = Column(Float)

    # Structured fields as JSON
    skills_json = Column(JSON)         # List[SkillItem]
    work_history_json = Column(JSON)   # List[WorkItem]
    education_json = Column(JSON)      # List[EduItem]
    certifications_json = Column(JSON)

    is_ocr = Column(Boolean, default=False)
    ocr_confidence = Column(Float, default=1.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    cv = relationship("UserCV", back_populates="cv_parsed_data")

# Relationship update:
class UserCV(Base):
    # ... existing ...
    cv_parsed_data = relationship("CVParsedData", back_populates="cv")
```

### 4.2 Upsert Skills vào DB

```python
# ─── Skill upsert từ CV parsed data ─────────────────────────────────────

async def _upsert_skills(skills: List[Dict], cv_id: str, db: Session):
    """Upsert skills từ CV parsed vào skills + user_skill_profile table."""
    for s in skills:
        skill_name = s.get("name", "")
        if not skill_name:
            continue

        # Upsert Skill
        skill = db.query(Skill).filter(Skill.name == skill_name).first()
        if not skill:
            skill = Skill(name=skill_name, category="Technology")
            db.add(skill)
            db.flush()

        # Upsert UserSkillProfile
        existing_profile = db.query(UserSkillProfile).filter(
            UserSkillProfile.cv_id == uuid.UUID(cv_id),
            UserSkillProfile.skill_id == skill.id
        ).first()

        level_map = {
            "Beginner": "Junior",
            "Intermediate": "Mid-level",
            "Advanced": "Senior",
            "Expert": "Expert"
        }

        profile_data = {
            "years_exp": float(s.get("years_exp") or 0),
            "level": level_map.get(s.get("level"), "Junior"),
            "last_used_year": s.get("last_used"),
            "skill_context": s.get("context"),
            "cv_id": uuid.UUID(cv_id),
            "source": "cv_parsed"
        }

        if existing_profile:
            for key, val in profile_data.items():
                setattr(existing_profile, key, val)
        else:
            new_profile = UserSkillProfile(
                id=uuid.uuid4(),
                skill_id=skill.id,
                **profile_data
            )
            db.add(new_profile)

    db.commit()
```

---

## 5. Gap Analysis Agent — Single LLM Full Context

### 5.1 Tại sao "holistic" tốt hơn "skill-by-skill"?

**Phân tích so sánh:**

```
Scenario: Senior Backend Engineer (6 năm Python, Django, PostgreSQL)
JD: Senior Backend — Python, FastAPI, Kubernetes, Terraform, Postgres

Skill-by-skill (Vector Engine v1/v2):
═══════════════════════════════════════
Kubernetes  → match: 0%   → GAP
Terraform   → match: 0%   → GAP
FastAPI     → match: 0%   → GAP
PostgreSQL  → match: 80%  → MET
Python      → match: 100% → MET
→ Overall: 40% match

LLM Holistic (v3):
═══════════════════════════════════════
"Ứng viên có 6 năm Python backend, dùng Django + PostgreSQL.
Học FastAPI là chuyển đổi async framework trong 3-4 tuần.
Kubernetes và Terraform thuộc DevOps stack — cần học thêm 2-3 tháng
nhưng có kinh nghiệm deploy Django, dễ chuyển sang K8s.
→ Overall: 72% match, thực chất phù hợp cao"
```

**Kết luận:** LLM holistic hiểu được ngữ cảnh, suy luận transferable tự nhiên → kết quả sát thực hơn.

### 5.2 Output Schema

```json
{
  "overall_match_pct": 72.5,
  "overall_assessment": "Ứng viên phù hợp 72.5% cho vị trí Senior Backend. "
    + "Điểm mạnh: 6 năm Python backend với Django và PostgreSQL. "
    + "Cần bổ sung Kubernetes và Terraform trong 2-3 tháng.",

  "strengths": [
    "6 năm kinh nghiệm Python backend, chuyên Django và FastAPI tương đương",
    "Có kinh nghiệm với PostgreSQL ở mức advanced (đã thiết kế schema phức tạp)",
    "Seniority level phù hợp với JD yêu cầu"
  ],

  "weaknesses": [
    "Không có kinh nghiệm Kubernetes trong production — đây là DevOps requirement bắt buộc",
    "Terraform là công cụ mới, chưa dùng Infrastructure-as-Code trong workflow hiện tại"
  ],

  "skill_gaps": [
    {
      "skill": "Kubernetes",
      "severity": "HIGH",
      "is_critical": true,
      "status": "GAP",
      "current_level": null,
      "required_level": "Mid-level",
      "years_gap": 0,
      "bridge_from": "Docker (đã dùng 3 năm trong production)",
      "learning_effort": "MEDIUM",
      "estimated_months": 3,
      "learning_path": "Docker fundamentals → K8s basics (Minikube) → K8s deployments → Helm charts → ArgoCD"
    },
    {
      "skill": "Terraform",
      "severity": "HIGH",
      "is_critical": false,
      "status": "GAP",
      "current_level": null,
      "required_level": "Junior",
      "years_gap": 0,
      "bridge_from": "Shell scripting và Ansible (có kinh nghiệm)",
      "learning_effort": "MEDIUM",
      "estimated_months": 2,
      "learning_path": "IaC concepts → Terraform basics → AWS provider → GCP provider → Terragrunt"
    }
  ],

  "gap_summary": {
    "total_gaps": 2,
    "critical_gaps": 1,
    "soft_gaps": 1,
    "estimated_total_months": 3.5,
    "blocking_skills": ["Kubernetes"]
  },

  "transferable_insights": [
    "Django → FastAPI: async framework tương tự, chuyển đổi trong 3-4 tuần",
    "Docker 3 năm → Kubernetes: có nền tảng container, học K8s nhanh hơn người mới",
    "PostgreSQL 6 năm → đủ để làm việc với bất kỳ SQL database nào"
  ]
}
```

---

## 6. Course Recommendation Agent

### 6.1 Kiến trúc

```
Agent 2: Course Recommendation (LLM-Guided, 2-step)
══════════════════════════════════════════════════════

Input: skill_gaps[] từ Agent 1 (đã sort HIGH → MEDIUM → LOW)

Step 1: Top 3 Gaps Filter (LLM)
────────────────────────────
→ LLM chọn TOP 3 gaps CẦN HỌC NHẤT:
  - Severity HIGH + is_critical = True → ưu tiên
  - Có transferable bridge → học nhanh → ưu tiên (ROI cao)
  - Duration ngắn + impact cao → ưu tiên
→ Bỏ qua LOW severity (dễ tự học)

Step 2: Course Search per Gap
────────────────────────────
Với mỗi gap skill:
  a. pgvector similarity search courses (threshold > 0.65)
     → Lấy top 10 candidates
  b. LLM chọn TOP 2 phù hợp nhất
     (level, duration, certification, platform quality)

Step 3: Final Ranking (LLM)
────────────────────────────
→ Deduplicate (tránh trùng khóa học giữa các gap)
→ Rank theo: severity × certification × duration
→ LLM viết selection_reason cho từng course
```

### 6.2 Implementation

```python
# ─── worker/langgraph_agents/gap_v3/nodes/course_nodes.py ──────────────

async def course_recommendation_llm_node(state: GapAnalysisStateV3) -> GapAnalysisStateV3:
    """
    Node 4: Course Recommendation Agent.
    Tìm và rank khóa học cho TOP 3 skill gaps (yếu nhất + cần thiết nhất).
    """
    logger.info("--- [GAP v3] COURSE RECOMMENDATION NODE ---")

    gap_analysis: GapAnalysisResult = state.get("gap_analysis")
    if not gap_analysis:
        return {**state, "course_recommendations": [], "status": "courses_done"}

    skill_gaps = gap_analysis.get("skill_gaps", [])
    jd_context = gap_analysis.get("jd_context", "")

    if not skill_gaps:
        return {**state, "course_recommendations": [], "status": "courses_done"}

    # ── Step 1: LLM Prioritize TOP 3 Gaps ──────────────────────────────
    top_gaps = await _llm_prioritize_top_gaps(skill_gaps, jd_context)

    logger.info(f"  Top {len(top_gaps)} gaps prioritized for courses: "
                f"{[g['skill'] for g in top_gaps]}")

    # ── Step 2: Vector Search + LLM Select ───────────────────────────
    all_recommendations = []

    for gap in top_gaps:
        gap_skill = gap["skill"]
        target_level = gap.get("required_level", "Mid-level")
        estimated_months = gap.get("estimated_months", 3)

        # 2a. Vector search candidates
        course_candidates = await _vector_search_courses(
            skill_name=gap_skill,
            target_level=target_level,
            db=state["db"],
            limit=10
        )

        # 2b. LLM chọn TOP 2
        selected = await _llm_select_best_courses(
            gap=gap,
            candidates=course_candidates,
            jd_context=jd_context
        )

        for course in selected:
            course["gap_skill"] = gap_skill
            course["gap_severity"] = gap.get("severity", "MEDIUM")
            course["gap_learning_path"] = gap.get("learning_path", "")
            course["gap_estimated_months"] = estimated_months
            course["is_critical"] = gap.get("is_critical", False)
            all_recommendations.append(course)

    # ── Step 3: Deduplicate + Rank ────────────────────────────────────
    course_recommendations = _deduplicate_and_rank(all_recommendations)

    logger.info(f"  Final: {len(course_recommendations)} unique courses selected")

    return {
        **state,
        "course_recommendations": course_recommendations,
        "status": "courses_done"
    }


async def _llm_prioritize_top_gaps(skill_gaps: List[Dict], jd_context: str) -> List[Dict]:
    """LLM chọn TOP 3 gaps cần học nhất, ưu tiên weakest + most critical."""
    gaps_str = "\n".join([
        f"- #{i+1} {g['skill']} | severity: {g['severity']} | "
        f"critical: {g.get('is_critical')} | "
        f"months: {g.get('estimated_months')} | "
        f"learning_effort: {g.get('learning_effort')} | "
        f"bridge_from: {g.get('bridge_from', 'none')} | "
        f"learning_path: {g.get('learning_path','')}"
        for i, g in enumerate(skill_gaps)
    ])

    prompt = f"""Bạn là chuyên gia tư vấn học tập. Chọn TOP 3 skill gaps ƯU TIÊN NHẤT để lấp gap.

## Job Context: {jd_context}

## All Skill Gaps:
{gaps_str}

## Quy tắc ưu tiên:
1. HIGH severity + is_critical=True → học TRƯỚC (job requirement thiết yếu)
2. Có bridge_from (transferable) → học NHANH (ROI cao) → ưu tiên
3. estimated_months ≤ 3 → có thể hoàn thành trước khi apply
4. LOW severity → bỏ qua (dễ tự học, không cần course)

## Output JSON:
{{
  "top_gaps": [
    {{
      "skill": "<tên>",
      "severity": "HIGH|MEDIUM|LOW",
      "is_critical": true|false,
      "priority_rank": <1, 2, 3>,
      "estimated_months": <số tháng>,
      "bridge_from": "<skill đã có, null>",
      "learning_path": "<lộ trình>",
      "reason": "<tại sao ưu tiên skill này>"
    }}
  ]
}}
CHỈ trả về JSON hợp lệ. Tối đa 3 gaps."""

    result = await _llm_json_completion(prompt, jd_context)
    top_gaps = result.get("top_gaps", skill_gaps[:3])

    # Fallback: sort by severity + is_critical
    if not top_gaps:
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_gaps = sorted(skill_gaps, key=lambda g: (
            severity_order.get(g.get("severity", "LOW"), 2),
            -int(g.get("is_critical", False))
        ))
        top_gaps = sorted_gaps[:3]

    return top_gaps


async def _vector_search_courses(skill_name: str, target_level: str, db, limit: int = 10) -> List[Dict]:
    """pgvector similarity search cho courses."""
    from shared.llm_utils import get_embedding

    search_text = f"{skill_name} {target_level} course tutorial"
    skill_vector = get_embedding(search_text)

    if not skill_vector:
        return []

    query = text("""
        SELECT id, title, platform, url, level, provider,
               duration_hours, is_certification, cost_usd, tags,
               1 - (vector <=> :vec::vector) as similarity
        FROM courses
        WHERE vector IS NOT NULL
          AND 1 - (vector <=> :vec::vector) > 0.60
        ORDER BY similarity DESC
        LIMIT :limit
    """)

    results = db.execute(query, {"vec": skill_vector, "limit": limit}).fetchall()

    return [
        {
            "course_id": str(r.id),
            "title": r.title,
            "platform": r.platform,
            "url": r.url,
            "level": r.level,
            "provider": r.provider,
            "duration_hours": r.duration_hours or 0,
            "is_certification": bool(r.is_certification),
            "cost_usd": r.cost_usd or 0,
            "tags": r.tags or [],
            "similarity": float(r.similarity)
        }
        for r in results
    ]


async def _llm_select_best_courses(gap: Dict, candidates: List[Dict], jd_context: str) -> List[Dict]:
    """LLM chọn TOP 2 courses phù hợp nhất cho 1 gap skill."""
    if not candidates:
        return []

    skill_name = gap["skill"]
    required_level = gap.get("required_level", "Mid-level")
    estimated_months = gap.get("estimated_months", 3)
    learning_path = gap.get("learning_path", "")

    candidates_str = "\n".join([
        f"- [{i+1}] {c['title']} | {c['platform']} | {c['level']} | "
        f"{c['duration_hours']}h | cert: {c['is_certification']} | "
        f"similarity: {c['similarity']:.2f} | ${c['cost_usd']} | "
        f"tags: {', '.join(c['tags'][:5])}"
        for i, c in enumerate(candidates)
    ])

    prompt = f"""Chọn TOP 2 khóa học phù hợp nhất để lấp gap "{skill_name}"
(target level: {required_level}, ước tính: {estimated_months} tháng).

## Learning path đề xuất: {learning_path}

## Available Courses ({len(candidates)} candidates):
{candidates_str}

## Quy tắc chọn:
1. Ưu tiên certification = true (giá trị trên CV)
2. Duration phù hợp: không quá 3× estimated_months (VD: 3 tháng → khóa ≤ 80 giờ)
3. Level phù hợp với gap level (Beginner cho GAP, Intermediate cho PARTIAL)
4. Platform uy tín: Udemy, Coursera, Pluralsight, LinkedIn Learning, edX
5. Free hoặc < $50 là best value
6. Khóa nào phù hợp với learning_path → ưu tiên

## Output JSON:
{{
  "selected_courses": [
    {{
      "course_id": "<id>",
      "selection_reason": "<tại sao chọn khóa này cho gap {skill_name}>"
    }}
  ]
}}
CHỈ trả về JSON hợp lệ. Top 2 thôi."""

    result = await _llm_json_completion(prompt, jd_context)
    selected_ids = [c["course_id"] for c in result.get("selected_courses", [])]

    # Map back to full course data
    course_map = {c["course_id"]: c for c in candidates}
    output = []

    for cid in selected_ids[:2]:
        course = course_map.get(cid)
        if not course:
            continue
        sel = next((s for s in result.get("selected_courses", []) if s["course_id"] == cid), {})
        output.append({
            **course,
            "selection_reason": sel.get("selection_reason", ""),
            "learning_path": learning_path
        })

    return output


def _deduplicate_and_rank(courses: List[Dict]) -> List[Dict]:
    """Deduplicate và rank theo severity × certification × similarity."""
    seen_ids = {}
    for c in courses:
        cid = c["course_id"]
        if cid not in seen_ids:
            seen_ids[cid] = c

    ranked = list(seen_ids.values())

    severity_w = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}
    for c in ranked:
        sev = severity_w.get(c.get("gap_severity", "LOW"), 0.4)
        cert = 0.2 if c.get("is_certification") else 0
        sim = c.get("similarity", 0) * 0.2
        c["rank_score"] = round(sev * 0.6 + cert * 0.2 + sim, 3)

    ranked.sort(key=lambda x: x["rank_score"], reverse=True)
    return ranked
```

---

## 7. Data Flow Tổng thể

```
USER UPLOAD CV
═════════════
  │
  ▼
[Pipeline 1: CV Parsing]
  │ OCR / Direct extract (Hybrid)
  ▼
  │ LLM structured parsing → CVParsedData
  │ Upsert skills vào DB
  │ Persist cv_parsed_json vào user_cvs
  ▼
[Database: user_cvs + cv_parsed_json + user_skill_profile]
         ↑ saved (run once)
         │
         │
USER CHỌN JD / PASTE JD TEXT
         │
         ▼
[Pipeline 2: Gap Analysis]
  │
  ├─► [Node 1: Load CV from DB] ──► cv_parsed_json
  │
  ├─► [Node 2: Extract JD] ───────► LLM extract requirements
  │                                  cache vào Redis (1h)
  ▼
  ├─► [Node 3: Gap Analysis LLM]──► LLM holistic reasoning
  │   "Dựa trên TOÀN BỘ CV + JD,    full context, 1 call
  │    hãy phân tích sự phù hợp"
  │                                  → overall_match_pct
  │                                  → skill_gaps (HIGH→MEDIUM→LOW)
  │                                  → transferable_insights
  │                                  → gap_summary
  ▼
  ├─► [Node 4: Course Recommendation]► TOP 3 gaps → vector search
  │                                     → LLM select TOP 2 per gap
  │                                     → deduplicate + rank
  ▼
  ├─► [Node 5: Roadmap Synthesis]──► LLM tạo timeline stages
  │                                     milestones per stage
  ▼
  ├─► [Node 6: Finalize + Cache + Persist]
  │   • Merge all outputs
  │   • Cache Redis db=2 (TTL 30m)
  │   • Persist vào UserAnalysis table
  ▼
[FINAL REPORT]
{
  "overall_match_pct": 72.5,
  "overall_assessment": "...",
  "strengths": [...],
  "weaknesses": [...],
  "skill_gaps": [...],         ← sort HIGH → MEDIUM → LOW
  "gap_summary": {...},
  "transferable_insights": [...],
  "course_recommendations": [
    {
      "gap_skill": "Kubernetes",
      "gap_severity": "HIGH",
      "course": { "title": "...", "platform": "Udemy", ... },
      "rank_score": 0.87,
      "selection_reason": "..."
    },
    ...
  ],
  "career_roadmap": {
    "stages": [...],
    "total_weeks": 16,
    "total_hours": 120
  },
  "notes": ["Gap Analysis Method: LLM Holistic v3"]
}
```

---

## 8. Gap so với Spec & Impl cũ

### 8.1 So sánh chi tiết

| Khía cạnh | Spec yêu cầu | v1 (Vector) | v2 (Multi-Agent) | **v3 (LLM-Centric)** |
|---|---|---|---|---|
| Gap calculation | Theo từng skill + transferable | Skill-by-skill, vector | 3-tier + Neo4j | **LLM holistic, full context** |
| Neo4j | Suy luận transferable | Không dùng | Stage 3 graph traversal | **BỎ — LLM suy luận tự nhiên** |
| CV parsing | 1 lần, reuse | Mỗi lần full text | Mỗi lần full text | **Parse 1 lần → lưu structured** |
| pgvector matching | JD vs CV skills | Stage 2 cosine | Stage 2 cosine | **Chỉ dùng cho course search** |
| Course lookup | Ưu tiên weakest/critical | ILIKE text | Vector + LLM select | **LLM prioritize TOP 3 → vector → LLM select** |
| Transferable skills | Tự cải thiện | Không có | Neo4j Stage 3 | **LLM suy luận trong holistic call** |
| PII masking | Có | Không | Không | **Mask trong CV parsing node** |
| Redis cache | 30 phút | Không dùng | Không dùng | **Cache JD extract (1h) + Gap result (30m)** |
| Feedback loop | Dynamic weight | Không | Partial | **LLM suy luận feedback context** |
| Simulation | LLM roadmap | Hardcoded | Hardcoded | **LLM roadmap trong Agent 3** |

### 8.2 Ưu điểm vượt trội của v3

```
┌──────────────────────────────────────────────────────────────┐
│  Ưu điểm v3 so với v1/v2                                     │
├──────────────────────────────────────────────────────────────┤
│  ✅ Đơn giản hóa: Bỏ Neo4j → giảm độ phức tạp infrastructure │
│  ✅ Chính xác hơn: LLM hiểu ngữ cảnh tổng thể thay vì chia  │
│     nhỏ từng skill                                          │
│  ✅ Tái sử dụng: CV parsed 1 lần → dùng nhiều JD analysis   │
│  ✅ Holistic: Transferable skills suy luận tự nhiên, không  │
│     cần graph traversal thủ công                           │
│  ✅ Maintainable: Thay đổi logic bằng prompt, không cần   │
│     sửa code multi-stage phức tạp                        │
│  ✅ Caching tốt hơn: Layer cache (JD extract 1h + Gap 30m) │
│  ✅ Structured CV: Dùng cho nhiều feature khác (profile,   │
│     market fit, trending skills)                           │
└──────────────────────────────────────────────────────────────┘
```

---

## 9. Lộ trình Triển khai

### 9.1 Cấu trúc file mới

```
backend/worker/langgraph_agents/gap_v3/
├── __init__.py
├── orchestrator.py              ← LangGraph Orchestrator v3
├── states.py                    ← TypedDict states
├── nodes/
│   ├── cv_parsing_nodes.py      ← Pipeline 1: CV Parsing
│   ├── gap_nodes.py             ← Pipeline 2: Gap Analysis Nodes
│   ├── course_nodes.py          ← Node 4: Course Recommendation
│   └── roadmap_nodes.py        ← Node 5: Roadmap Synthesis
├── utils/
│   ├── pii_masker.py           ← PII masking
│   └── llm_helpers.py          ← LLM JSON completion wrapper
├── config.py                   ← Feature flags
└── tasks/
    ├── cv_parsing_task.py      ← Celery task: CV parsing
    └── gap_analysis_v3_task.py  ← Celery task: Gap analysis
```

### 9.2 Lộ trình 3 Phase

```
Phase 1 — CV Parsing Pipeline (Week 1-2)
══════════════════════════════════════════════════════════════
 □ Implement cv_parsing_nodes.py (5 nodes)
 □ Thêm cv_parsed_json column vào UserCV model
 □ Implement _upsert_skills (từ parsed CV → skills table)
 □ Viết migration thêm bảng cv_parsed_data (optional)
 □ Trigger CV parsing khi user upload CV thành công
 □ Unit tests

Phase 2 — Gap Analysis v3 + Course Agent (Week 3-4)
══════════════════════════════════════════════════════════════
 □ Implement gap_v3 orchestrator (6 nodes)
 □ gap_analysis_llm_node (core holistic reasoning)
 □ course_recommendation_llm_node (2-step: priority → search → select)
 □ roadmap_synthesis_node
 □ finalize_report_node + Redis cache
 □ Update Celery task entry point
 □ Integration tests

Phase 3 — Reliability + Polish (Week 5-6)
══════════════════════════════════════════════════════════════
 □ JD Parsing pipeline (extract_jd_node) — replace parse_jd_task stub
 □ Feedback loop: LLM đọc feedback → adjust analysis
 □ Trending skills salary insight
 □ Performance: batch embedding, Redis tuning
 □ A/B test: v3 vs v2 latency + accuracy
 □ Documentation + deployment
```

### 9.3 Quick Wins (tuần 1)

| # | Action | Effort | Impact |
|---|---|---|---|
| QW1 | Thêm `cv_parsed_json` column + `load_cv_parsed_data_node` | 1 day | High — không cần re-parse |
| QW2 | Implement PII masking trong CV parsing | 1 day | Security compliance |
| QW3 | Rewrite `gap_analysis_llm_node` thành holistic style | 2 days | Core feature — cải thiện accuracy |
| QW4 | Vector search cho courses (thay ILIKE) | 1 day | Course quality improvement |

---

## ✅ Tóm tắt Changes chính

| # | Change | Reason |
|---|---|---|
| 1 | **Bỏ Neo4j hoàn toàn** | Không cần graph traversal; LLM suy luận transferable tự nhiên |
| 2 | **CV Parsing Pipeline: parse 1 lần → lưu structured** | Reuse cho nhiều JD; không cần re-parse mỗi analysis |
| 3 | **Gap Analysis: single LLM holistic call** | Hiểu ngữ cảnh toàn cục; không chia nhỏ skill-by-skill |
| 4 | **pgvector chỉ dùng cho course search** | Không dùng vector matching cho JD vs CV matching nữa |
| 5 | **Course Agent: 2-step (priority → vector → LLM select)** | Ưu tiên weakest + most critical trước |
| 6 | **PII masking** | Mask trước khi LLM parse CV |
| 7 | **Redis cache: JD extract 1h + Gap 30m** | Giảm redundant LLM calls |

---

*Document v3.0 — LLM-Centric Holistic Architecture. Claude Code. 2026-01-26.*