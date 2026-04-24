#!/usr/bin/env python3
"""
Test employment type extraction from TopCV scraper.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.scrapers.topcv import TopCVScraper
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 80)
    logger.info("Testing Employment Type Extraction")
    logger.info("=" * 80)
    
    scraper = TopCVScraper()
    
    # Test with one URL
    test_url = "https://www.topcv.vn/viec-lam/truong-nhom-phan-tich-nghiep-vu-ba-lead/1830557.html"
    
    logger.info(f"\nTesting URL: {test_url}")
    job_data = scraper.scrape_job_details(test_url)
    
    if job_data:
        logger.info("\n✅ Successfully scraped job!")
        logger.info(f"Title: {job_data.get('title_raw')}")
        logger.info(f"Company: {job_data.get('company_name')}")
        logger.info(f"Employment Type: {job_data.get('employment_type')}")
        logger.info(f"Location: {job_data.get('location_raw')}")
        logger.info(f"Location Normalized: {job_data.get('location_normalized')}")
        logger.info(f"Location District: {job_data.get('location_district')}")
        
        logger.info(f"\nStructured Fields:")
        logger.info(f"  - Job Description: {len(job_data.get('job_description', ''))} chars")
        logger.info(f"  - Requirements: {len(job_data.get('requirements', ''))} chars")
        logger.info(f"  - Benefits: {len(job_data.get('benefits', ''))} chars")
        
        if job_data.get('employment_type'):
            logger.info(f"\n✅ Employment type extracted: '{job_data.get('employment_type')}'")
        else:
            logger.warning(f"\n⚠️ Employment type not found")
    else:
        logger.error("\n❌ Failed to scrape job")
    
    logger.info("\n" + "=" * 80)
    logger.info("Test complete!")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
