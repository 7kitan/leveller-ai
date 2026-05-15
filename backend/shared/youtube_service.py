import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from shared.models import YouTubeCourse
from shared.llm_utils import get_embedding
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("youtube_service")

class YouTubeSearchService:
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.base_url = "https://www.googleapis.com/youtube/v3/search"

    async def search_and_cache(self, query: str, db: Session, limit: int = 3, lang: str = "en", domain: str = "programming") -> List[Dict[str, Any]]:
        """
        Tìm kiếm video YouTube với context chuyên ngành.
        Sử dụng Vector Search để tìm trong cache trước khi gọi API thật.
        
        Args:
            query: Skill name + level (e.g. "Python Beginner", "Docker Mid-level")
            db: Database session
            limit: Max results
            lang: Language code ("vi" or "en")
            domain: Domain context ("programming", "devops", "data-science", etc.)
        """
        # 1. Parse query to extract skill and level
        clean_query = query.strip()
        
        # Translate English level names to Vietnamese
        level_map_vi = {
            "beginner": "cơ bản",
            "intermediate": "trung cấp", 
            "mid-level": "trung cấp",
            "advanced": "nâng cao",
            "senior": "chuyên sâu",
            "expert": "chuyên gia"
        }
        
        # Extract level from query
        skill_name = clean_query
        level_suffix = ""
        target_skill_level = None  # For database matching
        
        # Map to database skill_level format
        level_to_db_map = {
            "beginner": "Junior",
            "junior": "Junior",
            "intermediate": "Mid-level",
            "mid-level": "Mid-level",
            "advanced": "Senior",
            "senior": "Senior",
            "expert": "Expert"
        }
        
        for eng_level, vi_level in level_map_vi.items():
            if eng_level in clean_query.lower():
                skill_name = clean_query.lower().replace(eng_level, "").strip()
                level_suffix = vi_level if lang == "vi" else eng_level
                target_skill_level = level_to_db_map.get(eng_level)
                break
        
        # 2. Build optimized queries
        skill_clean = skill_name.strip()
        
        # Vietnamese Query
        if level_suffix:
            vn_q = f"Khóa học {skill_clean} {level_suffix} hướng dẫn"
        else:
            vn_q = f"Khóa học {skill_clean} hướng dẫn đầy đủ"
            
        # English Fallback Query (Always keep this clean for best results)
        eng_level = next((k for k, v in level_map_vi.items() if v == level_suffix), "beginner")
        eng_q = f"{skill_clean} {domain} full course {eng_level}"

        # 2. Tạo embedding cho query (dùng English query để có semantic vector tốt nhất)
        query_vector = get_embedding(eng_q)
        now = datetime.now(timezone.utc)
        
        if query_vector:
            # 3. HYBRID SEARCH: Vector Similarity + BM25 Full-Text + Metadata Boosts
            try:
                # ... existing search logic ...
                tsquery = skill_clean.replace("'", "")
                # ...
                results = db.execute(
                    text(f"""
                        WITH ranked_videos AS (
                            SELECT 
                                yc.id, yc.video_id, yc.title, yc.description, yc.thumbnail, yc.channel_name, yc.url, yc.last_verified_at,
                                (yc.vector <=> :v) as distance,
                                (1 - (yc.vector <=> :v)) as similarity,
                                CASE WHEN yc.search_vector IS NOT NULL AND :has_ts THEN
                                    LEAST(ts_rank(yc.search_vector, websearch_to_tsquery('english', :tsquery)) * 2.0, 1.0)
                                ELSE 0 END as bm25_score,
                                CASE WHEN yc.is_curated = TRUE THEN 0.10 ELSE 0 END as curated_boost,
                                CASE WHEN yc.quality_score >= 80 THEN 0.05 WHEN yc.quality_score >= 60 THEN 0.02 ELSE 0 END as quality_boost,
                                CASE WHEN yc.skill_level = :target_level THEN 0.05 ELSE 0 END as level_boost,
                                CASE WHEN EXISTS (SELECT 1 FROM youtube_video_skills yvs WHERE yvs.video_id = yc.video_id AND yvs.skill_name ILIKE :skill) THEN 0.12 ELSE 0 END as skill_boost,
                                CASE WHEN yc.language = :lang THEN 0.03 ELSE 0 END as lang_boost
                            FROM youtube_courses yc
                            WHERE ((1 - (yc.vector <=> :v)) > 0.70 OR (yc.search_vector IS NOT NULL AND :has_ts AND yc.search_vector @@ websearch_to_tsquery('english', :tsquery)))
                            AND (yc.expires_at > :now OR yc.expires_at IS NULL)
                        )
                        SELECT *, (similarity * 0.5 + bm25_score * 0.3 + curated_boost + quality_boost + level_boost + skill_boost + lang_boost) as final_score
                        FROM ranked_videos WHERE similarity > 0.65 OR bm25_score > 0.1
                        ORDER BY final_score DESC LIMIT :l
                    """),
                    {
                        "v": str(query_vector), "l": limit * 2, "now": now, "skill": f"%{skill_clean}%",
                        "target_level": target_skill_level, "lang": lang, "tsquery": tsquery, "has_ts": bool(tsquery)
                    }
                ).fetchall()
            except Exception as sql_err:
                logger.warning(f"[YOUTUBE CACHE] Hybrid search failed: {sql_err}")
                results = []

            if results:
                final_results = []
                for r in results:
                    final_results.append(self._format_video_result(r))
                if final_results:
                    return final_results[:limit]

        # 4. Nếu không thấy trong cache, gọi YouTube API
        if not self.api_key:
            return []

        # List of queries to try (Vietnamese first, then English fallback)
        queries_to_try = [(vn_q, "vi")]
        if lang == "vi":
            queries_to_try.append((eng_q, "en"))
        else:
            # If default lang is en, just search English
            queries_to_try = [(eng_q, "en")]

        all_video_results = []
        
        for q_text, q_lang in queries_to_try:
            if len(all_video_results) >= limit:
                break

            logger.info(f"[YOUTUBE API] Searching: {q_text} (lang={q_lang})")
            try:
                params = {
                    "part": "snippet",
                    "q": q_text,
                    "type": "video",
                    "maxResults": limit * 4, # Fetch more to filter
                    "key": self.api_key,
                    "relevanceLanguage": q_lang,
                    "videoDuration": "any",  # Changed from 'long' to 'any' for better coverage
                    "videoDefinition": "high",
                    "order": "relevance",
                    "safeSearch": "moderate"
                }
                if q_lang == "vi":
                    params["regionCode"] = "VN"

                async with httpx.AsyncClient() as client:
                    response = await client.get(self.base_url, params=params)
                    if response.status_code == 403:
                        logger.error("[YOUTUBE API] 403 Forbidden - Likely quota exceeded")
                        break
                    response.raise_for_status()
                    data = response.json()

                items = data.get("items", [])
                
                for item in items:
                    snippet = item.get("snippet", {})
                    title = snippet.get("title", "").lower()
                    description = snippet.get("description", "").lower()
                    channel_name = snippet.get("channelTitle", "")
                    
                    # NEGATIVE FILTER: Skip interview/job-related content
                    interview_keywords = ["interview", "phỏng vấn", "phong van", "salary", "hired", "resume", "cv tips", "job search"]
                    if any(kw in title or kw in description for kw in interview_keywords):
                        continue
                    
                    # POSITIVE FILTER: Require strong learning indicators
                    learning_indicators = [
                        "tutorial", "course", "hướng dẫn", "khóa học", "learn", "học", "hoc", 
                        "guide", "beginner", "cơ bản", "step by step", "từng bước", "full course", "complete"
                    ]
                    if not any(ind in title or ind in description for ind in learning_indicators):
                        continue
                    
                    video_id = item.get("id", {}).get("videoId")
                    if not video_id:
                        continue

                    # Avoid duplicates in the same search session
                    if any(v["video_id"] == video_id for v in all_video_results):
                        continue

                    # Check DB to avoid unique constraint errors and reuse embeddings
                    existing = db.query(YouTubeCourse).filter(YouTubeCourse.video_id == video_id).first()
                    if not existing:
                        context = f"Title: {snippet.get('title')}. Channel: {channel_name}. Description: {description}"
                        vector = get_embedding(context)
                        
                        published_at = None
                        if snippet.get("publishedAt"):
                            try:
                                published_at = datetime.fromisoformat(snippet.get("publishedAt").replace("Z", "+00:00"))
                            except ValueError:
                                pass

                        new_video = YouTubeCourse(
                            video_id=video_id,
                            title=snippet.get("title"),
                            description=snippet.get("description"),
                            thumbnail=snippet.get("thumbnails", {}).get("high", {}).get("url"),
                            channel_name=channel_name,
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            embedding_context=context,
                            vector=vector,
                            published_at=published_at,
                            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                            last_verified_at=datetime.now(timezone.utc),
                            language=q_lang,
                            skill_level=target_skill_level,
                            is_curated=False
                        )
                        db.add(new_video)
                        
                        # Auto-tag skills
                        if skill_name and skill_name.strip():
                            import uuid
                            try:
                                db.execute(
                                    text("""
                                        INSERT INTO youtube_video_skills (id, video_id, skill_name)
                                        VALUES (:id, :vid, :skill)
                                        ON CONFLICT (video_id, skill_name) DO NOTHING
                                    """),
                                    {
                                        "id": str(uuid.uuid4()),
                                        "vid": video_id, 
                                        "skill": skill_name.strip()
                                    }
                                )
                            except Exception as e:
                                logger.warning(f"[YOUTUBE API] Failed to auto-tag skill '{skill_name}' for video {video_id}: {e}")

                        video_data = {
                            "video_id": video_id,
                            "title": snippet.get("title"),
                            "description": snippet.get("description"),
                            "thumbnail": new_video.thumbnail,
                            "channel_name": channel_name,
                            "url": new_video.url,
                            "embed_url": f"https://www.youtube.com/embed/{video_id}",
                            "language": q_lang,
                            "skill_level": target_skill_level,
                            "is_curated": False
                        }
                    else:
                        video_data = {
                            "video_id": existing.video_id,
                            "title": existing.title,
                            "description": existing.description,
                            "thumbnail": existing.thumbnail,
                            "channel_name": existing.channel_name,
                            "url": existing.url,
                            "embed_url": f"https://www.youtube.com/embed/{existing.video_id}",
                            "language": existing.language,
                            "skill_level": existing.skill_level,
                            "is_curated": existing.is_curated
                        }
                    
                    all_video_results.append(video_data)
                    if len(all_video_results) >= limit:
                        break

            except Exception as e:
                logger.error(f"[YOUTUBE API] Search iteration failed: {str(e)}")
                continue

        try:
            db.commit()
        except Exception as commit_err:
            logger.warning(f"[YOUTUBE API] Failed to commit new videos: {commit_err}")
            db.rollback()

        return all_video_results[:limit]

    def _format_video_result(self, r) -> Dict[str, Any]:
        return {
            "id": str(r.id),
            "video_id": r.video_id,
            "title": r.title,
            "description": r.description,
            "thumbnail": r.thumbnail,
            "channel_name": r.channel_name,
            "url": r.url,
            "embed_url": f"https://www.youtube.com/embed/{r.video_id}",
            # Include metadata for filtering and display
            "language": r.language if hasattr(r, 'language') else None,
            "skill_level": r.skill_level if hasattr(r, 'skill_level') else None,
            "is_curated": r.is_curated if hasattr(r, 'is_curated') else False,
            "quality_score": r.quality_score if hasattr(r, 'quality_score') else None
        }

    async def verify_videos_availability(self, video_ids: List[str]) -> List[str]:
        """
        Kiểm tra danh sách Video ID có còn Public và Embeddable hay không.
        Sử dụng YouTube API videos.list.
        """
        if not self.api_key or not video_ids:
            return video_ids # Giả định là ok nếu không có key

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={
                        "part": "status,snippet",
                        "id": ",".join(video_ids),
                        "key": self.api_key
                    }
                )
                response.raise_for_status()
                data = response.json()

            valid_ids = []
            items = data.get("items", [])
            
            for item in items:
                v_id = item.get("id")
                status = item.get("status", {})
                
                # Điều kiện: Public + Embeddable
                is_public = status.get("privacyStatus") == "public"
                is_embeddable = status.get("embeddable", True)
                
                if is_public and is_embeddable:
                    valid_ids.append(v_id)
            
            return valid_ids

        except Exception as e:
            logger.error(f"[YOUTUBE VERIFY] Verification failed: {str(e)}")
            return video_ids # Fallback: giữ lại để tránh mất dữ liệu khi API lỗi

# Singleton instance
youtube_service = YouTubeSearchService()
