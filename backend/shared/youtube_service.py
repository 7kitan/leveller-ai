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
        
        for eng_level, vi_level in level_map_vi.items():
            if eng_level in clean_query.lower():
                skill_name = clean_query.lower().replace(eng_level, "").strip()
                level_suffix = vi_level if lang == "vi" else eng_level
                break
        
        # 2. Build optimized query with domain context
        if lang == "vi":
            # Vietnamese: "Lập trình Python cơ bản" or "Học Docker DevOps"
            domain_prefix = {
                "programming": "Lập trình",
                "devops": "DevOps",
                "data-science": "Khoa học dữ liệu",
                "web-development": "Phát triển web",
                "mobile": "Lập trình mobile"
            }.get(domain, "Lập trình")
            
            if level_suffix:
                final_q = f"{domain_prefix} {skill_name} {level_suffix} tutorial"
            else:
                final_q = f"{domain_prefix} {skill_name} hướng dẫn"
        else:
            # English: "Python programming tutorial beginner" or "Docker DevOps course"
            if level_suffix:
                final_q = f"{skill_name} {domain} tutorial {level_suffix}"
            else:
                final_q = f"{skill_name} {domain} tutorial course"

        # 2. Tạo embedding cho query (dùng final_q để đồng bộ với nội dung tìm kiếm thực tế)
        query_vector = get_embedding(final_q)
        now = datetime.now(timezone.utc)
        
        if query_vector:
            # 3. Tìm kiếm trong Cache bằng Vector Similarity (Threshold 0.85)
            # ... (keep existing cache logic)
            results = db.execute(
                text("""
                    SELECT id, video_id, title, description, thumbnail, channel_name, url, (vector <=> :v) as distance
                    FROM youtube_courses
                    WHERE (1 - (vector <=> :v)) > 0.85
                      AND (expires_at > :now OR expires_at IS NULL)
                    ORDER BY distance ASC
                    LIMIT :l
                """),
                {"v": str(query_vector), "l": limit, "now": now}
            ).fetchall()

            if results:
                # ... (rest of cache logic)
                logger.info(f"[YOUTUBE CACHE] Found {len(results)} matches. Checking verification age...")
                
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
                "maxResults": limit * 2,  # Fetch more to filter later
                "key": self.api_key,
                "relevanceLanguage": lang,
                "videoDuration": "medium",  # Filter out shorts (<4min) and very long (>20min)
                "videoDefinition": "any",  # Accept both HD and SD
                "order": "relevance",  # Sort by relevance first
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
                
                # Skip videos with spam/clickbait indicators
                spam_keywords = ["click here", "subscribe now", "free download", "hack", "crack", "pirate"]
                if any(kw in title or kw in description for kw in spam_keywords):
                    continue
                
                # Skip videos from suspicious channels (very short names, all caps)
                if len(channel_name) < 3 or channel_name.isupper():
                    continue
                
                # Prioritize educational channels (common patterns)
                quality_indicators = ["tutorial", "course", "learn", "programming", "coding", "hướng dẫn", "học"]
                has_quality = any(ind in title or ind in description for ind in quality_indicators)
                
                if has_quality or len(filtered_items) < limit:
                    filtered_items.append(item)
                
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
                        last_verified_at=now # Đánh dấu vừa check xong
                    )
                    db.add(new_video)
                    db.flush() # Để lấy ID nếu cần
                    
                    video_data = {
                        "video_id": video_id,
                        "title": title,
                        "description": description,
                        "thumbnail": thumbnail,
                        "channel_name": channel_name,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "embed_url": f"https://www.youtube.com/embed/{video_id}"
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
            "embed_url": f"https://www.youtube.com/embed/{r.video_id}"
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
