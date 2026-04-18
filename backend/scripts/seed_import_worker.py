import json
import os
import sys
import uuid
import logging

# Thêm path của folder backend vào biến môi trường để import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from worker.celery_app import celery_app
from shared.database import SessionLocal
from shared.models import Course

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("seed_import_worker")

def load_urls_from_json(json_path: str):
    """Trích xuất URL từ file Coursera300.json."""
    if not os.path.exists(json_path):
        logger.error(f"Lỗi: Không tìm thấy file {json_path}")
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        courses = json.load(f)
    links = []
    for c in courses:
        lnk = c.get("link")
        if lnk and "coursera.org" in lnk and lnk not in links:
            links.append(lnk)
    return links

def load_urls_from_txt(txt_path: str):
    """Đọc URL từ file text (mỗi dòng 1 link)."""
    if not os.path.exists(txt_path):
        logger.error(f"Lỗi: Không tìm thấy file {txt_path}")
        return []
    with open(txt_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and "coursera.org" in line]

def seed_courses(source_path: str, force: bool = False, dry_run: bool = False):
    """
    Đẩy URL từ file (TXT hoặc JSON) vào Celery Worker.
    """
    if source_path.endswith('.json'):
        urls = load_urls_from_json(source_path)
    else:
        urls = load_urls_from_txt(source_path)

    if not urls:
        logger.warning(f"⚠️ Không tìm thấy URL nào để xử lý từ {source_path}")
        return

    logger.info(f"🚀 Bắt đầu đẩy {len(urls)} URL vào Celery Worker (force={force}, dry_run={dry_run})...\n")
    
    db = SessionLocal()
    success_count = 0
    skipped_count = 0
    fail_count = 0
    
    try:
        for i, url in enumerate(urls):
            # Kiểm tra duplication (Deduplication) trước khi đẩy task
            if not force:
                exists = db.query(Course.id).filter(Course.url == url).first()
                if exists:
                    skipped_count += 1
                    continue
            
            if dry_run:
                logger.info(f"  [DRY] Would push: {url}")
                success_count += 1
                continue

            try:
                # Đẩy Task vào Queue với auto_save=True
                celery_app.send_task(
                    "worker.tasks.crawler_tasks.crawl_course_task",
                    args=[url],
                    kwargs={"auto_save": True}
                )
                success_count += 1
                if (i + 1) % 50 == 0:
                    logger.info(f"  ... đã đẩy {i+1}/{len(urls)} URLs")
                    
            except Exception as e:
                logger.error(f"❌ Lỗi khi gửi task cho {url}: {e}")
                fail_count += 1
    finally:
        db.close()

    logger.info(f"\n==================================================")
    if dry_run:
        logger.info(f"🧪 [DRY RUN] Đã xử lý {len(urls)} URLs. Sẽ đẩy: {success_count}. Bỏ qua: {skipped_count}")
    else:
        logger.info(f"✅ ĐÃ ĐẨY HẾT VÀO HÀNG ĐỢI! Thành công: {success_count}, Bỏ qua: {skipped_count}, Lỗi: {fail_count}")
        logger.info(f"⚠️  Chú ý: Quá trình cào và insert DB sẽ chạy ngầm bởi Celery Worker.")
    logger.info(f"==================================================\n")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed Coursera courses via Background Worker")
    parser.add_argument("--file", type=str, help="Path tới file nguồn (.txt hoặc .json)")
    parser.add_argument("--force", action="store_true", help="Đẩy task kể cả khi khóa học đã tồn tại trong DB")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ hiển thị URL, không gửi task thực tế")
    
    args = parser.parse_args()
    
    base_dir = os.path.dirname(__file__)
    # Ưu tiên đọc từ coursera_links.txt theo yêu cầu của user
    default_path = os.path.abspath(os.path.join(base_dir, '..', '..', 'dataset', 'coursera_links.txt'))
    source_path = args.file or default_path
    
    seed_courses(source_path, force=args.force, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
