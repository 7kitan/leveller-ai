import hashlib
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import uuid
import re

from shared.models import Job
from shared.llm_utils import get_embedding, openai_client, LLM_PROVIDER, LLM_MODEL

logger = logging.getLogger("gap_calculator.retriever")


class RequirementRetriever:
    def __init__(self, db: Session):
        self.db = db

    async def extract(self, jd_text: str) -> List[Dict[str, Any]]:
        """AI Trích xuất JD với cơ chế 4-Layer Knowledge Retrieval (Hybrid)."""
        jd_text = jd_text.strip()
        jd_embedding = None

        # Layer 1: Exact Hit (Hash-based)
        text_hash = hashlib.sha256(jd_text.encode()).hexdigest()[:16]
        exact_id = f"cache_{text_hash}"
        exact_hit = self.db.query(Job).filter(Job.source_id == exact_id).first()
        if exact_hit and exact_hit.extracted_requirements_json:
            # DIRTY CACHE DETECTION:
            # 1. Skip if contains generic placeholders
            reqs = exact_hit.extracted_requirements_json
            reqs_str = json.dumps(reqs).lower()
            dirty_keywords = [
                "technologies",
                "alternative",
                "category",
                "required",
                "optional",
                "generic",
            ]
            is_dirty = any(
                f'"{kw}' in reqs_str or f" {kw}" in reqs_str for kw in dirty_keywords
            )

            # 2. Skip if it looks like the old "2-year default" extraction (heuristic)
            if not is_dirty and isinstance(reqs, list):
                years_list = []
                for r in reqs:
                    if r.get("type") == "skill":
                        years_list.append(r.get("years_required"))
                    elif r.get("type") == "group":
                        for s in r.get("skills", []):
                            years_list.append(s.get("years_required"))

                # If everything is exactly 2 years, it's likely a legacy extraction using the old forced default
                if len(years_list) > 2 and all(y == 2 for y in years_list):
                    is_dirty = True
                    logger.info(
                        "LAYER 1 DIRTY CACHE: Detected legacy 2-year default pattern."
                    )

            if not is_dirty:
                logger.info(f"LAYER 1 HIT: Exact hash match {text_hash}")
                return exact_hit.extracted_requirements_json
            logger.info(f"LAYER 1 DIRTY CACHE: Forcing re-extraction.")

        # Layer 2: Keyword Hit (Postgres FTS)
        keyword_hit = self._find_keyword_cache(jd_text)
        if keyword_hit:
            logger.info("LAYER 2 HIT: Semantic match via Keywords")
            return keyword_hit

        # Layer 3: Semantic Hit (Vector Similarity)
        logger.info("No text-based hits. Transitioning to Semantic Search (Vector)...")
        jd_embedding = get_embedding(jd_text)
        cached_reqs = self._find_semantic_cache(jd_text, jd_embedding)
        if cached_reqs:
            logger.info("LAYER 3 HIT: Matched via Vector Similarity")
            return cached_reqs

        # Layer 4: AI Extraction (Chat Completion)
        logger.info("Knowledge Retrieval failed. Executing AI Extraction (GPT)...")
        requirements = await self._ai_extract(jd_text)

        if requirements:
            self._save_to_cache(jd_text, jd_embedding, requirements)

        return requirements

    def _find_keyword_cache(self, jd_text: str) -> Optional[List[Dict[str, Any]]]:
        if len(jd_text) < 50:
            return None
        try:
            # Reset any aborted transaction
            try:
                self.db.rollback()
            except Exception:
                pass

            query = text("""
                SELECT source_id, extracted_requirements_json,
                       ts_rank_cd(to_tsvector('english', raw_text), plainto_tsquery('english', :text)) as rank
                FROM jobs
                WHERE to_tsvector('english', raw_text) @@ plainto_tsquery('english', :text)
                  AND extracted_requirements_json IS NOT NULL
                ORDER BY rank DESC
                LIMIT 1
            """)
            result = self.db.execute(query, {"text": jd_text}).first()
            if result and result.rank > 0.5:
                return result.extracted_requirements_json
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error checking keyword cache: {e}")
            return None

    def _find_semantic_cache(
        self, jd_text: str, embedding: List[float]
    ) -> Optional[List[Dict[str, Any]]]:
        if not embedding:
            return None
        try:
            # Reset any aborted transaction
            try:
                self.db.rollback()
            except Exception:
                pass

            query = text("""
                SELECT source_id, extracted_requirements_json, 1 - (vector <=> :vec::vector) as similarity
                FROM jobs
                WHERE vector IS NOT NULL AND extracted_requirements_json IS NOT NULL
                ORDER BY similarity DESC
                LIMIT 1
            """)
            result = self.db.execute(query, {"vec": embedding}).first()
            if result and result.similarity > 0.97:
                return result.extracted_requirements_json
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error checking semantic cache: {e}")
            return None

    def _save_to_cache(
        self, jd_text: str, embedding: List[float], requirements: List[Dict[str, Any]]
    ):
        try:
            # Reset any aborted transaction
            try:
                self.db.rollback()
            except Exception:
                pass

            text_hash = hashlib.sha256(jd_text.encode()).hexdigest()[:16]
            source_id = f"cache_{text_hash}"
            existing = self.db.query(Job).filter(Job.source_id == source_id).first()

            if existing:
                existing.extracted_requirements_json = requirements
                existing.last_analyzed_at = datetime.now()
                if embedding:
                    existing.vector = embedding
            else:
                new_job = Job(
                    id=uuid.uuid4(),
                    source_id=source_id,
                    title_raw="Cached Analysis",
                    raw_text=jd_text,
                    vector=embedding,
                    extracted_requirements_json=requirements,
                    last_analyzed_at=datetime.now(),
                    status="cache",
                )
                self.db.add(new_job)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save cache: {e}")

    async def _ai_extract(self, jd_text: str) -> List[Dict[str, Any]]:
        prompt = f"""
        YOU ARE A SENIOR TECHNICAL RECRUITMENT EXPERT.
        Extract the required technical skills from the following Job Description (JD).
        
        STRICT SCOPE: Extract ONLY pure technology skills.
        DO NOT extract soft skills, spoken languages, or general methodologies.
        
        CRITICAL RULES:
        1. NAME PRECISION: Extract specific technical names (e.g., 'SQL', 'ReactJS', 'Node.js') rather than generic categories (e.g., 'Database Technologies', 'Frontend Frameworks', 'Web Development').
        2. ATOMICITY RULE: NEVER combine technologies with '/' (e.g. "VueJS/ReactJS"). Split these into "exclusive" groups.
        3. SMART GROUPING: 
           - INCLUSIVE (AND): Mandatory tech stack elements that must all be present.
           - EXCLUSIVE (OR): Alternative options (e.g., "Java or C++", "at least one of X/Y/Z"). 
             IMPORTANT: Vietnamese phrases ("ít nhất 1", "hoặc") and slash symbols "/" indicate EXCLUSIVE strategy.
        4. YEARS OF EXPERIENCE & LEVEL: 
           - Set "years_required" to the specific number of years mentioned (e.g., "3 năm" -> 3).
           - IF NO duration or seniority is mentioned (e.g. "Hiểu REST API", "Có kiến thức Docker"), YOU MUST:
             a. Set "years_required" to 0.
             b. Set "target_level" to "Junior".
           - DO NOT hallucinate years. Only capture what is explicitly written. Use 0 as the safe minimum.

        JD CONTENT: 
        {jd_text}

        5. FEW-SHOT EXAMPLE:
           Input: "Kinh nghiệm với VueJS/ReactJS 2 năm và hiểu biết về Docker, REST API"
           Expected Output:
           {{
             "requirements": [
               {{
                 "type": "group",
                 "group_name": "Frontend Alternatives",
                 "group_strategy": "exclusive",
                 "skills": [
                   {{"skill": "VueJS", "target_level": "Mid-level", "years_required": 2}},
                   {{"skill": "ReactJS", "target_level": "Mid-level", "years_required": 2}}
                 ]
               }},
               {{
                 "type": "skill",
                 "skill": "Docker",
                 "target_level": "Junior",
                 "years_required": 0
               }},
               {{
                 "type": "skill",
                 "skill": "REST API",
                 "target_level": "Junior",
                 "years_required": 0
               }}
             ]
           }}

        6. JSON FORMAT: Return a JSON object with the key "requirements". Each element must contain:
           - type: "skill" or "group"
           - skill: Specific name (e.g., "PostgreSQL", NOT "Database")
           - group_strategy: "inclusive" or "exclusive"
           - skills: List of sub-skills (if type is "group").
           - target_level: (Junior, Mid-level, Senior, Expert)
           - years_required: integer (Default to 0 if not mentioned)
           - is_primary: true (mandatory) or false (optional)
           - importance_weight: 1-10 (default 5).

        Return ONLY valid JSON.
        """
        try:
            if LLM_PROVIDER == "openai":
                response = openai_client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )
                raw_content = response.choices[0].message.content
                raw = json.loads(raw_content)
                reqs = raw.get("requirements") or []

                normalized_reqs = []
                for r in reqs:
                    if r.get("type") == "group":
                        # ATOMIC FLATTENING: Nếu group là generic container, flatten nó ra thành từng skill lẻ
                        g_name = (r.get("group_name") or "Skill Group").lower()
                        container_keywords = [
                            "technologies",
                            "languages",
                            "requirements",
                            "tools",
                            "stack",
                            "category",
                            "alternative",
                        ]
                        is_generic_container = any(
                            kw in g_name for kw in container_keywords
                        )

                        if is_generic_container:
                            for s in r.get("skills", []):
                                normalized_reqs.append(
                                    {
                                        "type": "skill",
                                        "skill": s.get("skill"),
                                        "target_level": s.get("target_level")
                                        or "Junior",
                                        "years_required": s.get("years_required", 0),
                                        "is_primary": r.get("is_primary")
                                        if r.get("is_primary") is not None
                                        else True,
                                        "importance_weight": r.get("importance_weight")
                                        or 5,
                                    }
                                )
                            continue

                        sub_skills = []
                        for s in r.get("skills", []):
                            sub_skills.append(
                                {
                                    "skill": s.get("skill"),
                                    "target_level": s.get("target_level") or "Junior",
                                    "years_required": s.get("years_required", 0),
                                }
                            )
                        normalized_reqs.append(
                            {
                                "type": "group",
                                "group_name": r.get("group_name") or "Skill Group",
                                "group_strategy": r.get("group_strategy")
                                or "exclusive",
                                "skills": sub_skills,
                                "is_primary": r.get("is_primary")
                                if r.get("is_primary") is not None
                                else True,
                                "importance_weight": r.get("importance_weight") or 5,
                            }
                        )
                    else:
                        s_name = r.get("skill") or r.get("name")
                        if not s_name:
                            continue

                        # HEURISTIC FALLBACK: Split skills with slashes into an "OR" group if LLM missed it
                        if "/" in s_name and any(c.isalpha() for c in s_name):
                            # Handle nested slashes in parentheses like "Database (SQL/NoSQL)"
                            parts = []
                            if "(" in s_name and ")" in s_name:
                                match = re.search(r"\((.*)\)", s_name)
                                if match:
                                    inside = match.group(1)
                                    parts = [
                                        p.strip()
                                        for p in inside.split("/")
                                        if p.strip()
                                    ]

                            if not parts:
                                parts = [
                                    p.strip() for p in s_name.split("/") if p.strip()
                                ]

                            if len(parts) > 1:
                                sub_skills = []
                                for p in parts:
                                    p_clean = re.sub(r"[()\[\]{}]", "", p).strip()
                                    if not p_clean:
                                        continue
                                    sub_skills.append(
                                        {
                                            "skill": p_clean,
                                            "target_level": r.get("target_level")
                                            or "Junior",
                                            "years_required": r.get(
                                                "years_required", 0
                                            ),
                                        }
                                    )
                                normalized_reqs.append(
                                    {
                                        "type": "group",
                                        "group_name": f"{s_name} (Combined)",
                                        "group_strategy": "exclusive",
                                        "skills": sub_skills,
                                        "is_primary": r.get("is_primary")
                                        if r.get("is_primary") is not None
                                        else True,
                                        "importance_weight": r.get("importance_weight")
                                        or 5,
                                    }
                                )
                                continue

                        normalized_reqs.append(
                            {
                                "type": "skill",
                                "skill": s_name,
                                "target_level": r.get("target_level") or "Junior",
                                "years_required": r.get("years_required", 0),
                                "is_primary": r.get("is_primary")
                                if r.get("is_primary") is not None
                                else True,
                                "importance_weight": r.get("importance_weight") or 5,
                            }
                        )
                return normalized_reqs
            return []
        except Exception as e:
            logger.error(f"Error extracting requirements with AI: {str(e)}")
            return []
