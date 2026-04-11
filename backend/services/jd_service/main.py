from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.models import Job
from shared.redis_client import auth_cache # Dùng để check auth nếu cần, nhưng gateway đã làm rồi
from worker.celery_app import celery_app
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI(title="JD Service")

class JobCreate(BaseModel):
    title_raw: str
    raw_text: str
    source_url: Optional[str] = None
    source_label: Optional[str] = "manual"

class JobResponse(BaseModel):
    id: uuid.UUID
    title_raw: str
    status: str
    
    class Config:
        from_attributes = True

@app.post("/jd/import/text", response_model=JobResponse)
def import_jd_text(job_in: JobCreate, request: Request, db: Session = Depends(get_db)):
    # Lấy user_id từ header do Gateway inject
    user_id = request.headers.get("X-User-ID")
    
    # Tạo source_id giả định cho manual import
    source_id = f"manual_{uuid.uuid4()}"
    
    new_job = Job(
        source_id=source_id,
        title_raw=job_in.title_raw,
        raw_text=job_in.raw_text,
        source_url=job_in.source_url,
        source_label=job_in.source_label,
        status="processing"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Gửi task vào Celery để AI xử lý (Phase 4 sẽ implement task thực sự)
    celery_app.send_task("worker.tasks.parse_jd_task.parse_jd", args=[str(new_job.id)])
    
    return new_job

@app.get("/jd/list", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).filter(Job.status == "active").all()

@app.get("/jd/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
