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

    async def search_and_cache(self, query: str, db: Session, limit: int = 3, lang: str = "en") -> List[Dict[str, Any]]:
        """
        Tìm kiếm video YouTube.
        Sử dụng Vector Search để tìm trong cache trước khi gọi API thật.
        """
        # Tối ưu query theo ngôn ngữ
        search_query = query
        if lang == "vi":
            if "tiếng việt" not in query.lower():
                search_query = f"{query} tiếng Việt"
        
        # 1. Tạo embedding cho query (dùng search_query để khớp với nội dung ngôn ngữ)
        query_vector = get_embedding(search_query)
        now = datetime.now(timezone.utc)
        
        if query_vector:
            # 2. Tìm kiếm trong Cache bằng Vector Similarity (Threshold 0.85)
            # Chỉ lấy các video chưa hết hạn (expires_at > now)
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
                logger.info(f"[YOUTUBE CACHE] Found {len(results)} matches. Checking verification age...")
                
                now = datetime.now(timezone.utc)
                verification_threshold = now - timedelta(days=7) # Chỉ kiểm tra lại nếu quá 7 ngày
                
                # Phân loại: video nào cần check lại, video nào dùng luôn
                to_verify = []
                final_results = []
                
                for r in results:
                    # R.last_verified_at có thể là None nếu mới được crawl
                    if not r.last_verified_at or r.last_verified_at < verification_threshold:
                        to_verify.append(r)
                    else:
                        final_results.append(self._format_video_result(r))
                
                if to_verify:
                    logger.info(f"[YOUTUBE VERIFY] Verifying {len(to_verify)} stale videos...")
                    valid_ids = await self.verify_videos_availability([v.video_id for v in to_verify])
                    
                    for v in to_verify:
                        # Fetch the actual object for ORM update/delete
                        db_video = db.query(YouTubeCourse).filter(YouTubeCourse.video_id == v.video_id).first()
                        if not db_video:
                            continue

                        if v.video_id in valid_ids:
                            # Update verification time using ORM
                            db_video.last_verified_at = now
                            final_results.append(self._format_video_result(v))
                        else:
                            logger.warning(f"[YOUTUBE CACHE] Video {v.video_id} is no longer available. Removing.")
                            db.delete(db_video)
                    
                    db.commit()

                if final_results:
                    return final_results[:limit]

        # 3. Nếu không thấy trong cache hoặc similarity thấp, gọi YouTube API
        if not self.api_key:
            logger.warning("[YOUTUBE API] No API Key found. Skipping search.")
            return []

        logger.info(f"[YOUTUBE API] Calling YouTube Search for: {search_query} (lang={lang})")
        try:
            # Tối ưu hóa từ khóa theo ngôn ngữ
            keyword_suffix = "course tutorial"
            if lang == "vi":
                keyword_suffix = "khóa học hướng dẫn"
            
            final_q = f"{search_query} {keyword_suffix}"

            params = {
                "part": "snippet",
                "q": final_q,
                "type": "video",
                "maxResults": limit,
                "key": self.api_key,
                "relevanceLanguage": lang
            }
            if lang == "vi":
                params["regionCode"] = "VN"

            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

            items = data.get("items", [])
            results = []

            for item in items:
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
