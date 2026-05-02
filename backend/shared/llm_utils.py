import os
import logging
import time
from typing import List, Optional, Dict, Any
import openai
import tiktoken
from shared.config_utils import config_manager
from shared.ai_service import generate_completion
from shared.ai_service.logger import log_llm_call
from shared.system_logger import system_logger

logger = logging.getLogger("llm_utils")

# ─── Token Counting & Cost Tracking ──────────────────────────────────────────

# Embedding model pricing (per 1M tokens)
EMBEDDING_COSTS = {
    "text-embedding-3-small": 0.02,  # $0.02 per 1M tokens
    "text-embedding-3-large": 0.13,  # $0.13 per 1M tokens
    "text-embedding-ada-002": 0.10,  # $0.10 per 1M tokens
}

def count_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    """Count tokens in text using tiktoken."""
    try:
        # Use cl100k_base encoding for embedding models
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Failed to count tokens: {e}. Using character estimate.")
        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4

def calculate_embedding_cost(token_count: int, model: str = "text-embedding-3-small") -> float:
    """Calculate cost in USD for embedding tokens."""
    cost_per_million = EMBEDDING_COSTS.get(model, 0.02)
    return (token_count / 1_000_000) * cost_per_million

# ─── Mapping & Configuration ──────────────────────────────────────────────────

# Mapping từ Model ID sang Provider
MODEL_PROVIDER_MAP = {
    # Google Gemini
    "gemini-1.5-pro": "google",
    "gemini-1.5-flash": "google",
    # OpenAI
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4-turbo": "openai",
    # Anthropic
    "claude-3-5-sonnet": "anthropic",
    "claude-3-5-haiku": "anthropic",
    "claude-3-haiku": "anthropic",
    "claude-3-opus": "anthropic",
}

# ─── Clients Factory ─────────────────────────────────────────────────────────

class LLMFactory:
    """
    Factory class quản lý singleton clients cho các LLM providers khác nhau.
    """
    _clients = {}

    @classmethod
    def get_provider(cls, model_name: str) -> str:
        return MODEL_PROVIDER_MAP.get(model_name, "openai")

    @classmethod
    def get_openai_client(cls):
        if "openai" not in cls._clients:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                cls._clients["openai"] = openai.OpenAI(api_key=api_key)
            else:
                logger.warning("OPENAI_API_KEY is not set.")
                return None
        return cls._clients["openai"]

    @classmethod
    def get_google_client(cls):
        # Lưu ý: Google GenAI SDK sử dụng hàm khởi tạo khác, 
        # nhưng ở đây ta có thể dùng LangChain wrapper để đồng bộ.
        if "google" not in cls._clients:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                api_key = os.getenv("GEMINI_API_KEY")
                if api_key:
                    cls._clients["google"] = ChatGoogleGenerativeAI(
                        model="gemini-1.5-flash", # Default, sẽ override khi gọi
                        google_api_key=api_key
                    )
                else:
                    logger.warning("GEMINI_API_KEY is not set.")
                    return None
            except ImportError:
                logger.error("langchain-google-genai not installed.")
                return None
        return cls._clients["google"]

# Initialize default OpenAI client for legacy support (embeddings)
openai_client = LLMFactory.get_openai_client()

# ─── Embedding Functions ────────────────────────────────────────────────────

def get_embedding(text: str, log_cost: bool = True) -> Optional[List[float]]:
    """
    Tạo vector nhúng (embedding) cho một đoạn văn bản.
    Sử dụng model text-embedding-3-small mặc định của OpenAI.
    
    Args:
        text: Text to embed
        log_cost: Whether to log token usage and cost
    """
    res = get_embeddings_batch([text], log_cost=log_cost)
    return res[0] if res else None

def get_embeddings_batch(texts: List[str], log_cost: bool = True) -> List[List[float]]:
    """
    Tạo vector nhúng (embedding) cho danh sách các đoạn văn bản (Batch).
    
    Args:
        texts: List of texts to embed
        log_cost: Whether to log token usage and cost
    """
    client = LLMFactory.get_openai_client()
    if not texts or not client:
        return []
        
    try:
        # Resolve embedding model from environment variable
        model_id = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        # Làm sạch text nhẹ nhàng
        clean_texts = [t.replace("\n", " ").strip() for t in texts if t]
        if not clean_texts: return []

        # Count tokens before sending
        total_tokens = 0
        if log_cost:
            for text in clean_texts:
                total_tokens += count_tokens(text, model_id)
            
            cost = calculate_embedding_cost(total_tokens, model_id)
            logger.info(f"[EMBED] Sending {len(clean_texts)} texts | model={model_id} | tokens={total_tokens:,} | cost=${cost:.6f}")
        else:
            logger.info(f"[EMBED] Sending {len(clean_texts)} texts | model={model_id}")

        t0 = time.monotonic()
        try:
            response = client.embeddings.create(
                input=clean_texts,
                model=model_id
            )
            duration = int((time.monotonic() - t0) * 1000)
            
            # Log success to DB
            total_tokens = 0
            if hasattr(response, 'usage') and response.usage:
                total_tokens = response.usage.total_tokens
            
            log_llm_call(
                user_id=None, # System level
                model_id=model_id,
                provider="openai",
                call_type="embedding",
                prompt_tokens=total_tokens,
                completion_tokens=0,
                latency_ms=duration,
                status="success",
                request_metadata={"vectors_count": len(response.data)}
            )
            
            # Log actual usage from API response
            if total_tokens > 0:
                actual_cost = calculate_embedding_cost(total_tokens, model_id)
                logger.info(f"[EMBED] ✓ Success | vectors={len(response.data)} | actual_tokens={total_tokens:,} | actual_cost=${actual_cost:.6f}")
            else:
                logger.info(f"[EMBED] ✓ Success | vectors={len(response.data)}")
            
            return [d.embedding for d in response.data]
        except Exception as e:
            duration = int((time.monotonic() - t0) * 1000)
            logger.error(f"[EMBED] ❌ Error generating batch embeddings: {e}")
            
            # Log failure to DB
            log_llm_call(
                user_id=None,
                model_id=model_id,
                provider="openai",
                call_type="embedding",
                latency_ms=duration,
                status="failed",
                error_message=str(e)
            )
            return []
    except Exception as e:
        logger.error(f"[EMBED] ❌ Critical Error in batch wrapper: {e}")
        return []

# ─── Chat Completion Functions ──────────────────────────────────────────────

def get_chat_completion(
    prompt: str, 
    system_prompt: str = "You are a helpful assistant.", 
    json_mode: bool = False,
    model: Optional[str] = None,
    model_key: str = "career_advisor_model",
    call_name: str = "chat_completion",
    user_id: Optional[str] = None
) -> Optional[str]:
    """
    [LEGACY] Wrapper for the new AI Service completion core.
    This function is maintained for backward compatibility.
    """
    # Use career_advisor_model as default for general chat completions if model is not override
    m_key = model_key if model_key else "ai_model"
    
    return generate_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        json_mode=json_mode,
        model=model,
        model_key=m_key,
        call_name=call_name,
        user_id=user_id
    )

# ─── Utility Functions ───────────────────────────────────────────────────────

def build_cv_skill_context(skill_name: str, level: str, years: float, last_used: int = None, context: str = "") -> str:
    parts = [f"Skill: {skill_name}"]
    if level: parts.append(f"Proficiency: {level}")
    if years > 0: parts.append(f"Experience: {years} years")
    if last_used: parts.append(f"Last used: {last_used}")
    if context: parts.append(f"Context: {context}")
    return ". ".join(parts)

def build_jd_skill_context(skill_name: str, level: str, years: float, domain: str = "") -> str:
    parts = [f"Required skill: {skill_name}"]
    if years > 0: parts.append(f"Experience: {years} years of professional use")
    if level and level != "Junior": parts.append(f"Seniority: {level} level")
    if domain: parts.append(f"Domain: {domain}")
    return ". ".join(parts)

def normalize_location(location_raw: str) -> str:
    """
    Normalize location to standard cities: HN, HCM, DN, or Other.
    
    Args:
        location_raw: Raw location string from job posting
        
    Returns:
        Normalized location code (HN, HCM, DN, Other)
    """
    if not location_raw:
        return "Other"
    
    location_lower = location_raw.lower()
    
    # Hanoi patterns
    if any(pattern in location_lower for pattern in ["hà nội", "ha noi", "hanoi", "hn"]):
        return "HN"
    
    # Ho Chi Minh patterns
    if any(pattern in location_lower for pattern in ["hồ chí minh", "ho chi minh", "hcm", "sài gòn", "saigon", "tp.hcm"]):
        return "HCM"
    
    # Da Nang patterns
    if any(pattern in location_lower for pattern in ["đà nẵng", "da nang", "danang", "dn"]):
        return "DN"
    
    return "Other"


def build_job_embedding_context(
    requirements: str = None,
    extracted_skills: list = None,
    job_description: str = None
) -> str:
    """
    Build optimized embedding context for job matching.
    
    Strategy: ONLY embed requirements + skills (no title, location, company)
    Reason: Vector search should match on skills/requirements, not location/title
            Location/title filtering should use SQL WHERE clauses
    
    Args:
        requirements: Job requirements text (primary)
        extracted_skills: List of extracted skill names (secondary)
        job_description: Job description (optional, low priority)
        
    Returns:
        Optimized embedding context string
    """
    parts = []
    
    # Priority 1: Requirements (most important for matching)
    if requirements and requirements.strip():
        # Repeat requirements for emphasis in embedding space
        parts.append(f"Requirements: {requirements.strip()}")
    
    # Priority 2: Extracted skills (structured, high signal)
    if extracted_skills and len(extracted_skills) > 0:
        skills_text = ", ".join(extracted_skills)
        # Repeat skills 2x for emphasis
        parts.append(f"Key skills: {skills_text}. {skills_text}")
    
    # Priority 3: Job description (optional, lower priority)
    if job_description and job_description.strip():
        # Truncate to 500 chars to avoid noise
        desc_truncated = job_description.strip()[:500]
        parts.append(f"Description: {desc_truncated}")
    
    # Fallback: If no content, return empty (will be handled by caller)
    if not parts:
        logger.warning("[JOB EMBED] No content available for embedding")
        return ""
    
    context = ". ".join(parts)
    
    # Log token count for monitoring
    token_count = count_tokens(context)
    logger.info(f"[JOB EMBED] Built context | tokens={token_count} | has_requirements={bool(requirements)} | skills_count={len(extracted_skills) if extracted_skills else 0}")
    
    return context


def get_current_date() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

def truncate_for_prompt(text: str, max_chars: int = 4000) -> str:
    """Cắt bớt text để tránh quá giới hạn token của LLM, ưu tiên lấy phần đầu."""
    if not text: return ""
    if len(text) <= max_chars: return text
    return text[:max_chars] + "... [TRUNCATED]"

def clean_json_response(response: str) -> str:
    """
    SECURITY & STABILITY: Loại bỏ markdown code blocks từ LLM response.
    Đảm bảo json.loads() có thể parse được kể cả khi LLM bao bọc trong ```json.
    """
    if not response:
        return ""
    # Remove ```json ... ``` or ``` ... ```
    import re
    cleaned = re.sub(r'^```(?:json)?\s*', '', response, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()

# ─── Skill Extraction ────────────────────────────────────────────────────────

def validate_and_clean_skill(skill: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate and clean a single extracted skill.
    Returns cleaned skill dict or None if invalid.
    """
    import re
    
    # Valid categories (21 categories: 15 technical + 6 soft skills)
    VALID_CATEGORIES = {
        # Core Programming
        "Programming Language",      # Python, Java, JavaScript, C++, Go, Rust
        "Web Technology",            # HTML, CSS, REST API, GraphQL, WebSocket
        "Backend Framework",         # Django, Spring Boot, Express, FastAPI
        "Frontend Framework",        # React, Vue, Angular, Svelte
        "Mobile Framework",          # Flutter, React Native, SwiftUI, Jetpack Compose
        
        # Data & Storage
        "Database",                  # PostgreSQL, MySQL, MongoDB, Cassandra
        "Caching & Queue",          # Redis, Memcached, Kafka, RabbitMQ
        
        # Infrastructure & Operations
        "Cloud Platform",            # AWS, Azure, GCP, DigitalOcean
        "DevOps & CI/CD",           # Docker, Kubernetes, Jenkins, GitHub Actions
        "Development Tool",          # Git, VS Code, Postman, Jira
        
        # Specialized Domains
        "Testing Framework",         # Jest, Pytest, Selenium, Cypress, JUnit
        "Security",                  # OAuth, JWT, SSL/TLS, Penetration Testing
        "Machine Learning",          # TensorFlow, PyTorch, scikit-learn, Keras
        "Data Science",              # Pandas, NumPy, Jupyter, Tableau, Power BI
        
        # Technical Practices
        "Methodology",               # TDD, Microservices, Design Patterns, CI/CD
        
        # Soft Skills
        "Communication",             # Presentation, Written/Verbal communication, English
        "Leadership",                # Team leadership, Mentoring, Decision making
        "Teamwork",                  # Collaboration, Cross-functional teamwork
        "Problem Solving",           # Analytical thinking, Critical thinking, Troubleshooting
        "Time Management",           # Prioritization, Meeting deadlines, Multi-tasking
        "Adaptability"               # Learning agility, Flexibility, Growth mindset
    }
    
    # Extract skill_name
    skill_name = skill.get("skill_name", "").strip()
    
    if not skill_name:
        return None
    
    # Check length (2-50 characters)
    if len(skill_name) < 2 or len(skill_name) > 50:
        logger.debug(f"[SKILL VALIDATE] Rejected '{skill_name}': invalid length ({len(skill_name)} chars)")
        return None
    
    # Check for Vietnamese characters
    vietnamese_pattern = r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]'
    if re.search(vietnamese_pattern, skill_name):
        logger.debug(f"[SKILL VALIDATE] Rejected '{skill_name}': contains Vietnamese characters")
        return None
    
    # Check for invalid patterns (phrases that are not skill names)
    invalid_patterns = [
        r'\d+\+?\s*(years?|yrs?)',  # "5+ years", "3 years"
        r'(knowledge|experience|ability|understanding)\s+(of|in|with)',  # "knowledge of", "experience in"
        r'(bachelor|master|degree|diploma)',  # Education requirements
        r'(good|excellent|strong|solid)\s+',  # Adjectives
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, skill_name, re.IGNORECASE):
            logger.debug(f"[SKILL VALIDATE] Rejected '{skill_name}': matches invalid pattern '{pattern}'")
            return None
    
    # Validate category
    category = skill.get("category", "").strip()
    if category not in VALID_CATEGORIES:
        # Try to map common variations to valid categories
        category_mapping = {
            # Programming
            "language": "Programming Language",
            "programming": "Programming Language",
            
            # Web
            "web": "Web Technology",
            "api": "Web Technology",
            "web tech": "Web Technology",
            
            # Frameworks
            "framework": "Backend Framework",  # Default to backend
            "backend": "Backend Framework",
            "frontend": "Frontend Framework",
            "mobile": "Mobile Framework",
            
            # Data & Storage
            "database": "Database",
            "db": "Database",
            "cache": "Caching & Queue",
            "caching": "Caching & Queue",
            "queue": "Caching & Queue",
            "message queue": "Caching & Queue",
            
            # Infrastructure
            "cloud": "Cloud Platform",
            "devops": "DevOps & CI/CD",
            "ci/cd": "DevOps & CI/CD",
            "cicd": "DevOps & CI/CD",
            "tool": "Development Tool",
            "development tool": "Development Tool",
            "design tool": "Development Tool",  # Map Design Tool → Development Tool
            "infrastructure": "DevOps & CI/CD",
            "os": "DevOps & CI/CD",
            "operating system": "DevOps & CI/CD",
            
            # Specialized
            "testing": "Testing Framework",
            "test": "Testing Framework",
            "security": "Security",
            "ml": "Machine Learning",
            "machine learning": "Machine Learning",
            "ai": "Machine Learning",
            "data science": "Data Science",
            "data": "Data Science",
            
            # Practices
            "methodology": "Methodology",
            "practice": "Methodology",
            
            # Soft Skills
            "communication": "Communication",
            "leadership": "Leadership",
            "teamwork": "Teamwork",
            "collaboration": "Teamwork",
            "problem solving": "Problem Solving",
            "analytical thinking": "Problem Solving",
            "critical thinking": "Problem Solving",
            "time management": "Time Management",
            "prioritization": "Time Management",
            "adaptability": "Adaptability",
            "flexibility": "Adaptability",
            "learning agility": "Adaptability",
        }
        category_lower = category.lower()
        if category_lower in category_mapping:
            category = category_mapping[category_lower]
        else:
            logger.debug(f"[SKILL VALIDATE] Invalid category '{category}' for skill '{skill_name}', rejecting skill")
            return None  # Reject skills with invalid categories
    
    # Validate and clean other fields
    required_level = skill.get("required_level")
    if required_level and not isinstance(required_level, str):
        required_level = None
    
    min_years_exp = skill.get("min_years_exp", 0)
    try:
        min_years_exp = float(min_years_exp) if min_years_exp else 0
        min_years_exp = max(0, min(min_years_exp, 50))  # Cap at 50 years
    except (ValueError, TypeError):
        min_years_exp = 0
    
    is_mandatory = skill.get("is_mandatory", True)
    if not isinstance(is_mandatory, bool):
        is_mandatory = True
    
    importance_weight = skill.get("importance_weight", 5)
    try:
        importance_weight = int(importance_weight)
        importance_weight = max(1, min(importance_weight, 10))  # Clamp to 1-10
    except (ValueError, TypeError):
        importance_weight = 5
    
    # Determine skill_type based on category
    SOFT_SKILL_CATEGORIES = {
        "Communication", "Leadership", "Teamwork", 
        "Problem Solving", "Time Management", "Adaptability"
    }
    
    skill_type = skill.get("skill_type", "").lower()
    if not skill_type or skill_type not in ["technical", "soft"]:
        # Auto-detect based on category
        skill_type = "soft" if category in SOFT_SKILL_CATEGORIES else "technical"
    
    # Check if this is a skill group
    is_group = skill.get("is_group", False)
    
    # Build base cleaned skill
    cleaned = {
        "skill_name": skill_name,
        "category": category,
        "required_level": required_level,
        "min_years_exp": min_years_exp,
        "is_mandatory": is_mandatory,
        "importance_weight": importance_weight,
        "skill_type": skill_type
    }
    
    # If it's a skill group, preserve group fields
    if is_group:
        cleaned["is_group"] = True
        cleaned["group_strategy"] = skill.get("group_strategy", "any_one")
        cleaned["alternative_skills"] = skill.get("alternative_skills", [])
        cleaned["min_required"] = skill.get("min_required", 1)
        
        # Validate alternative_skills is a list
        if not isinstance(cleaned["alternative_skills"], list):
            cleaned["alternative_skills"] = []
        
        # Validate min_required is an integer
        try:
            cleaned["min_required"] = int(cleaned["min_required"])
            cleaned["min_required"] = max(1, cleaned["min_required"])
        except (ValueError, TypeError):
            cleaned["min_required"] = 1
    
    return cleaned


def extract_skills_from_requirements(requirements_text: str, model_key: str = "ai_model", user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Extract structured skills AND classify job type from requirements text using LLM.
    
    Returns dict with classification and skills:
    {
        "is_tech_job": true/false,
        "confidence": 0.0-1.0,
        "primary_domain": "Software Engineering" or "Sales" etc,
        "classification_reason": "Brief explanation",
        "skills": [
            {
                "skill_name": "Python",
                "category": "Programming Language",
                "required_level": "Senior",
                "min_years_exp": 5.0,
                "is_mandatory": true,
                "importance_weight": 10
            },
            ...
        ]
    }
    """
    if not requirements_text or len(requirements_text.strip()) < 20:
        logger.warning("[SKILL EXTRACT] Requirements text too short, skipping extraction")
        return None
    
    prompt = f"""Analyze this job requirements and perform TWO tasks:

TASK 1: Classify if this is a TECH job
TASK 2: If TECH job, extract technical skills

Job Requirements:
{requirements_text}

=== TASK 1: JOB CLASSIFICATION ===

Think step-by-step to determine if this is a TECH job:

Step 1: Identify the main responsibilities
- What are the core tasks mentioned?
- Do they involve coding, system design, technical problem-solving?

Step 2: Check for technical requirements
- Programming languages mentioned?
- Frameworks, databases, cloud platforms?
- Technical tools or methodologies?

Step 3: Determine job domain
- Is this Software Engineering, DevOps, Data Science, QA, IT?
- Or is it Sales, Marketing, HR, Finance, Operations?

TECH jobs include:
- Software Engineer, Developer, Programmer
- DevOps Engineer, SRE, System Administrator
- Data Scientist, Data Engineer, ML Engineer
- QA Engineer, Test Automation Engineer
- Security Engineer, Network Engineer
- Technical roles requiring programming/technical skills

NON-TECH jobs include:
- Sales, Marketing, HR, Finance, Operations
- Customer Service, Administrative roles
- Management roles WITHOUT technical focus
- Jobs mentioning only "MS Office" or "basic computer skills"

Provide:
- is_tech_job: true/false
- confidence: 0.0-1.0 (how confident in classification)
- primary_domain: Main job domain (e.g., "Software Engineering", "Sales", "Marketing")
- classification_reason: Your step-by-step reasoning (2-3 sentences)

=== TASK 2: SKILL EXTRACTION (only if is_tech_job = true) ===

If TECH job, extract skills using these 21 categories (15 technical + 6 soft skills):

CORE PROGRAMMING:
- "Programming Language" (Python, Java, JavaScript, C++, Go, Rust, TypeScript)
- "Web Technology" (HTML, CSS, REST API, GraphQL, WebSocket)
- "Backend Framework" (Django, Spring Boot, Express, FastAPI, Laravel)
- "Frontend Framework" (React, Vue, Angular, Svelte, Next.js)
- "Mobile Framework" (Flutter, React Native, SwiftUI, Jetpack Compose)

DATA & STORAGE:
- "Database" (PostgreSQL, MySQL, MongoDB, Cassandra)
- "Caching & Queue" (Redis, Kafka, RabbitMQ, Memcached)

INFRASTRUCTURE:
- "Cloud Platform" (AWS, Azure, GCP)
- "DevOps & CI/CD" (Docker, Kubernetes, Jenkins, Terraform)
- "Development Tool" (Git, VS Code, Postman, Jira)

SPECIALIZED:
- "Testing Framework" (Jest, Pytest, Selenium, Cypress)
- "Security" (OAuth, JWT, SSL/TLS, OWASP)
- "Machine Learning" (TensorFlow, PyTorch, scikit-learn)
- "Data Science" (Pandas, NumPy, Jupyter, Tableau)

PRACTICES:
- "Methodology" (TDD, Microservices, Design Patterns)

SOFT SKILLS (extract these separately):
- "Communication" (Presentation skills, Written communication, Verbal communication, English proficiency)
- "Leadership" (Team leadership, Mentoring, Decision making, Strategic thinking)
- "Teamwork" (Collaboration, Cross-functional teamwork, Agile teamwork)
- "Problem Solving" (Analytical thinking, Critical thinking, Troubleshooting, Debugging mindset)
- "Time Management" (Prioritization, Meeting deadlines, Multi-tasking)
- "Adaptability" (Learning agility, Flexibility, Change management, Growth mindset)

For each skill:
- skill_name: Specific name in ENGLISH (e.g., "Python", "React", "Communication", "Leadership")
- category: ONE of the 21 categories above (15 technical + 6 soft skills)
- required_level: "Junior", "Mid", "Senior", "Expert" or null
- min_years_exp: Number (0 if not specified)
- is_mandatory: true if required, false if "nice to have"
- importance_weight: 1-10 (10=critical, 5=mentioned, 1=minor)
- skill_type: "technical" or "soft" (to distinguish between technical and soft skills)

RULES:
- STRICTLY ENGLISH ONLY. No Vietnamese characters allowed in any field.
- Any skill_name (including group names) containing Vietnamese will be REJECTED by the system.
- 2-50 characters per skill name.
- No phrases like "years of experience", "knowledge of".
- Specific names: "React" not "frameworks".
- Proper capitalization: "JavaScript" not "javascript".
- Extract BOTH technical AND soft skills explicitly mentioned.
- For soft skills, use the skill_type="soft" field.
- If NON-TECH job, return empty skills array [].

=== IMPORTANT: ALTERNATIVE SKILL GROUPS ===

MANDATORY RULE: You MUST detect when requirements mention ALTERNATIVES (user only needs ONE or SOME, not ALL) and return them as a SKILL GROUP. Do NOT list them as separate skills.

PATTERNS TO DETECT:
- English: "or", "at least one of", "one of the following", "any of", "or equivalent"
- Vietnamese: "hoặc", "ít nhất một", "một trong các", "tương đương", "một trong số", "nắm vững một trong các", "biết ít nhất một"
- Parentheses: "(Blender, Maya, or 3ds Max)", "(SQL/NoSQL)"
- Slashes: "SQL/NoSQL", "React/Vue/Angular"

When you detect alternatives, return as a SKILL GROUP:
{{
  "skill_name": "3D Modeling Tools",  // Descriptive name in ENGLISH
  "category": "Development Tool",
  "is_group": true,                      // Mark as group
  "group_strategy": "any_one",           // Strategy (see below)
  "alternative_skills": ["Blender", "Maya", "3ds Max"],  // Array of alternatives
  "min_required": 1,                     // How many needed
  "is_mandatory": true,
  "importance_weight": 8,
  "skill_type": "technical"
}}

GROUP STRATEGIES:
- "any_one": User needs ANY ONE skill from alternatives (most common)
  Example: "Blender, Maya, or 3ds Max" → any_one, min_required=1
- "at_least_n": User needs at least N skills
  Example: "At least 2 of: Python, Java, C++, Go" → at_least_n, min_required=2
- "all": User needs ALL skills (rare, only if explicitly stated "all of")

EXAMPLES:
1. "Thành thạo ít nhất một phần mềm: Blender, Maya, hoặc 3ds Max"
   → {{"skill_name": "3D Modeling Tools", "is_group": true, "group_strategy": "any_one", "alternative_skills": ["Blender", "Maya", "3ds Max"], "min_required": 1}}

2. "Experience with SQL or NoSQL databases"
   → {{"skill_name": "Database Technology", "is_group": true, "group_strategy": "any_one", "alternative_skills": ["SQL", "NoSQL"], "min_required": 1}}

3. "At least 2 programming languages: Python, Java, C++, or Go"
   → {{"skill_name": "Backend Programming Languages", "is_group": true, "group_strategy": "at_least_n", "alternative_skills": ["Python", "Java", "C++", "Go"], "min_required": 2}}

Return JSON:
{{
  "is_tech_job": true/false,
  "confidence": 0.95,
  "primary_domain": "Software Engineering",
  "classification_reason": "This is a software development role requiring programming skills",
  "skills": [
    {{"skill_name": "Python", "category": "Programming Language", "required_level": "Senior", "min_years_exp": 5, "is_mandatory": true, "importance_weight": 10, "skill_type": "technical"}},
    {{"skill_name": "Django", "category": "Backend Framework", "required_level": null, "min_years_exp": 3, "is_mandatory": true, "importance_weight": 8, "skill_type": "technical"}},
    {{"skill_name": "3D Modeling Software", "category": "Design Tool", "is_group": true, "group_strategy": "any_one", "alternative_skills": ["Blender", "Maya", "3ds Max"], "min_required": 1, "is_mandatory": true, "importance_weight": 8, "skill_type": "technical"}},
    {{"skill_name": "Communication", "category": "Communication", "required_level": null, "min_years_exp": 0, "is_mandatory": true, "importance_weight": 7, "skill_type": "soft"}},
    {{"skill_name": "Team leadership", "category": "Leadership", "required_level": "Mid", "min_years_exp": 2, "is_mandatory": false, "importance_weight": 6, "skill_type": "soft"}}
  ]
}}

If NON-TECH:
{{
  "is_tech_job": false,
  "confidence": 0.90,
  "primary_domain": "Sales",
  "classification_reason": "This is a sales role focusing on customer relationships, not technical development",
  "skills": []
}}
"""

    system_prompt = "You are a technical recruiter expert at analyzing job requirements and extracting structured skill data. Always return valid JSON."
    
    try:
        logger.info(f"[SKILL EXTRACT] Extracting skills from {len(requirements_text)} chars of requirements...")
        system_logger.info("AI_SKILL_EXTRACT", f"Starting skill extraction ({len(requirements_text)} chars)")
        
        response = get_chat_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            model_key=model_key,
            call_name="extract_skills",
            user_id=user_id
        )
        
        # DEBUG: Log raw response
        # logger.info(f"[DEBUG RAW LLM] {response}")
        
        if not response:
            logger.error("[SKILL EXTRACT] No response from LLM")
            return None
        
        # Parse JSON response with cleaning
        import json
        cleaned_response = clean_json_response(response)
        result = json.loads(cleaned_response)
        
        # Validate response structure
        if not isinstance(result, dict):
            logger.error(f"[SKILL EXTRACT] Expected dict, got {type(result)}")
            return None
        
        # Extract classification data
        is_tech_job = result.get("is_tech_job", True)
        confidence = result.get("confidence", 0.5)
        primary_domain = result.get("primary_domain", "Unknown")
        classification_reason = result.get("classification_reason", "")
        skills = result.get("skills", [])
        
        # Validate classification fields
        if not isinstance(is_tech_job, bool):
            is_tech_job = True
        
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(confidence, 1.0))  # Clamp to 0.0-1.0
        except (ValueError, TypeError):
            confidence = 0.5
        
        if not isinstance(skills, list):
            logger.error(f"[SKILL EXTRACT] Expected skills list, got {type(skills)}")
            skills = []
        
        logger.info(f"[SKILL EXTRACT] Classification: is_tech={is_tech_job}, confidence={confidence:.2f}, domain={primary_domain}")
        logger.info(f"[SKILL EXTRACT] Raw extraction: {len(skills)} skills")
        
        # If non-tech job, return early with empty skills
        if not is_tech_job:
            logger.warning(f"[SKILL EXTRACT] Non-tech job detected: {classification_reason}")
            system_logger.info("AI_SKILL_EXTRACT", f"Non-tech job: {primary_domain} (confidence: {confidence:.2f})")
            return {
                "is_tech_job": False,
                "confidence": confidence,
                "primary_domain": primary_domain,
                "classification_reason": classification_reason,
                "skills": []
            }
        
        # Validate and clean each skill (only for tech jobs)
        validated_skills = []
        rejected_count = 0
        
        for skill in skills:
            cleaned_skill = validate_and_clean_skill(skill)
            if cleaned_skill:
                validated_skills.append(cleaned_skill)
            else:
                rejected_count += 1
        
        logger.info(f"[SKILL EXTRACT] ✓ Validated {len(validated_skills)} skills ({rejected_count} rejected)")
        system_logger.info("AI_SKILL_EXTRACT", f"Tech job: {primary_domain} - extracted {len(validated_skills)} skills ({rejected_count} rejected)")
        
        # Log validated skills for monitoring
        for skill in validated_skills[:5]:  # Log first 5
            logger.debug(f"[SKILL EXTRACT]   - {skill.get('skill_name')} ({skill.get('category')}) | Level: {skill.get('required_level')} | Years: {skill.get('min_years_exp')} | Weight: {skill.get('importance_weight')}")
        
        # Return full result with classification + skills
        return {
            "is_tech_job": True,
            "confidence": confidence,
            "primary_domain": primary_domain,
            "classification_reason": classification_reason,
            "skills": validated_skills
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[SKILL EXTRACT] Failed to parse JSON response: {e}")
        logger.debug(f"[SKILL EXTRACT] Raw response: {response[:200]}...")
        return None
    except Exception as e:
        logger.error(f"[SKILL EXTRACT] Error extracting skills: {e}", exc_info=True)
        system_logger.error("AI_SKILL_EXTRACT", f"Error during skill extraction: {str(e)}")
        return None
