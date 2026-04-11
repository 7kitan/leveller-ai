from worker.celery_app import celery_app
import time

@celery_app.task(name="worker.tasks.parse_jd_task.parse_jd")
def parse_jd(job_id: str):
    print(f"Starting to parse JD with ID: {job_id}")
    # Logic thực sự sẽ được triển khai trong Phase 4 bằng LangGraph
    # Hiện tại giả lập xử lý trong 5 giây
    time.sleep(5)
    print(f"Finished parsing JD with ID: {job_id}")
    return {"job_id": job_id, "status": "done"}
