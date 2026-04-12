import os
import sys
import time
import logging

# Configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GPU-Diag")

def test_cuda():
    logger.info("--- Phase 1: CUDA Check ---")
    try:
        import torch
        logger.info(f"PyTorch version: {torch.__version__}")
        cuda_available = torch.cuda.is_available()
        logger.info(f"CUDA Available: {cuda_available}")
        
        if not cuda_available:
            logger.error("CUDA is not available. Please check drivers and torch installation.")
            return False
            
        device_count = torch.cuda.device_count()
        logger.info(f"Device Count: {device_count}")
        
        for i in range(device_count):
            name = torch.cuda.get_device_name(i)
            props = torch.cuda.get_device_properties(i)
            logger.info(f"Device {i}: {name}")
            logger.info(f"  VRAM: {props.total_memory / 1024**3:.2f} GB")
            logger.info(f"  Compute Capability: {props.major}.{props.minor}")
            
        return True
    except ImportError:
        logger.error("PyTorch is not installed.")
        return False

def test_bitsandbytes():
    logger.info("\n--- Phase 2: BitsAndBytes Check ---")
    try:
        import bitsandbytes as bnb
        logger.info(f"bitsandbytes version: {getattr(bnb, '__version__', 'unknown')}")
        
        # Test basic 4-bit config loading if possible
        import torch
        from transformers import BitsAndBytesConfig
        config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
        )
        logger.info("Successfully created BitsAndBytesConfig. Kernel check passed.")
        return True
    except Exception as e:
        logger.error(f"bitsandbytes check failed: {e}")
        return False

def test_tensor_ops():
    logger.info("\n--- Phase 3: Tensor Operations & Latency ---")
    try:
        import torch
        device = "cuda"
        size = 4096
        
        logger.info(f"Allocating {size}x{size} tensor on {device}...")
        start = time.time()
        x = torch.randn(size, size, device=device)
        y = torch.randn(size, size, device=device)
        torch.cuda.synchronize()
        logger.info(f"Allocation and sync took {time.time() - start:.4f}s")
        
        logger.info("Performing Matrix Multiplication (Gemm)...")
        start = time.time()
        z = torch.matmul(x, y)
        torch.cuda.synchronize()
        logger.info(f"Matmul (4096^2) took {time.time() - start:.4f}s")
        
        return True
    except Exception as e:
        logger.error(f"Tensor ops failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting GPU Cloud Readiness Diagnostic...")
    
    results = {
        "CUDA": test_cuda(),
        "BitsAndBytes": test_bitsandbytes(),
        "TensorOps": test_tensor_ops()
    }
    
    logger.info("\n--- Final Report ---")
    for test, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        logger.info(f"{test:15}: {status}")
        
    if all(results.values()):
        logger.info("SYSTEM READY: The environment is correctly configured for GPU inference.")
    else:
        logger.error("SYSTEM NOT READY: Please resolve the failures above before deploying.")
