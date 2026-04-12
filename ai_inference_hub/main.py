from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from contextlib import asynccontextmanager
import asyncio
import logging
from auth import get_api_key
from worker import worker
from engine import process_ocr_task, calculate_bertscore_task
from models import hub

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_inference_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load all AI models once during startup
    hub.load_all()
    
    # Start the background worker
    processors = {
        "ocr": process_ocr_task,
        "bertscore": calculate_bertscore_task
    }
    worker_task = asyncio.create_task(worker.start(processors))
    logger.info("Lifespan: Worker task created.")
    yield
    # Cleanup logic (if needed)
    worker.is_running = False
    await worker_task
    hub.unload_models()
    logger.info("Lifespan: Cleanup complete.")

app = FastAPI(
    title="AI Inference Hub (Chandra OCR 2 & BERTScore)",
    description="Serial Queue AI Inference with datalab-to/chandra-ocr-2 for low-resource environments.",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "queue_size": worker.queue.qsize(),
        "ocr_engine": hub.chandra_path,
        "ocr_loaded": hub.chandra_model is not None,
        "bertscore_loaded": hub.bert_scorer is not None,
    }

@app.post("/tasks/ocr", dependencies=[Depends(get_api_key)])
async def create_ocr_task(payload: dict):
    task_id = await worker.add_task("ocr", payload)
    return {"task_id": task_id, "status": "pending"}

@app.post("/tasks/bertscore", dependencies=[Depends(get_api_key)])
async def create_bertscore_task(payload: dict):
    task_id = await worker.add_task("bertscore", payload)
    return {"task_id": task_id, "status": "pending"}

@app.get("/tasks/{task_id}", dependencies=[Depends(get_api_key)])
async def get_task_result(task_id: str):
    status = worker.get_task_status(task_id)
    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Task not found")
    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
