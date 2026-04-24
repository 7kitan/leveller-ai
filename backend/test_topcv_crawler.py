#!/usr/bin/env python3
"""
Test script to manually run TopCV crawler with detailed logging.
Usage: python test_topcv_crawler.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.scrapers.topcv import TopCVScraper
from shared.llm_utils import get_embedding
import logging

# Setup console logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 80)
    logger.info("Starting TopCV Crawler Test with Embedding Cost Tracking")
    logger.info("=" * 80)
    
    scraper = TopCVScraper()
    
    # Test 1: Get job URLs
    logger.info("\n[TEST 1] Getting latest job URLs...")
    urls = scraper.get_latest_job_urls(limit=2)  # Reduced to 2 for faster testing
    logger.info(f"[TEST 1] Found {len(urls)} job URLs")
    
    if not urls:
        logger.error("[TEST 1] No URLs found! Check the logs for details.")
        return
    
    for i, url in enumerate(urls, 1):
        logger.info(f"[TEST 1] URL {i}: {url}")
    
    # Test 2: Scrape first job details
    if urls:
        logger.info(f"\n[TEST 2] Scraping first job: {urls[0]}")
        job_data = scraper.scrape_job_details(urls[0])
        
        if job_data:
            logger.info("[TEST 2] ✅ Successfully scraped job!")
            logger.info(f"[TEST 2] Title: {job_data.get('title_raw')}")
            logger.info(f"[TEST 2] Company: {job_data.get('company_name')}")
            logger.info(f"[TEST 2] Location: {job_data.get('location_raw')}")
            logger.info(f"[TEST 2] Salary: {job_data.get('min_salary_vnd')} - {job_data.get('max_salary_vnd')}")
            logger.info(f"[TEST 2] Raw text length: {len(job_data.get('raw_text', ''))}")
            logger.info(f"[TEST 2] Job description length: {len(job_data.get('job_description', ''))}")
            logger.info(f"[TEST 2] Requirements length: {len(job_data.get('requirements', ''))}")
            logger.info(f"[TEST 2] Benefits length: {len(job_data.get('benefits', ''))}")
            
            # Show previews
            if job_data.get('job_description'):
                logger.info(f"\n[TEST 2] Job Description Preview:")
                logger.info(job_data['job_description'][:300] + "...")
            
            if job_data.get('requirements'):
                logger.info(f"\n[TEST 2] Requirements Preview:")
                logger.info(job_data['requirements'][:300] + "...")
            
            if job_data.get('benefits'):
                logger.info(f"\n[TEST 2] Benefits Preview:")
                logger.info(job_data['benefits'][:300] + "...")
            
            # Test 3: Generate embedding with cost tracking
            logger.info(f"\n[TEST 3] Testing embedding generation with cost tracking...")
            title = job_data.get('title_raw', '')
            company = job_data.get('company_name', '')
            location = job_data.get('location_raw', '')
            requirements = job_data.get('requirements', '')
            
            if requirements:
                embedding_ctx = f"Job: {title} at {company}. Location: {location}. Requirements: {requirements}"
            else:
                embedding_ctx = f"Job: {title} at {company}. Location: {location}."
            
            logger.info(f"[TEST 3] Embedding context length: {len(embedding_ctx)} chars")
            logger.info(f"[TEST 3] Generating embedding...")
            
            vector = get_embedding(embedding_ctx, log_cost=True)
            
            if vector:
                logger.info(f"[TEST 3] ✅ Embedding generated successfully!")
                logger.info(f"[TEST 3] Vector dimensions: {len(vector)}")
            else:
                logger.error(f"[TEST 3] ❌ Failed to generate embedding")
        else:
            logger.error("[TEST 2] ❌ Failed to scrape job details!")
    
    logger.info("\n" + "=" * 80)
    logger.info("Test complete! Check logs directory for detailed HTML dumps.")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
