import asyncio
import logging
import uuid
import gc
from typing import Dict, Any, Callable, Awaitable
from datetime import datetime

logger = logging.getLogger("ai_worker")

class AIWorker:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.results: Dict[str, Any] = {}
        self.is_running = False

    async def add_task(self, task_type: str, payload: Any) -> str:
        """Add a task to the queue and return a unique task ID."""
        task_id = str(uuid.uuid4())
        self.results[task_id] = {
            "status": "pending",
            "task_type": task_type,
            "created_at": datetime.now().isoformat()
        }
        await self.queue.put((task_id, task_type, payload))
        logger.info(f"DEBUG WORKER: Task {task_id} ({task_type}) ENQUEUED at {datetime.now().isoformat()}. Queue size: {self.queue.qsize()}")
        return task_id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Retrieve task status and result."""
        return self.results.get(task_id, {"status": "not_found"})

    async def start(self, processors: Dict[str, Callable[[Any], Awaitable[Any]]]):
        """Start the background worker loop."""
        if self.is_running:
            return
        self.is_running = True
        logger.info("AI Background Worker started (Serial Concurrency=1).")
        
        while self.is_running:
            task_id, task_type, payload = await self.queue.get()
            try:
                self.results[task_id]["status"] = "processing"
                logger.info(f"DEBUG WORKER: [Task {task_id}] DEQUEUED and STARTING at {datetime.now().isoformat()}...")
                
                # Execute the specific processor for this task type
                processor = processors.get(task_type)
                if processor:
                    result = await processor(payload)
                    self.results[task_id].update({
                        "status": "completed",
                        "completed_at": datetime.now().isoformat(),
                        "result": result
                    })
                else:
                    self.results[task_id].update({"status": "failed", "error": f"Unknown task type: {task_type}"})

            except Exception as e:
                logger.error(f"Error processing task {task_id}: {e}")
                self.results[task_id].update({"status": "failed", "error": str(e)})
            finally:
                # CRITICAL: Clean up memory after each task to avoid leaks on 8GB VPS
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    
                self.queue.task_done()
                logger.info(f"DEBUG WORKER: [Task {task_id}] FINISHED at {datetime.now().isoformat()}. Memory cleaned.")

# Global Worker Instance
worker = AIWorker()
