# Category System Improvements - Skill Extraction

## 📊 Tổng Quan

Document này mô tả chi tiết việc nâng cấp hệ thống phân loại skills từ **10 categories** lên **17 categories** để phù hợp hơn với ngành tech hiện đại.

---

## ❌ Vấn Đề với 10 Categories Cũ

### Categories cũ:
```
1. Programming Language
2. Framework (quá chung chung!)
3. Database
4. Cloud Platform
5. DevOps Tool
6. Development Tool
7. Methodology
8. Soft Skill
9. Domain Knowledge
10. Other Technical (catch-all, không hữu ích)
```

### Vấn đề chính:

**1. "Framework" quá chung chung**
- React (Frontend) vs Django (Backend) vs Flutter (Mobile) → Tất cả đều là "Framework"
- Không phân biệt được frontend/backend/mobile
- Gây khó khăn cho matching và filtering

**2. Thiếu categories cho specialized domains**
- Testing: Jest, Pytest, Selenium → Không có category phù hợp
- Security: OAuth, JWT → Không rõ category
- ML/AI: TensorFlow, PyTorch → Bị nhầm với "Framework"
- Data Science: Pandas, NumPy → Không có category riêng

**3. Web technologies không có chỗ đứng**
- HTML, CSS → Không phải "Programming Language"
- REST API, GraphQL → Không phải "Framework"
- Thường bị xếp vào "Other Technical"

**4. Redis/Kafka bị misclassified**
- Redis: Cache, không phải traditional database
- Kafka: Message queue, không phải database
- Nhưng thường bị xếp vào "Database"

**5. "Other Technical" là catch-all vô nghĩa**
- Mọi thứ không fit → "Other Technical"
- Không giúp ích gì cho categorization

---

## ✅ Giải Pháp: 17 Categories Mới

### Cấu trúc phân cấp:

```
CORE PROGRAMMING (5 categories)
├── Programming Language      (Python, Java, JavaScript, C++, Go, Rust, TypeScript)
├── Web Technology           (HTML, CSS, REST API, GraphQL, WebSocket, HTTP)
├── Backend Framework        (Django, Spring Boot, Express, FastAPI, Laravel)
├── Frontend Framework       (React, Vue, Angular, Svelte, Next.js)
└── Mobile Framework         (Flutter, React Native, SwiftUI, Jetpack Compose)

DATA & STORAGE (2 categories)
├── Database                 (PostgreSQL, MySQL, MongoDB, Oracle, Cassandra)
└── Caching & Queue         (Redis, Memcached, Kafka, RabbitMQ, Amazon SQS)

INFRASTRUCTURE & OPERATIONS (3 categories)
├── Cloud Platform          (AWS, Azure, GCP, DigitalOcean, Heroku)
├── DevOps & CI/CD         (Docker, Kubernetes, Jenkins, GitHub Actions, Terraform)
└── Development Tool        (Git, VS Code, IntelliJ, Postman, Jira)

SPECIALIZED DOMAINS (4 categories)
├── Testing Framework       (Jest, Pytest, Selenium, Cypress, JUnit, Mocha)
├── Security               (OAuth, JWT, SSL/TLS, Penetration Testing, OWASP)
├── Machine Learning       (TensorFlow, PyTorch, scikit-learn, Keras, YOLO)
└── Data Science           (Pandas, NumPy, Jupyter, Matplotlib, Tableau, Power BI)

PROCESS & SOFT SKILLS (3 categories)
├── Methodology            (Agile, Scrum, Kanban, TDD, BDD, Microservices, DDD)
├── Soft Skill            (Communication, Leadership, Problem Solving, Teamwork)
└── Domain Knowledge       (Finance, Healthcare, E-commerce, Fintech, EdTech)
```

---

## 🎯 Lợi Ích của 17 Categories

### 1. **Phân loại chính xác hơn**

**Trước (10 categories):**
```json
{"skill_name": "React", "category": "Framework"}
{"skill_name": "Django", "category": "Framework"}
{"skill_name": "Flutter", "category": "Framework"}
{"skill_name": "Jest", "category": "Framework"}
```
→ Tất cả đều "Framework", không phân biệt được!

**Sau (17 categories):**
```json
{"skill_name": "React", "category": "Frontend Framework"}
{"skill_name": "Django", "category": "Backend Framework"}
{"skill_name": "Flutter", "category": "Mobile Framework"}
{"skill_name": "Jest", "category": "Testing Framework"}
```
→ Rõ ràng, dễ filter và match!

### 2. **Hỗ trợ matching tốt hơn**

Khi user có skill "React", system có thể:
- Match với jobs yêu cầu "Frontend Framework"
- Không match với jobs yêu cầu "Backend Framework"
- Suggest related skills: Vue, Angular (cùng category)

### 3. **Analytics & Insights chính xác hơn**

```sql
-- Top frontend frameworks
SELECT skill_name, COUNT(*) 
FROM job_skill_requirement 
WHERE category = 'Frontend Framework'
GROUP BY skill_name;

-- Jobs requiring ML skills
SELECT job_id 
FROM job_skill_requirement 
WHERE category = 'Machine Learning';

-- Full-stack jobs (có cả frontend + backend)
SELECT job_id 
FROM job_skill_requirement 
WHERE category IN ('Frontend Framework', 'Backend Framework')
GROUP BY job_id 
HAVING COUNT(DISTINCT category) = 2;
```

### 4. **Skill recommendations tốt hơn**

```python
# Recommend skills based on category
if user_has_skill("React", "Frontend Framework"):
    recommend = [
        "TypeScript",  # Programming Language
        "Next.js",     # Frontend Framework
        "REST API",    # Web Technology
        "Jest"         # Testing Framework
    ]
```

---

## 📋 Categorization Guidelines

### Rules để tránh misclassification:

| Skill | ❌ Wrong Category | ✅ Correct Category | Lý do |
|-------|------------------|---------------------|-------|
| HTML, CSS | Programming Language | **Web Technology** | Markup/styling, không phải programming |
| REST API | Backend Framework | **Web Technology** | Architectural style, không phải framework |
| React | Backend Framework | **Frontend Framework** | UI library cho browser |
| Flutter | Frontend Framework | **Mobile Framework** | Cross-platform mobile |
| Jest | Backend Framework | **Testing Framework** | Testing tool |
| Redis | Database | **Caching & Queue** | In-memory cache |
| Kafka | Database | **Caching & Queue** | Message broker |
| OAuth | Web Technology | **Security** | Authentication protocol |
| TensorFlow | Backend Framework | **Machine Learning** | ML framework |
| Pandas | Programming Language | **Data Science** | Data analysis library |

---

## 🔧 Implementation Details

### 1. Validation Function

**File:** `backend/shared/llm_utils.py:360-377`

```python
VALID_CATEGORIES = {
    # Core Programming
    "Programming Language", "Web Technology", 
    "Backend Framework", "Frontend Framework", "Mobile Framework",
    
    # Data & Storage
    "Database", "Caching & Queue",
    
    # Infrastructure
    "Cloud Platform", "DevOps & CI/CD", "Development Tool",
    
    # Specialized
    "Testing Framework", "Security", 
    "Machine Learning", "Data Science",
    
    # Process
    "Methodology", "Soft Skill", "Domain Knowledge"
}
```

### 2. Category Mapping

**File:** `backend/shared/llm_utils.py:423-470`

Comprehensive mapping để handle variations:
```python
category_mapping = {
    "framework": "Backend Framework",  # Default
    "backend": "Backend Framework",
    "frontend": "Frontend Framework",
    "mobile": "Mobile Framework",
    "testing": "Testing Framework",
    "ml": "Machine Learning",
    "ai": "Machine Learning",
    "data science": "Data Science",
    # ... 40+ mappings
}
```

### 3. Prompt với Examples

**File:** `backend/shared/llm_utils.py:542-569`

Prompt bao gồm:
- 17 categories với examples cụ thể
- Categorization guidelines
- 5 example outputs với đúng categories

---

## 📊 Expected Impact

### Metrics Before vs After:

| Metric | Before (10 cats) | After (17 cats) | Improvement |
|--------|------------------|-----------------|-------------|
| Skills in "Other Technical" | ~15% | ~0% | ✅ Eliminated |
| Misclassified frameworks | ~30% | ~5% | ✅ 83% reduction |
| Category precision | ~70% | ~95% | ✅ 36% improvement |
| Matching accuracy | ~75% | ~90% | ✅ 20% improvement |

### Category Distribution (Expected):

```
Programming Language:  15-20%
Backend Framework:     10-15%
Frontend Framework:    8-12%
Database:             8-10%
Web Technology:       5-8%
DevOps & CI/CD:       5-8%
Cloud Platform:       5-7%
Testing Framework:    3-5%
Mobile Framework:     3-5%
Development Tool:     3-5%
Security:             2-4%
Methodology:          5-8%
Soft Skill:           5-10%
Machine Learning:     1-3%
Data Science:         1-3%
Caching & Queue:      1-2%
Domain Knowledge:     2-5%
```

---

## 🧪 Testing

### Test Cases:

**1. Frontend Stack:**
```
Input: "React, TypeScript, Next.js, HTML, CSS, REST API"
Expected:
- React → Frontend Framework
- TypeScript → Programming Language
- Next.js → Frontend Framework
- HTML → Web Technology
- CSS → Web Technology
- REST API → Web Technology
```

**2. Mobile Stack:**
```
Input: "Flutter, Dart, Firebase, iOS, Android"
Expected:
- Flutter → Mobile Framework
- Dart → Programming Language
- Firebase → Cloud Platform
- iOS → Mobile Framework (or Domain Knowledge)
- Android → Mobile Framework (or Domain Knowledge)
```

**3. ML/Data Stack:**
```
Input: "Python, TensorFlow, PyTorch, Pandas, NumPy, Jupyter"
Expected:
- Python → Programming Language
- TensorFlow → Machine Learning
- PyTorch → Machine Learning
- Pandas → Data Science
- NumPy → Data Science
- Jupyter → Data Science
```

**4. Full Stack:**
```
Input: "React, Node.js, Express, PostgreSQL, Redis, Docker, Jest"
Expected:
- React → Frontend Framework
- Node.js → Programming Language
- Express → Backend Framework
- PostgreSQL → Database
- Redis → Caching & Queue
- Docker → DevOps & CI/CD
- Jest → Testing Framework
```

---

## 🚀 Migration Plan

### Phase 1: Deploy New Code (No data migration)
```bash
# Deploy updated llm_utils.py
git pull
docker-compose restart worker
docker-compose restart service
```

### Phase 2: Monitor New Extractions
```bash
# Monitor logs for 1 week
docker-compose logs -f worker | grep "SKILL EXTRACT"

# Check category distribution
psql -d recruitment_db -c "
SELECT category, COUNT(*) 
FROM job_skill_requirement 
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY category 
ORDER BY COUNT(*) DESC;
"
```

### Phase 3: Re-extract Existing Data (Optional)
```bash
# Re-extract skills for all jobs
curl -X POST http://localhost:8000/jd/admin/batch-extract-skills \
  -H "Content-Type: application/json" \
  -d '{"limit": 1000}'
```

### Phase 4: Update Frontend Filters
```javascript
// Update category filters in frontend
const SKILL_CATEGORIES = [
  { value: 'Programming Language', label: 'Programming Languages' },
  { value: 'Backend Framework', label: 'Backend Frameworks' },
  { value: 'Frontend Framework', label: 'Frontend Frameworks' },
  { value: 'Mobile Framework', label: 'Mobile Frameworks' },
  // ... all 17 categories
];
```

---

## 📝 Notes

- **Backward compatibility:** Old data với "Framework" category vẫn hoạt động, nhưng nên re-extract
- **LLM cost:** Prompt dài hơn (~200 tokens) nhưng accuracy cao hơn → Worth it
- **Category evolution:** Có thể thêm categories mới trong tương lai (e.g., "Blockchain", "IoT")

---

## 🔗 Related Files

- `backend/shared/llm_utils.py` - Validation & prompt
- `backend/shared/skill_extraction.py` - Extraction workflow
- `backend/scripts/test_improved_skill_extraction.py` - Test suite
- `docs/skill-extraction-improvements.md` - Main documentation

---

**Last Updated:** 2026-05-01  
**Version:** 2.0 (17 categories)  
**Author:** OpenCode AI Assistant
