"""
Verification Script: Celery Beat Periodic Tasks

This script verifies that all periodic tasks are properly configured and running.

Run with: python -m scripts.verify_celery_beat
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from worker.celery_app import celery_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_beat_schedule():
    """Verify all periodic tasks are configured."""
    logger.info("=" * 80)
    logger.info("CELERY BEAT PERIODIC TASKS VERIFICATION")
    logger.info("=" * 80)
    
    beat_schedule = celery_app.conf.beat_schedule
    
    if not beat_schedule:
        logger.error("❌ No periodic tasks configured!")
        return False
    
    logger.info(f"\n✓ Found {len(beat_schedule)} periodic tasks:\n")
    
    for task_name, config in beat_schedule.items():
        logger.info(f"📅 {task_name}")
        logger.info(f"   Task: {config['task']}")
        
        if 'schedule' in config:
            schedule = config['schedule']
            if isinstance(schedule, (int, float)):
                logger.info(f"   Schedule: Every {schedule} seconds ({schedule/60:.1f} minutes)")
            else:
                logger.info(f"   Schedule: {schedule}")
        
        if 'args' in config:
            logger.info(f"   Args: {config['args']}")
        
        logger.info("")
    
    return True

def verify_task_routes():
    """Verify task routing configuration."""
    logger.info("=" * 80)
    logger.info("CELERY TASK ROUTING VERIFICATION")
    logger.info("=" * 80)
    
    task_routes = celery_app.conf.task_routes
    
    if not task_routes:
        logger.warning("⚠ No task routes configured!")
        return False
    
    logger.info(f"\n✓ Found {len(task_routes)} routing rules:\n")
    
    for pattern, config in task_routes.items():
        logger.info(f"🔀 {pattern}")
        logger.info(f"   → Queue: {config.get('queue', 'default')}")
        logger.info("")
    
    return True

def verify_workers_needed():
    """List all workers needed based on queues."""
    logger.info("=" * 80)
    logger.info("REQUIRED WORKERS")
    logger.info("=" * 80)
    
    queues = set()
    for pattern, config in celery_app.conf.task_routes.items():
        queue = config.get('queue', 'default')
        queues.add(queue)
    
    logger.info(f"\n✓ Need workers for {len(queues)} queues:\n")
    
    worker_configs = {
        'analysis': {
            'container': 'advisor_worker_analysis',
            'command': 'celery -A worker.celery_app worker -Q analysis',
            'concurrency': '${WORKER_ANALYSIS_CONCURRENCY:-1}'
        },
        'cv_parsing': {
            'container': 'advisor_worker_parsing',
            'command': 'celery -A worker.celery_app worker -Q cv_parsing',
            'concurrency': '${WORKER_PARSING_CONCURRENCY:-2}'
        },
        'market_stats': {
            'container': 'advisor_worker_crawler',
            'command': 'celery -A worker.celery_app worker -Q market_stats',
            'concurrency': '${WORKER_CRAWLER_CONCURRENCY:-1}'
        },
        'email': {
            'container': 'advisor_worker_email',
            'command': 'celery -A worker.celery_app worker -Q email',
            'concurrency': '${WORKER_EMAIL_CONCURRENCY:-2}'
        },
        'default': {
            'container': 'advisor_worker_default',
            'command': 'celery -A worker.celery_app worker',
            'concurrency': '${WORKER_DEFAULT_CONCURRENCY:-1}'
        }
    }
    
    for queue in sorted(queues):
        config = worker_configs.get(queue, {})
        logger.info(f"📦 Queue: {queue}")
        logger.info(f"   Container: {config.get('container', 'N/A')}")
        logger.info(f"   Command: {config.get('command', 'N/A')}")
        logger.info(f"   Concurrency: {config.get('concurrency', 'N/A')}")
        logger.info("")
    
    logger.info("🕐 Scheduler:")
    logger.info("   Container: advisor_celery_beat")
    logger.info("   Command: celery -A worker.celery_app beat")
    logger.info("")
    
    return True

def check_docker_compose():
    """Check if docker-compose.yml has all required workers."""
    logger.info("=" * 80)
    logger.info("DOCKER-COMPOSE.YML VERIFICATION")
    logger.info("=" * 80)
    
    compose_file = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
    
    if not os.path.exists(compose_file):
        logger.error(f"❌ docker-compose.yml not found at {compose_file}")
        return False
    
    with open(compose_file, 'r') as f:
        content = f.read()
    
    required_containers = [
        'advisor_worker_analysis',
        'advisor_worker_parsing',
        'advisor_worker_crawler',
        'advisor_worker_email',
        'advisor_worker_default',
        'advisor_celery_beat'
    ]
    
    logger.info("\nChecking for required containers:\n")
    
    all_found = True
    for container in required_containers:
        if container in content:
            logger.info(f"✓ {container}")
        else:
            logger.error(f"❌ {container} - MISSING!")
            all_found = False
    
    logger.info("")
    
    if all_found:
        logger.info("✓ All required containers are present in docker-compose.yml")
    else:
        logger.error("❌ Some containers are missing from docker-compose.yml")
    
    return all_found

def main():
    """Run all verifications."""
    logger.info("\n")
    
    results = []
    
    results.append(("Beat Schedule", verify_beat_schedule()))
    results.append(("Task Routes", verify_task_routes()))
    results.append(("Workers Config", verify_workers_needed()))
    results.append(("Docker Compose", check_docker_compose()))
    
    logger.info("=" * 80)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    
    for name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {name}")
    
    logger.info("")
    
    if all(r[1] for r in results):
        logger.info("✓ All verifications passed!")
        logger.info("\nNext steps:")
        logger.info("1. Restart docker-compose to apply changes:")
        logger.info("   docker-compose down && docker-compose up -d")
        logger.info("2. Check celery-beat logs:")
        logger.info("   docker logs -f advisor_celery_beat")
        logger.info("3. Verify periodic tasks are scheduled:")
        logger.info("   docker exec advisor_celery_beat celery -A worker.celery_app inspect scheduled")
        return 0
    else:
        logger.error("❌ Some verifications failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
