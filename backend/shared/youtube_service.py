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
        
        # 2. Build optimized query with domain context
        if lang == "vi":
            # Vietnamese: "Khóa học Lập trình Python trọn bộ" or "Hướng dẫn Docker DevOps đầy đủ"
            domain_prefix = {
                "programming": "Lập trình",
                "devops": "DevOps",
                "data-science": "Khoa học dữ liệu",
                "web-development": "Phát triển web",
                "mobile": "Lập trình mobile",
                "domain-knowledge": "về",
                "soft-skills": "Kỹ năng mềm",
                "certifications": "Chứng chỉ"
            }.get(domain, "")
            
            if level_suffix:
                final_q = f"Khóa học {domain_prefix} {skill_name} {level_suffix} trọn bộ"
            else:
                final_q = f"Khóa học {domain_prefix} {skill_name} đầy đủ nhất"
        else:
            # English: "Python programming full course beginner" or "Docker DevOps complete tutorial"
            if level_suffix:
                final_q = f"{skill_name} {domain} full course {level_suffix}"
            else:
                final_q = f"{skill_name} {domain} complete tutorial course"

        # 2. Tạo embedding cho query (dùng final_q để đồng bộ với nội dung tìm kiếm thực tế)
        query_vector = get_embedding(final_q)
        now = datetime.now(timezone.utc)
        
        if query_vector:
            # 3. HYBRID SEARCH: Vector Similarity + BM25 Full-Text + Metadata Boosts
            # 
            # Scoring System (Weighted):
            # - Vector similarity (50%): Semantic understanding (0.75 - 1.0) × 0.5 = 0.375 - 0.5
            # - BM25 text rank (30%): Keyword matching (0 - 1.0) × 0.3 = 0 - 0.3
            # - Metadata boosts (20%): Curated, quality, level, skill, language = 0 - 0.35
            # 
            # Total possible score: 0.375 (min) to 1.15 (max)
            # 
            # Example: "Python Beginner" query
            # - Curated Python tutorial: vector=0.82, bm25=0.95, boosts=0.25 → 0.41 + 0.285 + 0.25 = 0.945
            # - Generic programming video: vector=0.85, bm25=0.20, boosts=0.05 → 0.425 + 0.06 + 0.05 = 0.535
            # → Curated video wins despite lower vector similarity!
            
            # Build tsquery for BM25 search
            # Clean and prepare search terms - filter out '&' and empty strings to avoid syntax errors
            search_terms = [t for t in skill_name.strip().replace("'", "").split() if t and t != '&']
            tsquery = " & ".join(search_terms) if search_terms else ""
            
            # Use separate queries or conditional logic if tsquery is empty
            bm25_score_sql = "0"
            bm25_filter_sql = "FALSE"
            if tsquery:
                bm25_score_sql = "LEAST(ts_rank(yc.search_vector, to_tsquery('english', :tsquery)) * 2.0, 1.0)"
                bm25_filter_sql = "yc.search_vector @@ to_tsquery('english', :tsquery)"

            try:
                results = db.execute(
                    text(f"""
                        WITH ranked_videos AS (
                            SELECT 
                                yc.id,
                                yc.video_id,
                                yc.title,
                                yc.description,
                                yc.thumbnail,
                                yc.channel_name,
                                yc.url,
                                yc.last_verified_at,
                                (yc.vector <=> :v) as distance,
                                (1 - (yc.vector <=> :v)) as similarity,
                                -- BM25 full-text search score (0-1 normalized)
                                CASE 
                                    WHEN yc.search_vector IS NOT NULL AND :has_ts THEN
                                        {bm25_score_sql}
                                    ELSE 0
                                END as bm25_score,
                                -- Metadata boost factors
                                CASE WHEN yc.is_curated = TRUE THEN 0.10 ELSE 0 END as curated_boost,
                                CASE WHEN yc.quality_score >= 80 THEN 0.05 
                                     WHEN yc.quality_score >= 60 THEN 0.02 
                                     ELSE 0 END as quality_boost,
                                CASE WHEN yc.skill_level = :target_level THEN 0.05 ELSE 0 END as level_boost,
                                CASE WHEN EXISTS (
                                     SELECT 1 FROM youtube_video_skills yvs
                                     WHERE yvs.video_id = yc.video_id 
                                     AND yvs.skill_name ILIKE :skill
                                ) THEN 0.12 ELSE 0 END as skill_boost,
                                CASE WHEN yc.language = :lang THEN 0.03 ELSE 0 END as lang_boost
                            FROM youtube_courses yc
                            WHERE (
                                -- Vector search OR text search (union of results)
                                (1 - (yc.vector <=> :v)) > 0.70
                                OR (yc.search_vector IS NOT NULL AND :has_ts AND {bm25_filter_sql})
                            )
                            AND (yc.expires_at > :now OR yc.expires_at IS NULL)
                        )
                        SELECT 
                            id, video_id, title, description, thumbnail, channel_name, url, 
                            last_verified_at, distance, similarity, bm25_score,
                            -- Hybrid score: 50% vector + 30% BM25 + 20% boosts
                            (
                                (similarity * 0.5) + 
                                (bm25_score * 0.3) + 
                                (curated_boost + quality_boost + level_boost + skill_boost + lang_boost)
                            ) as final_score
                        FROM ranked_videos
                        WHERE similarity > 0.70 OR bm25_score > 0.1
                        ORDER BY final_score DESC, distance ASC
                        LIMIT :l
                    """),
                    {
                        "v": str(query_vector), 
                        "l": limit * 2,  # Fetch more to ensure quality after verification
                        "now": now,
                        "skill": f"%{skill_name}%",
                        "target_level": target_skill_level,
                        "lang": lang,
                        "tsquery": tsquery,
                        "has_ts": bool(tsquery)
                    }
                ).fetchall()
            except Exception as sql_err:
                logger.warning(f"[YOUTUBE CACHE] Hybrid search failed: {sql_err}")
                if db:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                results = []

            if results:
                # Log scoring details
                curated_count = sum(1 for r in results if hasattr(r, 'final_score'))
                logger.info(
                    f"[YOUTUBE CACHE] Found {len(results)} matches with boost scoring. "
                    f"Skill: '{skill_name}', Level: {target_skill_level}, Lang: {lang}. "
                    f"Checking verification age..."
                )
                
                now = datetime.now(timezone.utc)
                verification_threshold = now - timedelta(days=7) # Chỉ kiểm tra lại nếu quá 7 ngày
                
                to_verify = []
                final_results = []
                
                for r in results:
                    if not r.last_verified_at or r.last_verified_at < verification_threshold:
                        to_verify.append(r)
                    else:
                        final_results.append(self._format_video_result(r))
                
                if to_verify:
                    logger.info(f"[YOUTUBE VERIFY] Verifying {len(to_verify)} stale videos...")
                    try:
                        valid_ids = await self.verify_videos_availability([v.video_id for v in to_verify])
                        
                        for v in to_verify:
                            db_video = db.query(YouTubeCourse).filter(YouTubeCourse.video_id == v.video_id).first()
                            if not db_video:
                                continue

                            if v.video_id in valid_ids:
                                db_video.last_verified_at = now
                                final_results.append(self._format_video_result(v))
                            else:
                                logger.warning(f"[YOUTUBE CACHE] Video {v.video_id} is no longer available. Removing.")
                                db.delete(db_video)
                        
                        db.commit()
                    except Exception as verify_err:
                        logger.warning(f"[YOUTUBE VERIFY] Failed to verify/update videos: {verify_err}")
                        if db:
                            try:
                                db.rollback()
                            except Exception:
                                pass
                        # Fallback: still return whatever was already in final_results

                if final_results:
                    return final_results[:limit]

        # 4. Nếu không thấy trong cache hoặc similarity thấp, gọi YouTube API
        if not self.api_key:
            logger.warning("[YOUTUBE API] No API Key found. Skipping search.")
            return []

        logger.info(f"[YOUTUBE API] Calling YouTube Search for: {final_q} (lang={lang}, domain={domain})")
        try:
            params = {
                "part": "snippet",
                "q": final_q,
                "type": "video",
                "maxResults": limit * 3,  # Fetch more to filter later
                "key": self.api_key,
                "relevanceLanguage": lang,
                "videoDuration": "long",  # Changed from 'medium' to 'long' (>20min) to get real courses
                "videoDefinition": "high",  # Prioritize HD
                "order": "relevance",
                "safeSearch": "moderate"
            }
            if lang == "vi":
                params["regionCode"] = "VN"

            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

            items = data.get("items", [])
            
            # Post-filter: Remove low-quality videos
            filtered_items = []
            for item in items:
                snippet = item.get("snippet", {})
                title = snippet.get("title", "").lower()
                description = snippet.get("description", "").lower()
                channel_name = snippet.get("channelTitle", "")
                
                # NEGATIVE FILTER 1: Skip interview/job-related content
                interview_keywords = [
                    "interview", "phỏng vấn", "phong van",
                    "câu hỏi phỏng vấn", "cau hoi phong van",
                    "interview questions", "interview tips",
                    "mock interview", "job interview",
                    "salary negotiation", "resume tips",
                    "career advice", "how to get hired"
                ]
                if any(kw in title or kw in description for kw in interview_keywords):
                    logger.debug(f"[YOUTUBE FILTER] Skipped interview video: {title[:50]}")
                    continue
                
                # NEGATIVE FILTER 2: Skip spam/clickbait
                spam_keywords = ["click here", "subscribe now", "free download", "hack", "crack", "pirate"]
                if any(kw in title or kw in description for kw in spam_keywords):
                    continue
                
                # NEGATIVE FILTER 3: Skip suspicious channels
                if len(channel_name) < 3 or channel_name.isupper():
                    continue
                
                # POSITIVE FILTER: Require strong learning indicators
                # Use specific keywords that appear in tutorials but NOT in interviews
                strong_learning_indicators = [
                    "tutorial", "course", "hướng dẫn", "khóa học",
                    "full course", "trọn bộ", "đầy đủ", "complete tutorial",
                    "beginner", "cơ bản", "co ban",
                    "step by step", "từng bước", "tu tung buoc",
                    "complete guide", "hướng dẫn đầy đủ",
                    "learn", "học", "hoc",
                    "introduction", "giới thiệu"
                ]
                has_strong_indicator = any(ind in title or ind in description for ind in strong_learning_indicators)
                
                # ONLY accept videos with strong learning indicators
                if has_strong_indicator:
                    filtered_items.append(item)
                    logger.debug(f"[YOUTUBE FILTER] Accepted tutorial video: {title[:50]}")
                else:
                    logger.debug(f"[YOUTUBE FILTER] Skipped non-tutorial video: {title[:50]}")
                
                if len(filtered_items) >= limit:
                    break
            
            results = []

            for item in filtered_items:
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId")
                if not video_id:
                    continue

                title = snippet.get("title")
                description = snippet.get("description")
                thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url")
                channel_name = snippet.get("channelTitle")
                published_at_str = snippet.get("publishedAt")
                
                # Check if exists in DB by video_id (để tránh lỗi Unique Constraint)
                existing = db.query(YouTubeCourse).filter(YouTubeCourse.video_id == video_id).first()
                if not existing:
                    # Tạo embedding context cho video mới
                    context = f"Title: {title}. Channel: {channel_name}. Description: {description}"
                    vector = get_embedding(context)

                    published_at = None
                    if published_at_str:
                        published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))

                    # Auto-tag with metadata from search context
                    # This enables boost scoring and filtering for auto-cached videos
                    auto_language = lang if lang in ["en", "vi"] else None
                    auto_skill_level = target_skill_level  # Already mapped to DB format (Junior/Mid-level/Senior/Expert)

                    new_video = YouTubeCourse(
                        video_id=video_id,
                        title=title,
                        description=description,
                        thumbnail=thumbnail,
                        channel_name=channel_name,
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        embedding_context=context,
                        vector=vector,
                        published_at=published_at,
                        expires_at=now + timedelta(days=30), # Cache trong 30 ngày
                        last_verified_at=now, # Đánh dấu vừa check xong
                        # Auto-tag metadata for boost scoring and filtering
                        language=auto_language,
                        skill_level=auto_skill_level,
                        is_curated=False  # Mark as auto-cached (not manually curated)
                    )
                    db.add(new_video)
                    db.flush() # Để lấy ID nếu cần
                    
                    # Auto-tag skills in junction table
                    # This enables skill-based boost scoring (+0.12) and filtering
                    if skill_name and skill_name.strip():
                        from sqlalchemy import text as sql_text
                        try:
                            db.execute(
                                sql_text("""
                                    INSERT INTO youtube_video_skills (video_id, skill_name)
                                    VALUES (:vid, :skill)
                                    ON CONFLICT (video_id, skill_name) DO NOTHING
                                """),
                                {"vid": video_id, "skill": skill_name.strip()}
                            )
                        except Exception as e:
                            logger.warning(f"[YOUTUBE CACHE] Failed to auto-tag skill '{skill_name}' for video {video_id}: {e}")
                    
                    video_data = {
                        "video_id": video_id,
                        "title": title,
                        "description": description,
                        "thumbnail": thumbnail,
                        "channel_name": channel_name,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "embed_url": f"https://www.youtube.com/embed/{video_id}",
                        # Include auto-tagged metadata in response
                        "language": auto_language,
                        "skill_level": auto_skill_level,
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
                        "embed_url": f"https://www.youtube.com/embed/{existing.video_id}"
                    }
                
                results.append(video_data)

            db.commit()
            return results

        except Exception as e:
            logger.error(f"[YOUTUBE API] Search failed: {str(e)}")
            return []

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
