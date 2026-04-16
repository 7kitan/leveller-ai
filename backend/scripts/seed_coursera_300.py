"""
Seed 300 Coursera courses from dataset/Coursera300.json into PostgreSQL courses table.

Mapping Coursera300.json → Course model:
  course_name  → title
  summary      → description
  platform     → "Coursera" (hardcoded)
  link         → url
  level        → level
  certificate  → is_certification (bool)
  (auto)       → provider (extracted from link or "Coursera")
  (parsed)     → duration_hours (converted from "duration" string)
  (extracted)   → tags (LLM + keyword extraction from name + summary)
  (generated)  → embedding_context (rich text for vector search)
  (generated)  → vector (OpenAI text-embedding-3-small, 1536 dims)
  (fixed)      → language = "en"
  (fixed)      → cost_usd = 0 (Coursera audit mode is free)

Tag extraction strategy:
  1. Keyword matching on course_name + summary for domain categories
  2. LLM-assisted tagging for ambiguous courses (batch prompt)
  3. Cross-reference with existing Skill table for consistency

Usage:
  python scripts/seed_coursera_300.py
  python scripts/seed_coursera_300.py --force      # re-seed even if courses exist
  python scripts/seed_coursera_300.py --dry-run    # show what would be inserted
  python scripts/seed_coursera_300.py --skip-embed  # skip OpenAI embedding (dev only)
"""

import os
import sys
import uuid
import json
import re
import logging
import argparse
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add backend root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.models import Course, Skill
from shared.database import SessionLocal as SharedSessionLocal

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("seed_coursera_300")

# ─── Config ────────────────────────────────────────────────────────────────────
load_dotenv()

POSTGRES_USER     = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB       = os.getenv("POSTGRES_DB", "career_advisor")
POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432}/{POSTGRES_DB}"

engine    = create_engine(DATABASE_URL)
Session   = sessionmaker(bind=engine)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "Coursera300.json")

# ─── Duration parser ───────────────────────────────────────────────────────────
def parse_duration_to_hours(duration_str: str) -> Optional[float]:
    """Convert Coursera duration string to total hours (float)."""
    if not duration_str:
        return None
    s = duration_str.strip().lower()
    total = 0.0

    # e.g. "6 months" → 720h, "3 months" → 360h, "2 weeks" → 40h, "10 hours" → 10h
    if "month" in s:
        m = re.search(r"(\d+(?:\.\d+)?)\s*month", s)
        if m:
            total += float(m.group(1)) * 4.33 * 40  # ~4.33 weeks/month × 40h/week
    if "week" in s:
        w = re.search(r"(\d+(?:\.\d+)?)\s*week", s)
        if w:
            total += float(w.group(1)) * 10  # ~10h/week estimate
    if "hour" in s:
        h = re.search(r"(\d+(?:\.\d+)?)\s*hour", s)
        if h:
            total += float(h.group(1))
    if "year" in s:
        y = re.search(r"(\d+(?:\.\d+)?)\s*year", s)
        if y:
            total += float(y.group(1)) * 2080  # 40h/week × 52 weeks

    return round(total, 1) if total > 0 else None


# ─── Domain keyword dictionaries for tag extraction ──────────────────────────
# Maps domain keywords → canonical tag(s)
DOMAIN_TAG_MAP: dict[str, list[str]] = {
    # Programming & Languages
    "python":           ["Python"],
    "javascript":       ["JavaScript"],
    "java":             ["Java"],
    "c++":              ["C++"],
    "c#":               ["C#"],
    "golang":           ["Go"],
    "go ":              ["Go"],
    "rust":             ["Rust"],
    "typescript":       ["TypeScript"],
    "react":            ["React"],
    "angular":          ["Angular"],
    "vue":              ["Vue.js"],
    "node.js":          ["Node.js"],
    "nodejs":           ["Node.js"],
    "spring":           ["Spring Boot"],
    ".net":             [".NET"],
    "swift":            ["Swift"],
    "kotlin":           ["Kotlin"],
    "scala":            ["Scala"],
    "ruby":             ["Ruby"],
    "php":              ["PHP"],
    "perl":             ["Perl"],
    "html":             ["HTML"],
    "css":              ["CSS"],

    # AI & ML
    "machine learning": ["Machine Learning"],
    "deep learning":    ["Deep Learning"],
    "neural network":   ["Neural Networks"],
    "nlp":              ["NLP"],
    "natural language": ["NLP"],
    "computer vision":  ["Computer Vision"],
    "generative ai":    ["Generative AI"],
    "llm":              ["LLM"],
    "large language":   ["LLM"],
    "chatgpt":          ["LLM"],
    "prompt engineer":  ["Prompt Engineering"],
    "reinforcement":    ["Reinforcement Learning"],
    "ai for":           ["AI Fundamentals"],
    "artificial intelligence": ["AI Fundamentals"],
    "data science":     ["Data Science"],
    "ai systems design": ["AI Systems Design"],
    "rag":              ["RAG"],
    "mlops":            ["MLOps"],
    "ml engineering":   ["MLOps"],

    # Data & Analytics
    "data analysis":    ["Data Analysis"],
    "data analytics":   ["Data Analysis"],
    "data engineer":    ["Data Engineering"],
    "sql":              ["SQL"],
    "postgresql":       ["PostgreSQL"],
    "nosql":            ["NoSQL"],
    "mongodb":          ["MongoDB"],
    "tableau":          ["Tableau"],
    "power bi":         ["Power BI"],
    "excel":            ["Excel"],
    "statistics":       ["Statistics"],
    "probability":      ["Statistics"],
    "bayesian":         ["Bayesian Statistics"],
    "r programming":    ["R"],
    "r language":       ["R"],
    "data visualization": ["Data Visualization"],
    "dashboard":        ["Data Visualization"],
    "bi ":              ["Business Intelligence"],
    "business intelligence": ["Business Intelligence"],
    "etl":              ["ETL"],
    "data warehouse":   ["Data Warehouse"],

    # Cloud & DevOps
    "aws":              ["AWS"],
    "azure":            ["Azure"],
    "gcp":              ["Google Cloud"],
    "google cloud":    ["Google Cloud"],
    "cloud computing":  ["Cloud Computing"],
    "devops":          ["DevOps"],
    "docker":           ["Docker"],
    "kubernetes":       ["Kubernetes"],
    "ci/cd":            ["CI/CD"],
    "terraform":        ["Terraform"],
    "ansible":          ["Ansible"],
    "linux":            ["Linux"],
    "unix":             ["Linux"],

    # Backend & Architecture
    "backend":          ["Backend"],
    "frontend":         ["Frontend"],
    "fullstack":        ["Full Stack"],
    "full-stack":       ["Full Stack"],
    "microservice":     ["Microservices"],
    "api":              ["API Design"],
    "rest api":         ["REST API"],
    "graphql":          ["GraphQL"],
    "grpc":             ["gRPC"],
    "system design":    ["System Design"],
    "distributed":      ["Distributed Systems"],
    "scalability":      ["Scalability"],

    # Career & Soft Skills
    "career":           ["Career Development"],
    "leadership":       ["Leadership"],
    "management":       ["Management"],
    "project management": ["Project Management"],
    "agile":            ["Agile"],
    "scrum":            ["Scrum"],
    "product manager":  ["Product Management"],
    "communication":    ["Communication"],
    "presentation":     ["Presentation"],
    "negotiation":      ["Negotiation"],

    # Mathematics & Science
    "calculus":         ["Calculus"],
    "linear algebra":   ["Linear Algebra"],
    "algebra":          ["Mathematics"],
    "mathematics":     ["Mathematics"],
    "physics":          ["Physics"],
    "chemistry":       ["Chemistry"],
    "biology":          ["Biology"],
    "bioinformatics":   ["Bioinformatics"],

    # Business & Finance
    "finance":          ["Finance"],
    "accounting":       ["Accounting"],
    "blockchain":       ["Blockchain"],
    "crypto":           ["Cryptocurrency"],
    "fintech":          ["FinTech"],
    "marketing":        ["Marketing"],
    "digital marketing":["Digital Marketing"],
    "seo":              ["SEO"],
    "ux ":              ["UX Design"],
    "ui ":              ["UI Design"],
    "ux design":        ["UX Design"],
    "ui design":        ["UI Design"],
    "product design":  ["Product Design"],
    "ux research":      ["UX Research"],

    # Security & Legal
    "cyber":            ["Cybersecurity"],
    "security":         ["Security"],
    "penetration":      ["Penetration Testing"],
    "ethical hack":     ["Ethical Hacking"],
    "network security": ["Network Security"],
    "privacy":          ["Privacy"],
    "legal":            ["Legal"],
    "compliance":       ["Compliance"],
    "gdpr":             ["Data Privacy"],
}

# Level normalization
LEVEL_MAP = {
    "foundations":  "Beginner",
    "beginner":     "Beginner",
    "intermediate":"Intermediate",
    "middle":       "Intermediate",
    "advanced":     "Advanced",
    "senior":       "Advanced",
    "specialist":   "Advanced",
    "expert":       "Advanced",
}


def extract_tags(course_name: str, summary: str, skills_in_db: list[str]) -> list[str]:
    """
    Extract relevant tags from course metadata using multi-layer strategy:

    Layer 1: Keyword matching on DOMAIN_TAG_MAP (fast, deterministic)
    Layer 2: Cross-reference with existing Skill names in DB
    Layer 3: Normalize to max 8 tags, dedupe, sort alphabetically
    """
    text = f"{course_name} {summary}".lower()
    tags: set[str] = set()

    # Layer 1: keyword matching (longer matches first to avoid partial overlap)
    sorted_domains = sorted(DOMAIN_TAG_MAP.keys(), key=len, reverse=True)
    for keyword in sorted_domains:
        if keyword in text:
            for tag in DOMAIN_TAG_MAP[keyword]:
                tags.add(tag)

    # Layer 2: fuzzy match against existing Skill names in DB
    for skill_name in skills_in_db:
        sn_lower = skill_name.lower()
        if sn_lower in text and len(sn_lower) >= 3:
            # Avoid duplicates with Layer 1
            if skill_name not in tags:
                tags.add(skill_name)

    # Layer 3: add broad category if very few tags
    if len(tags) < 2:
        if any(k in text for k in ["python", "java", "javascript", "programming", "code"]):
            tags.add("Programming")
        if any(k in text for k in ["algorithm", "data structure", "dsa"]):
            tags.add("Algorithms")
        if any(k in text for k in ["database", "sql", "query"]):
            tags.add("Databases")
        if any(k in text for k in ["web", "app", "frontend", "backend"]):
            tags.add("Software Engineering")

    return sorted(list(tags))[:8]  # Cap at 8 tags


def extract_provider(link: str) -> str:
    """Extract provider/institution from Coursera URL."""
    if not link:
        return "Coursera"
    # e.g. https://www.coursera.org/learn/python-for-applied-data-science-ai
    # e.g. https://www.coursera.org/specializations/python
    # e.g. https://www.coursera.org/professional-certificates/microsoft-python-developer
    parts = link.split("/")
    # Known institution subdomains often appear early
    known = ["google", "ibm", "microsoft", "meta", "amazon", "deeplearning",
             "stanford", "mit", "yale", "harvard", "duke", "upenn",
             "aws", "intel", "oracle"]
    for part in parts:
        p = part.lower()
        if any(k in p for k in known):
            return part.split("-")[0].title() + "".join(
                w.title() for w in part.split("-")[1:] if w not in ["and", "or", "the"]
            )
    return "Coursera"


def build_embedding_context(course_name: str, summary: str, level: str,
                              tags: list[str], duration_h: Optional[float]) -> str:
    """Build a rich, searchable text for vector embedding."""
    parts = [
        course_name,
        f"Level: {level}",
        f"Duration: {duration_h}h" if duration_h else None,
        f"Tags: {', '.join(tags)}" if tags else None,
        summary[:600],
    ]
    return " | ".join(p for p in parts if p)


# ─── OpenAI Embedding ─────────────────────────────────────────────────────────
def get_embedding(text: str) -> Optional[list[float]]:
    """Generate text-embedding-3-small (1536 dims) via OpenAI."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — vector will be NULL")
        return None
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        response = openai.embeddings.create(
            input=text[:8000],  # safety cap
            model="text-embedding-3-small",
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return None


# ─── Tag extraction via LLM (optional, for ambiguous courses) ────────────────
def llm_extract_tags_batch(courses: list[dict], openai_key: str) -> list[list[str]]:
    """
    Batch LLM-assisted tag extraction for all courses at once.
    Falls back gracefully if API unavailable.
    Returns list of tag lists aligned with input order.
    """
    if not openai_key:
        logger.warning("No OPENAI_API_KEY — skipping LLM tag enrichment")
        return [[] for _ in courses]

    try:
        import openai
        openai.api_key = openai_key

        courses_text = "\n".join(
            f"{i+1}. {c['course_name']} — {c.get('summary','')[:200]}"
            for i, c in enumerate(courses)
        )

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are a course categorization assistant. "
                    "For each course below, output EXACTLY one line: "
                    "'INDEX | tag1, tag2, tag3, tag4, tag5' where tags are "
                    "specific technical skill names (e.g. Python, Machine Learning, AWS). "
                    "Max 5 tags per course. Use canonical skill names."
                )},
                {"role": "user", "content": courses_text}
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        result: list[list[str]] = [[] for _ in courses]
        for line in raw.split("\n"):
            if "|" not in line:
                continue
            idx_str, tags_str = line.split("|", 1)
            try:
                idx = int(idx_str.strip()) - 1
                if 0 <= idx < len(courses):
                    result[idx] = [t.strip() for t in tags_str.split(",") if t.strip()]
            except ValueError:
                continue
        return result
    except Exception as e:
        logger.warning(f"LLM tag batch failed: {e} — using keyword extraction only")
        return [[] for _ in courses]


# ─── Main seeder ───────────────────────────────────────────────────────────────
def seed_coursera_300(force: bool = False, dry_run: bool = False,
                       skip_embed: bool = False):
    """Main entry point."""

    # ── Load dataset ──────────────────────────────────────────────────────────
    if not os.path.exists(DATASET_PATH):
        logger.error(f"Dataset not found: {DATASET_PATH}")
        sys.exit(1)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        raw_courses: list[dict] = json.load(f)

    logger.info(f"Loaded {len(raw_courses)} courses from Coursera300.json")

    # ── Load existing Skill names for cross-reference ─────────────────────────
    db = Session()
    try:
        existing_skills: list[str] = [s.name for s in db.query(Skill.name).all()]
        existing_count  = db.query(Course).count()
    finally:
        db.close()

    logger.info(f"Existing skills in DB: {len(existing_skills)}")
    logger.info(f"Existing courses in DB: {existing_count}")

    if not force and existing_count >= len(raw_courses):
        logger.info(
            f"DB already has {existing_count} courses ≥ {len(raw_courses)} in dataset. "
            "Skip (use --force to re-seed)."
        )
        return

    # ── LLM-assisted tag enrichment (optional batch call) ──────────────────────
    llm_tags: list[list[str]] = []
    if not dry_run:
        llm_tags = llm_extract_tags_batch(raw_courses, OPENAI_API_KEY or "")

    # ── Transform each course ─────────────────────────────────────────────────
    to_insert: list[dict] = []

    for i, raw in enumerate(raw_courses):
        course_name  = raw.get("course_name", "").strip()
        summary      = raw.get("summary", "").strip()
        link         = raw.get("link", "")
        raw_level    = raw.get("level", "Foundations").strip()
        certificate  = raw.get("certificate", "Yes")

        # Skip if already seeded (unless force)
        db = Session()
        try:
            if not force:
                exists = db.query(Course).filter(
                    Course.title == course_name,
                    Course.platform == "Coursera"
                ).first()
                if exists:
                    db.close()
                    continue
        finally:
            pass

        # Parse fields
        level         = LEVEL_MAP.get(raw_level.lower(), "Beginner")
        duration_h    = parse_duration_to_hours(raw.get("duration", ""))
        provider      = extract_provider(link)
        keyword_tags  = extract_tags(course_name, summary, existing_skills)
        # Merge LLM tags if available (union, cap 8)
        all_tags: list[str] = list(set(keyword_tags + llm_tags[i]))[:8]
        ctx           = build_embedding_context(course_name, summary, level, all_tags, duration_h)
        vector        = None if skip_embed else get_embedding(ctx)

        record = {
            "id":                uuid.uuid4(),
            "title":             course_name,
            "description":       summary,
            "platform":          "Coursera",
            "url":               link,
            "language":          "en",
            "level":             level,
            "is_certification":  certificate.lower() in ("yes", "true", "1"),
            "provider":          provider,
            "duration_hours":    duration_h,
            "cost_usd":          0.0,   # Coursera audit is free
            "tags":              all_tags,
            "embedding_context": ctx,
            "vector":            vector,
        }
        to_insert.append(record)
        db.close()

        if dry_run:
            logger.info(f"  [DRY] {course_name}")
            logger.info(f"        level={level} | duration={duration_h}h | tags={all_tags}")
        else:
            if (i + 1) % 50 == 0:
                logger.info(f"  ... processed {i+1}/{len(raw_courses)} courses")

    # ── Batch insert ───────────────────────────────────────────────────────────
    if dry_run:
        logger.info(f"\n[dry-run] Would insert {len(to_insert)} courses")
        return

    if not to_insert:
        logger.info("No new courses to insert.")
        return

    BATCH = 25  # commit every N records
    db = Session()
    inserted = 0
    try:
        for j, record in enumerate(to_insert):
            course = Course(**record)
            db.add(course)
            inserted += 1
            if (j + 1) % BATCH == 0:
                db.commit()
                logger.info(f"  Committed batch {j+1} (total inserted: {inserted})")
        db.commit()  # final batch
        logger.info(f"\n✅ Successfully seeded {inserted} Coursera courses")
    except Exception as e:
        db.rollback()
        logger.error(f"Batch insert failed: {e}")
        raise
    finally:
        db.close()

    # ── Verify ─────────────────────────────────────────────────────────────────
    db = Session()
    try:
        total = db.query(Course).filter(Course.platform == "Coursera").count()
        total_all = db.query(Course).count()
        logger.info(f"  Coursera courses in DB : {total}")
        logger.info(f"  Total courses in DB   : {total_all}")
    finally:
        db.close()


# ─── CLI entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed 300 Coursera courses into DB")
    parser.add_argument("--force",     action="store_true", help="Re-seed even if courses exist")
    parser.add_argument("--dry-run",   action="store_true", help="Show what would be inserted (no writes)")
    parser.add_argument("--skip-embed", action="store_true", help="Skip OpenAI embeddings (dev/fast mode)")
    args = parser.parse_args()

    seed_coursera_300(force=args.force, dry_run=args.dry_run, skip_embed=args.skip_embed)
