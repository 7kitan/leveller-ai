"""
Analyze the length of skill extraction prompt in tokens and cost.
"""
import sys
sys.path.insert(0, '/app')

try:
    import tiktoken
except ImportError:
    print("Installing tiktoken...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tiktoken"])
    import tiktoken

# Prompt template (without requirements_text variable)
prompt_template = """Extract all technical and professional skills from the following job requirements.

Job Requirements:
{requirements_text}

For each skill, identify:
1. skill_name: The specific skill name in ENGLISH ONLY (e.g., "Python", "React", "Project Management")
2. category: Must be ONE of these exact categories:
   
   CORE PROGRAMMING:
   - "Programming Language" (Python, Java, JavaScript, C++, Go, Rust, TypeScript, Kotlin, Swift)
   - "Web Technology" (HTML, CSS, REST API, GraphQL, WebSocket, HTTP, JSON, XML)
   - "Backend Framework" (Django, Spring Boot, Express, FastAPI, Laravel, Ruby on Rails, ASP.NET)
   - "Frontend Framework" (React, Vue, Angular, Svelte, Next.js, Nuxt.js)
   - "Mobile Framework" (Flutter, React Native, SwiftUI, Jetpack Compose, Ionic, Xamarin)
   
   DATA & STORAGE:
   - "Database" (PostgreSQL, MySQL, MongoDB, Oracle, SQL Server, Cassandra, DynamoDB)
   - "Caching & Queue" (Redis, Memcached, Kafka, RabbitMQ, ActiveMQ, Amazon SQS)
   
   INFRASTRUCTURE & OPERATIONS:
   - "Cloud Platform" (AWS, Azure, GCP, DigitalOcean, Heroku, Vercel, Netlify)
   - "DevOps & CI/CD" (Docker, Kubernetes, Jenkins, GitHub Actions, GitLab CI, Terraform, Ansible)
   - "Development Tool" (Git, VS Code, IntelliJ, Postman, Jira, Confluence, Slack)
   
   SPECIALIZED DOMAINS:
   - "Testing Framework" (Jest, Pytest, Selenium, Cypress, JUnit, Mocha, TestNG, Cucumber)
   - "Security" (OAuth, JWT, SSL/TLS, Penetration Testing, OWASP, Encryption, Firewall)
   - "Machine Learning" (TensorFlow, PyTorch, scikit-learn, Keras, YOLO, OpenCV, Hugging Face)
   - "Data Science" (Pandas, NumPy, Jupyter, Matplotlib, Tableau, Power BI, Apache Spark)
   
   PROCESS & SOFT SKILLS:
   - "Methodology" (Agile, Scrum, Kanban, TDD, BDD, Microservices, DDD, SOLID, Design Patterns)
   - "Soft Skill" (Communication, Leadership, Problem Solving, Teamwork, Time Management)
   - "Domain Knowledge" (Finance, Healthcare, E-commerce, Fintech, EdTech, Gaming, Blockchain)
3. required_level: Seniority level if mentioned (e.g., "Junior", "Mid", "Senior", "Expert") or null
4. min_years_exp: Minimum years of experience required (extract number, or 0 if not specified)
5. is_mandatory: true if explicitly required, false if "nice to have" or "plus"
6. importance_weight: Rate 1-10 based on these criteria:
   - 10: Mentioned in job title or listed first, marked as "must have" or "required"
   - 8-9: Mentioned multiple times or emphasized with specific requirements
   - 5-7: Clearly mentioned but not emphasized
   - 3-4: Listed as "nice to have" or "plus"
   - 1-2: Mentioned briefly or indirectly

STRICT VALIDATION RULES:
- skill_name MUST be in English only (no Vietnamese characters: àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ)
- skill_name MUST be 2-50 characters long
- skill_name MUST NOT contain phrases like "years of experience", "knowledge of", "ability to"
- skill_name MUST be specific: "React" not "JavaScript frameworks", "PostgreSQL" not "databases"
- skill_name MUST use proper capitalization: "JavaScript" not "javascript", "AWS" not "aws"
- category MUST be one of the 17 categories listed above (exact match)
- Do NOT extract generic soft skills like "hard-working", "passionate", "team player" unless specifically required
- Do NOT extract job requirements that are not skills (e.g., "Bachelor's degree", "5+ years experience")
- Extract ONLY skills explicitly mentioned in the text
- Do NOT infer or add skills not mentioned

CATEGORIZATION GUIDELINES:
- HTML/CSS → "Web Technology" (not "Programming Language")
- REST API/GraphQL → "Web Technology" (not "Backend Framework")
- React/Vue/Angular → "Frontend Framework" (not "Backend Framework")
- Flutter/React Native → "Mobile Framework" (not "Frontend Framework")
- Jest/Pytest → "Testing Framework" (not "Backend Framework")
- Redis/Kafka → "Caching & Queue" (not "Database")
- OAuth/JWT → "Security" (not "Web Technology")
- TensorFlow/PyTorch → "Machine Learning" (not "Backend Framework")
- Pandas/NumPy → "Data Science" (not "Programming Language")

Return ONLY a JSON array of skills. Example:
[
  {{"skill_name": "Python", "category": "Programming Language", "required_level": "Senior", "min_years_exp": 5, "is_mandatory": true, "importance_weight": 10}},
  {{"skill_name": "Django", "category": "Backend Framework", "required_level": null, "min_years_exp": 3, "is_mandatory": true, "importance_weight": 8}},
  {{"skill_name": "React", "category": "Frontend Framework", "required_level": null, "min_years_exp": 2, "is_mandatory": true, "importance_weight": 7}},
  {{"skill_name": "Docker", "category": "DevOps & CI/CD", "required_level": null, "min_years_exp": 0, "is_mandatory": false, "importance_weight": 5}},
  {{"skill_name": "REST API", "category": "Web Technology", "required_level": null, "min_years_exp": 0, "is_mandatory": true, "importance_weight": 6}}
]

Return empty array [] if no clear skills found.
"""

system_prompt = "You are a technical recruiter expert at analyzing job requirements and extracting structured skill data. Always return valid JSON."

# Sample job requirements (short, medium, long)
sample_requirements = {
    "short": "Python, Django, PostgreSQL, Docker",
    "medium": """We are looking for a Senior Backend Developer with the following skills:
- 5+ years experience with Python
- Strong knowledge of Django or Flask
- PostgreSQL database experience
- Docker and Kubernetes
- AWS cloud services
- RESTful API design
Nice to have: React, Redis, CI/CD""",
    "long": """We are looking for a Senior Full-Stack Developer to join our team.

Required Skills:
- 5+ years of professional software development experience
- Expert-level Python programming (Django/Flask frameworks)
- Strong frontend skills with React, TypeScript, Next.js
- Database design and optimization (PostgreSQL, MongoDB)
- RESTful API and GraphQL development
- Cloud platforms (AWS: EC2, S3, Lambda, RDS)
- DevOps tools (Docker, Kubernetes, Jenkins, Terraform)
- Version control with Git and GitHub
- Agile/Scrum methodology
- Strong problem-solving and communication skills

Nice to Have:
- Mobile development (Flutter or React Native)
- Machine Learning experience (TensorFlow, PyTorch)
- Data analysis with Pandas, NumPy
- Testing frameworks (Jest, Pytest, Cypress)
- Security best practices (OAuth, JWT)
- Message queues (Kafka, RabbitMQ)
- Redis caching
- CI/CD pipeline setup
- Microservices architecture
- Domain knowledge in Fintech or E-commerce""" * 2  # Double it to simulate very long JD
}

def analyze_prompt():
    """Analyze prompt token count and cost."""
    print("=" * 80)
    print("SKILL EXTRACTION PROMPT ANALYSIS")
    print("=" * 80)
    
    # Count tokens
    encoding = tiktoken.get_encoding('cl100k_base')
    
    # Static prompt (without requirements)
    static_prompt = prompt_template.replace("{requirements_text}", "")
    static_tokens = len(encoding.encode(static_prompt))
    system_tokens = len(encoding.encode(system_prompt))
    
    print(f"\n1. STATIC PROMPT (without job requirements):")
    print(f"   Characters: {len(static_prompt):,}")
    print(f"   Lines: {len(static_prompt.splitlines())}")
    print(f"   Tokens: {static_tokens}")
    print(f"   System prompt tokens: {system_tokens}")
    print(f"   Total static tokens: {static_tokens + system_tokens}")
    
    print(f"\n2. WITH JOB REQUIREMENTS:")
    print(f"   {'Scenario':<15} {'Req Chars':<12} {'Req Tokens':<12} {'Total Tokens':<15} {'GPT-3.5 Cost':<15} {'GPT-4 Cost'}")
    print(f"   {'-'*15} {'-'*12} {'-'*12} {'-'*15} {'-'*15} {'-'*10}")
    
    for scenario, req_text in sample_requirements.items():
        req_tokens = len(encoding.encode(req_text))
        total_tokens = static_tokens + system_tokens + req_tokens
        
        # Cost calculation (input tokens only)
        # GPT-3.5-turbo: $0.0015 per 1K tokens (input)
        # GPT-4: $0.03 per 1K tokens (input)
        gpt35_cost = total_tokens / 1000 * 0.0015
        gpt4_cost = total_tokens / 1000 * 0.03
        
        print(f"   {scenario:<15} {len(req_text):<12,} {req_tokens:<12} {total_tokens:<15} ${gpt35_cost:<14.4f} ${gpt4_cost:.4f}")
    
    print(f"\n3. COST ESTIMATES (for 1000 jobs):")
    avg_req_tokens = len(encoding.encode(sample_requirements["medium"]))
    avg_total = static_tokens + system_tokens + avg_req_tokens
    
    print(f"   Assuming average job requirements (~{avg_req_tokens} tokens)")
    print(f"   Average total tokens per extraction: {avg_total}")
    print(f"   ")
    print(f"   GPT-3.5-turbo (1000 jobs):")
    print(f"     Input cost:  ${(avg_total / 1000 * 0.0015) * 1000:.2f}")
    print(f"     Output cost: ${(200 / 1000 * 0.002) * 1000:.2f} (assuming ~200 tokens output)")
    print(f"     Total:       ${((avg_total / 1000 * 0.0015) + (200 / 1000 * 0.002)) * 1000:.2f}")
    print(f"   ")
    print(f"   GPT-4 (1000 jobs):")
    print(f"     Input cost:  ${(avg_total / 1000 * 0.03) * 1000:.2f}")
    print(f"     Output cost: ${(200 / 1000 * 0.06) * 1000:.2f} (assuming ~200 tokens output)")
    print(f"     Total:       ${((avg_total / 1000 * 0.03) + (200 / 1000 * 0.06)) * 1000:.2f}")
    
    print(f"\n4. COMPARISON WITH SHORTER PROMPT:")
    # Estimate a minimal prompt
    minimal_prompt_tokens = 200  # Rough estimate for a very basic prompt
    print(f"   Current prompt: {static_tokens} tokens")
    print(f"   Minimal prompt: ~{minimal_prompt_tokens} tokens (estimated)")
    print(f"   Difference: {static_tokens - minimal_prompt_tokens} tokens ({((static_tokens - minimal_prompt_tokens) / static_tokens * 100):.1f}% overhead)")
    print(f"   ")
    print(f"   Extra cost per 1000 jobs (GPT-3.5):")
    print(f"     ${((static_tokens - minimal_prompt_tokens) / 1000 * 0.0015) * 1000:.2f}")
    
    print(f"\n5. VERDICT:")
    if static_tokens > 1000:
        print(f"   ⚠️  PROMPT IS LONG ({static_tokens} tokens)")
        print(f"   Consider optimizing if cost is a concern.")
    elif static_tokens > 600:
        print(f"   ⚠️  PROMPT IS MODERATELY LONG ({static_tokens} tokens)")
        print(f"   Acceptable for high-quality extraction, but could be optimized.")
    else:
        print(f"   ✓ PROMPT LENGTH IS REASONABLE ({static_tokens} tokens)")
    
    print(f"\n6. RECOMMENDATIONS:")
    if static_tokens > 600:
        print(f"   • Remove example skill names from category definitions")
        print(f"   • Shorten categorization guidelines (keep only most important)")
        print(f"   • Reduce number of validation rules")
        print(f"   • Use shorter category names if possible")
        print(f"   • Consider splitting into 2-stage extraction (extract → validate)")
    else:
        print(f"   • Current prompt length is acceptable")
        print(f"   • Focus on improving accuracy rather than reducing length")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    analyze_prompt()
