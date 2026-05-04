import contextvars
import time
import logging
import functools
from typing import Any, Dict, Optional, List

logger = logging.getLogger("benchmark_extension")

# Context variable to track if the current execution is part of a benchmark
is_benchmark_active = contextvars.ContextVar("is_benchmark_active", default=False)
# Context variable to store captured data for the current benchmark run
# Structure: {"calls": [{"prompt": "...", "response": "...", "latency": 123, ...}]}
benchmark_data = contextvars.ContextVar("benchmark_data", default=None)

def benchmark_interceptor(func):
    """
    Decorator to intercept LLM calls and record metadata if benchmark is active.
    This is designed to be wrapped around ai_service.generate_completion.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 1. Check if benchmarking is globally enabled and active for this request
        if not is_benchmark_active.get():
            return func(*args, **kwargs)
        
        # 2. Extract metadata from call
        call_name = kwargs.get("call_name") or "unknown"
        model_key = kwargs.get("model_key") or "ai_model"
        prompt = kwargs.get("prompt") or (args[0] if len(args) > 0 else "")
        
        t0 = time.monotonic()
        try:
            # 3. Execute the actual LLM call
            result = func(*args, **kwargs)
            
            latency = int((time.monotonic() - t0) * 1000)
            
            # 4. Capture data if benchmark_data context is initialized
            data = benchmark_data.get()
            if data is not None:
                if "calls" not in data:
                    data["calls"] = []
                
                data["calls"].append({
                    "call_name": call_name,
                    "model_key": model_key,
                    "prompt": prompt,
                    "response": result,
                    "latency_ms": latency,
                    "timestamp": time.time()
                })
                logger.debug(f"[BENCHMARK] Intercepted call '{call_name}' | latency={latency}ms")
            
            return result
        except Exception as e:
            logger.error(f"[BENCHMARK] Error in intercepted call '{call_name}': {e}")
            raise
            
    return wrapper
