import logging
import re
import time
from worker.celery_app import celery_app
from shared.scrapers.coursera import scrape_coursera_course
from shared.scrapers.topcv import TopCVScraper
from shared.database import SessionLocal
from shared.models import Job, SystemSetting, Course
from shared.llm_utils import get_embedding

logger = logging.getLogger("crawler_worker")

@celery_app.task(name="worker.tasks.crawler_tasks.crawl_course_task")
def crawl_course_task(url: str, auto_save: bool = False):
    """
    Background Task to crawl course meta-data from a URL.
    if auto_save=True, saves directly to the DB without returning to API.
    """
    logger.info(f"🚀 [CRAWLER] Received task for URL: {url} (auto_save={auto_save})")
    
    try:
        if "coursera.org" in url:
            logger.info(f"🔍 [CRAWLER] URL identified as Coursera. Calling scraper...")
            result = scrape_coursera_course(url)
            
            if not result or "error" in result:
                err = result.get('error', 'Scraper returned empty data') if result else 'Scraper returned empty data'
                logger.error(f"❌ [CRAWLER] Scrape failed for {url}: {err}")
                return {"error": err}
            
            if auto_save:
                from shared.llm_utils import get_embedding
                import uuid
                
                db = SessionLocal()
                try:
                    # Deduplication
                    source_id = result.get('source_id')
                    existing = db.query(Course).filter(Course.source_id == source_id).first() if source_id else None
                    if not existing:
                        existing = db.query(Course).filter(Course.url == url).first()
                    
                    if existing:
                        logger.info(f"⏭️ [CRAWLER] Course already exists: {result.get('name')} - Skipping save")
                        return result
                        
                    platform = result.get('source_platform', 'Coursera')
                    title = result.get('name', 'Unknown')
                    provider = result.get('provider') or platform
                    description = result.get('description', '')
                    modules = result.get('modules', [])
                    skills = result.get('skills', [])
                    outcomes = result.get('outcomes', [])
                    
                    context = (
                        f"PLATFORM: {platform}. TITLE: {title}. PROVIDER: {provider}. "
                        f"DESCRIPTION: {description}. MODULES: {', '.join(modules)}. "
                        f"SKILLS: {', '.join(skills)}. OUTCOMES: {', '.join(outcomes)}."
                    )
                    
                    # Generate embedding
                    vector = get_embedding(context)
                    
                    course = Course(
                        id=uuid.uuid4(),
                        title=title,
                        description=description,
                        platform="Coursera",
                        source_platform=platform,
                        source_id=source_id,
                        external_uuid=result.get('external_uuid'),
                        url=url,
                        level=result.get('level', 'Beginner'),
                        provider=provider,
                        duration_hours=result.get('duration_hours'),
                        duration_raw=result.get('duration_raw'),
                        cost_usd=0,
                        languages=result.get('languages', []),
                        tags=skills[:10],
                        skills_raw=skills,
                        outcomes=outcomes,
                        modules=modules,
                        embedding_context=context,
                        vector=vector
                    )
                    
                    db.add(course)
                    db.commit()
                    logger.info(f"✨ [CRAWLER] Cào và Auto-save thành công: '{title}'")
                except Exception as e:
                    db.rollback()
                    logger.error(f"💥 [CRAWLER] Auto-save failed cho {url}: {e}")
                    return {"error": f"Auto save failed: {str(e)}"}
                finally:
                    db.close()
            else:
                logger.info(f"✅ [CRAWLER] Scrape successful (no save): '{result.get('name')}'")
                
            return result
        else:
            logger.warning(f"⚠️ [CRAWLER] Unsupported URL pattern: {url}")
            return {"error": "Only Coursera URLs are supported at this time."}
    except Exception as e:
        logger.error(f"❌ [CRAWLER] Unexpected error crawling {url}: {e}", exc_info=True)
        return {"error": str(e)}
            

@celery_app.task(name="worker.tasks.crawler_tasks.crawl_topcv_jobs_task")
def crawl_topcv_jobs_task(limit: int = 20, force: bool = False):
    """
    Background Task to crawl latest Tehc jobs from TopCV.
    Runs every 30 mins via Celery Beat.
    """
    logger.info(f"🚀 [TOPCV CRAWLER] Starting crawl cycle (limit={limit}, force={force})...")
    scraper = TopCVScraper()
    urls = scraper.get_latest_job_urls(limit=limit)
    
    if not urls:
        logger.warning("⚠️ [TOPCV CRAWLER] No job URLs found. Possible block or empty result.")
        return {"status": "no_urls_found"}

    db = SessionLocal()
    
    # Check if crawling is enabled in settings (bypass if force=True)
    if not force:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "topcv_crawl_enabled").first()
        if setting and not setting.value:
            logger.info("⏭️ [TOPCV CRAWLER] Crawl cycle skipped (disabled in system settings).")
            db.close()
            return {"status": "disabled_by_settings"}

    new_jobs_count = 0
    try:
        for url in urls:
            # Check ID
            job_id_match = re.search(r'/(\d+)\.html', url)
            if not job_id_match: continue
            source_id = f"TOPCV_{job_id_match.group(1)}"
            
            existing = db.query(Job).filter(Job.source_id == source_id).first()
            if existing:
                logger.debug(f"⏭️ [TOPCV CRAWLER] Skipping existing job: {source_id}")
                continue
            
            # Scrape
            data = scraper.scrape_job_details(url)
            if not data: continue
            
            # Generate Embedding
            embedding_ctx = f"{data['title_raw']} at {data['company_name']}. {data['location_raw']}. {data['raw_text'][:1000]}"
            vector = get_embedding(embedding_ctx)
            
            # Save
            job = Job(**data)
            job.embedding_context = embedding_ctx
            job.vector = vector
            
            db.add(job)
            new_jobs_count += 1
            logger.info(f"✨ [TOPCV CRAWLER] Added new job: {data['title_raw']} ({source_id})")
            
            # Sleep a bit between scrapes to be polite
            time.sleep(1)
            
        db.commit()
        logger.info(f"✅ [TOPCV CRAWLER] Cycle complete. Added {new_jobs_count} new jobs.")
        return {"status": "success", "new_jobs": new_jobs_count}
        
    except Exception as e:
        db.rollback()
        logger.error(f"💥 [TOPCV CRAWLER] Critical error: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()
