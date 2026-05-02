import logging
import re
import time
import os
import uuid
from worker.celery_app import celery_app
from shared.scrapers.coursera import scrape_coursera_course
from shared.scrapers.topcv import TopCVScraper
from shared.database import SessionLocal
from shared.models import Job, SystemSetting, Course
from shared.llm_utils import normalize_location
from shared.skill_extraction import extract_and_save_job_skills
from shared.system_logger import system_logger

logger = logging.getLogger("crawler_worker")

@celery_app.task(name="worker.tasks.crawler_tasks.crawl_course_task")
def crawl_course_task(url: str, auto_save: bool = False):
    """
    Background Task to crawl course meta-data from a URL.
    if auto_save=True, saves directly to the DB without returning to API.
    """
    logger.info(f"🚀 [CRAWLER] Received task for URL: {url} (auto_save={auto_save})")
    system_logger.info("CRAWLER", f"Received course crawl task for: {url}")
    
    try:
        if "coursera.org" in url:
            logger.info(f"🔍 [CRAWLER] URL identified as Coursera. Calling scraper...")
            result = scrape_coursera_course(url)
            
            if not result or "error" in result:
                err = result.get('error', 'Scraper returned empty data') if result else 'Scraper returned empty data'
                logger.error(f"❌ [CRAWLER] Scrape failed for {url}: {err}")
                return {"error": err}
            
            if auto_save:
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
                    system_logger.info("CRAWLER", f"Successfully crawled and saved course: {title}")
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
def crawl_topcv_jobs_task(limit: int = 20, force: bool = False, extract_skills: bool = True):
    """
    Background Task to crawl latest Tech jobs from TopCV.
    Runs every 30 mins via Celery Beat.
    
    Args:
        limit: Number of jobs to crawl
        force: Bypass system settings check
        extract_skills: Whether to trigger async skill extraction for new jobs
    """
    logger.info(f"🚀 [TOPCV CRAWLER] Starting crawl cycle (limit={limit}, force={force}, extract_skills={extract_skills})...")
    system_logger.info("CRAWLER", f"Starting TopCV crawl cycle (limit={limit})")
    
    db = SessionLocal()
    
    # Get proxy list from SystemSetting (global PROXY_LIST for all crawlers)
    proxy_list = []
    try:
        proxy_setting = db.query(SystemSetting).filter(SystemSetting.key == "PROXY_LIST").first()
        if proxy_setting and proxy_setting.value:
            # Parse proxy list - support both comma-separated and newline-separated
            proxy_str = str(proxy_setting.value).strip()
            if proxy_str:
                # Split by both comma and newline, then filter empty strings
                proxy_list = [p.strip() for p in re.split(r'[,\n\r]+', proxy_str) if p.strip()]
                logger.info(f"[TOPCV CRAWLER] Loaded {len(proxy_list)} proxies from global PROXY_LIST")
        else:
            logger.info(f"[TOPCV CRAWLER] No proxy list configured in settings")
    except Exception as e:
        logger.warning(f"[TOPCV CRAWLER] Failed to load proxy list from settings: {e}")
    
    # Initialize scraper with proxy list
    scraper = TopCVScraper(proxy_list=proxy_list)
    
    urls = scraper.get_latest_job_urls(limit=limit)
    
    if not urls:
        logger.warning("⚠️ [TOPCV CRAWLER] No job URLs found. Possible block or empty result.")
        db.close()
        return {"status": "no_urls_found"}

    # Check if crawling is enabled in settings (bypass if force=True)
    if not force:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "TOPCV_CRAWL_ENABLED").first()
        if setting and not setting.value:
            logger.info("⏭️ [TOPCV CRAWLER] Crawl cycle skipped (disabled in system settings).")
            db.close()
            return {"status": "disabled_by_settings"}

    new_jobs_count = 0
    new_job_ids = []  # Track new job IDs for skill extraction
    
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
            
            # Normalize location to standard cities (HN, HCM, DN, Other)
            location_raw = data.get('location_raw', '')
            location_normalized = normalize_location(location_raw)
            data['location_normalized'] = location_normalized
            logger.info(f"[TOPCV CRAWLER] Location normalized: '{location_raw}' → '{location_normalized}'")
            
            # Save job
            job = Job(**data)
            
            db.add(job)
            db.flush()  # Get job.id before commit
            
            new_jobs_count += 1
            new_job_ids.append(str(job.id))  # Track for skill extraction
            logger.info(f"✨ [TOPCV CRAWLER] Added new job: {data['title_raw']} ({source_id})")
            system_logger.info("CRAWLER", f"Added new job: {data['title_raw']} ({source_id})")
            
            # Sleep a bit between scrapes to be polite
            time.sleep(1)
            
        db.commit()
        logger.info(f"✅ [TOPCV CRAWLER] Cycle complete. Added {new_jobs_count} new jobs.")
        system_logger.info("CRAWLER", f"TopCV crawl cycle complete. Added {new_jobs_count} new jobs.")
        
        # Trigger async skill extraction for new jobs
        if extract_skills and new_job_ids:
            logger.info(f"[TOPCV CRAWLER] Triggering skill extraction for {len(new_job_ids)} jobs...")
            for job_id in new_job_ids:
                try:
                    celery_app.send_task(
                        "worker.tasks.crawler_tasks.extract_job_skills_task",
                        args=[job_id]
                    )
                except Exception as e:
                    logger.error(f"[TOPCV CRAWLER] Failed to trigger skill extraction for {job_id}: {e}")
            logger.info(f"[TOPCV CRAWLER] ✓ Skill extraction tasks queued")
        
        return {"status": "success", "new_jobs": new_jobs_count, "skills_queued": len(new_job_ids) if extract_skills else 0}
        
    except Exception as e:
        db.rollback()
        logger.error(f"💥 [TOPCV CRAWLER] Critical error: {e}", exc_info=True)
        system_logger.error("CRAWLER", f"Critical error in TopCV crawler: {str(e)}")
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="worker.tasks.crawler_tasks.extract_job_skills_task")
def extract_job_skills_task(job_id: str):
    """
    Background task to extract skills AND classify job type.
    Non-tech jobs from crawlers will be automatically deactivated.
    """
    logger.info(f"🔍 [SKILL EXTRACT] Starting extraction + classification for job {job_id}")
    
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"❌ [SKILL EXTRACT] Job {job_id} not found")
            return {"error": "job_not_found"}
        
        if not job.requirements:
            logger.warning(f"⚠️ [SKILL EXTRACT] Job {job_id} has no requirements")
            return {"status": "no_requirements"}
        
        # Extract skills + classify job type
        result = extract_and_save_job_skills(
            db=db,
            job=job,
            model_key="ai_model",
            commit=True
        )
        
        if not result:
            logger.warning(f"⚠️ [SKILL EXTRACT] Extraction failed for job {job_id}")
            return {"status": "extraction_failed"}
        
        # Log classification results
        if result["status"] in ["non_tech", "deactivated"]:
            logger.warning(
                f"🚫 [SKILL EXTRACT] Non-tech job: {job.title_raw}\n"
                f"   Domain: {result['primary_domain']}\n"
                f"   Confidence: {result['confidence']:.2f}\n"
                f"   Status: {result['status']}\n"
                f"   Reason: {result['reason']}"
            )
        else:
            logger.info(
                f"✅ [SKILL EXTRACT] Tech job: {job.title_raw}\n"
                f"   Domain: {result['primary_domain']}\n"
                f"   Skills: {result['skill_count']}\n"
                f"   Confidence: {result['confidence']:.2f}"
            )
        
        return result
        
    except Exception as e:
        db.rollback()
        logger.error(f"💥 [SKILL EXTRACT] Error for job {job_id}: {e}", exc_info=True)
        return {"error": str(e), "status": "error"}
    finally:
        db.close()


@celery_app.task(name="worker.tasks.crawler_tasks.crawl_single_job_url_task")
def crawl_single_job_url_task(url: str):
    """
    Background task to crawl a single job URL from TopCV and auto-save to DB.
    Used for batch URL uploads from admin panel.
    
    Args:
        url: TopCV job URL to crawl
        
    Returns:
        dict with status and job info
    """
    logger.info(f"🚀 [SINGLE JOB CRAWLER] Starting crawl for URL: {url}")
    
    if "topcv.vn" not in url:
        logger.error(f"❌ [SINGLE JOB CRAWLER] Invalid URL (not TopCV): {url}")
        return {"status": "error", "error": "Only TopCV URLs are supported", "url": url}
    
    db = SessionLocal()
    
    try:
        # Get proxy list from SystemSetting
        proxy_list = []
        try:
            proxy_setting = db.query(SystemSetting).filter(SystemSetting.key == "PROXY_LIST").first()
            if proxy_setting and proxy_setting.value:
                proxy_str = str(proxy_setting.value).strip()
                if proxy_str:
                    proxy_list = [p.strip() for p in re.split(r'[,\n\r]+', proxy_str) if p.strip()]
        except Exception as e:
            logger.warning(f"[SINGLE JOB CRAWLER] Failed to load proxy list: {e}")
        
        # Check if job already exists
        job_id_match = re.search(r'/(\d+)\.html', url)
        if job_id_match:
            source_id = f"TOPCV_{job_id_match.group(1)}"
            existing = db.query(Job).filter(Job.source_id == source_id).first()
            if existing:
                logger.info(f"⏭️ [SINGLE JOB CRAWLER] Job already exists: {source_id}")
                return {
                    "status": "skipped",
                    "reason": "already_exists",
                    "url": url,
                    "source_id": source_id
                }
        
        # Initialize scraper and crawl
        scraper = TopCVScraper(proxy_list=proxy_list)
        data = scraper.scrape_job_details(url, max_retries=3)
        
        if not data:
            logger.error(f"❌ [SINGLE JOB CRAWLER] Scraper returned None for URL: {url}")
            return {"status": "error", "error": "Failed to scrape job data", "url": url}
        
        # Normalize location
        location_raw = data.get('location_raw', '')
        location_normalized = normalize_location(location_raw)
        data['location_normalized'] = location_normalized
        
        # Save to database
        job = Job(**data)
        
        db.add(job)
        db.flush()
        
        job_id = str(job.id)
        title = data.get('title_raw', 'Unknown')
        
        db.commit()
        
        logger.info(f"✨ [SINGLE JOB CRAWLER] Successfully saved job: {title} (ID: {job_id})")
        system_logger.info("CRAWLER", f"Single URL crawl success: {title}")
        
        # Extract skills synchronously (wait before moving to next URL)
        try:
            logger.info(f"[SINGLE JOB CRAWLER] Starting skill extraction for {job_id}...")
            
            if job.requirements:
                result = extract_and_save_job_skills(
                    db=db,
                    job=job,
                    model_key="ai_model",
                    commit=True
                )
                
                # extract_and_save_job_skills returns a dict with status info
                if result and result.get("status") == "success":
                    skills_count = result.get("skill_count", 0)
                    logger.info(f"✅ [SINGLE JOB CRAWLER] Extracted {skills_count} skills for {job_id}")
                elif result and result.get("status") == "non_tech":
                    logger.info(f"⚠️ [SINGLE JOB CRAWLER] Non-tech job {job_id}, skipped")
                else:
                    logger.warning(f"⚠️ [SINGLE JOB CRAWLER] No skills extracted for {job_id}")
            else:
                logger.warning(f"⚠️ [SINGLE JOB CRAWLER] Job {job_id} has no requirements, skipping skill extraction")
                
        except Exception as e:
            logger.error(f"[SINGLE JOB CRAWLER] Skill extraction failed for {job_id}: {e}")
            # Don't fail the whole task if skill extraction fails
        
        return {
            "status": "success",
            "url": url,
            "job_id": job_id,
            "title": title,
            "source_id": data.get('source_id')
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"💥 [SINGLE JOB CRAWLER] Error crawling {url}: {e}", exc_info=True)
        return {"status": "error", "error": str(e), "url": url}
    finally:
        db.close()


@celery_app.task(name="worker.tasks.crawler_tasks.batch_extract_skills_task")
def batch_extract_skills_task(limit: int = 100, skip_existing: bool = True):
    """
    Background task to extract skills for multiple jobs in batch.
    Useful for processing existing jobs that don't have skills extracted yet.
    
    Args:
        limit: Maximum number of jobs to process
        skip_existing: Skip jobs that already have skills extracted
    """
    logger.info(f"🔍 [BATCH SKILL EXTRACT] Starting batch extraction (limit={limit}, skip_existing={skip_existing})")
    
    db = SessionLocal()
    try:
        # Query jobs that need skill extraction
        query = db.query(Job).filter(
            Job.requirements.isnot(None),
            Job.requirements != ""
        )
        
        if skip_existing:
            # Skip jobs that already have extracted_requirements_json
            query = query.filter(Job.extracted_requirements_json.is_(None))
        
        jobs = query.limit(limit).all()
        
        logger.info(f"[BATCH SKILL EXTRACT] Found {len(jobs)} jobs to process")
        
        processed = 0
        failed = 0
        total_skills = 0
        
        for job in jobs:
            try:
                logger.info(f"[BATCH SKILL EXTRACT] Processing job {job.id}: {job.title_raw}")
                
                result = extract_and_save_job_skills(
                    db=db,
                    job=job,
                    model_key="ai_model",
                    commit=True
                )
                
                # extract_and_save_job_skills now returns a dict, not int
                if result and result.get("status") == "success":
                    skills_count = result.get("skill_count", 0)
                    processed += 1
                    total_skills += skills_count
                    logger.info(f"[BATCH SKILL EXTRACT] ✓ Job {job.id}: {skills_count} skills")
                elif result and result.get("status") == "non_tech":
                    logger.info(f"[BATCH SKILL EXTRACT] ⚠️ Job {job.id}: Non-tech job, skipped")
                else:
                    logger.warning(f"[BATCH SKILL EXTRACT] ⚠️ Job {job.id}: No skills extracted")
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                failed += 1
                logger.error(f"[BATCH SKILL EXTRACT] ❌ Job {job.id} failed: {e}")
                continue
        
        logger.info(f"✅ [BATCH SKILL EXTRACT] Complete: {processed} processed, {failed} failed, {total_skills} total skills")
        return {
            "status": "success",
            "processed": processed,
            "failed": failed,
            "total_skills": total_skills
        }
        
    except Exception as e:
        logger.error(f"💥 [BATCH SKILL EXTRACT] Critical error: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()
