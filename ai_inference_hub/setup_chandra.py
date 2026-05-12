import os
import sys
import logging
import time
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup_chandra")

def setup_chandra():
    """
    Setup script to pre-download Chandra OCR 2 model weights and verify dependencies.
    """
    logger.info("--- Starting Chandra OCR 2 Setup ---")
    
    # 1. Load Environment
    load_dotenv()
    model_path = os.getenv("CHANDRA_MODEL_PATH", "datalab-to/chandra-ocr-2")
    
    # Ensure cache directory exists
    cache_dir = os.getenv("HF_HOME", os.path.join(os.path.dirname(__file__), "models_cache"))
    os.makedirs(cache_dir, exist_ok=True)
    os.environ["HF_HOME"] = cache_dir
    os.environ["TRANSFORMERS_CACHE"] = cache_dir
    
    logger.info(f"Model Path: {model_path}")
    logger.info(f"Cache Directory: {cache_dir}")

    # 2. Check dependencies
    logger.info("Step 1: Checking Python dependencies...")
    try:
        import torch
        import transformers
        from transformers import AutoProcessor, AutoConfig
        logger.info(f"  - Torch version: {torch.__version__}")
        logger.info(f"  - Transformers version: {transformers.__version__}")
    except ImportError as e:
        logger.error(f"  - Missing core dependency: {e}")
        logger.info("Please run: pip install -r requirements_ai.txt")
        return

    try:
        import chandra
        logger.info("  - chandra-ocr package: Found")
    except ImportError:
        logger.warning("  - chandra-ocr package: NOT found. Attempting to install via pip...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "chandra-ocr"])
        logger.info("  - chandra-ocr package: Installed successfully")

    # 3. Pre-download Model Weights
    logger.info(f"Step 2: Pre-downloading weights for {model_path}...")
    logger.info("This may take several minutes depending on your internet connection (approx 5GB)...")
    
    start_time = time.time()
    try:
        # Download Config first
        logger.info("  - Fetching configuration...")
        config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
        
        # Download Processor
        logger.info("  - Fetching processor...")
        processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        
        # Download Model Weights (using CPU to avoid VRAM issues during setup)
        logger.info("  - Fetching model weights (this is the big one)...")
        # We use from_pretrained with low_cpu_mem_usage and device_map="cpu" to just cache it
        from transformers import AutoModelForImageTextToText
        AutoModelForImageTextToText.from_pretrained(
            model_path,
            trust_remote_code=True,
            device_map="cpu",
            low_cpu_mem_usage=True,
            torch_dtype="auto" # Use auto to match safetensors
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Step 2: Completed in {elapsed:.2f}s")
        
    except Exception as e:
        logger.error(f"Step 2: Failed to download weights: {e}")
        logger.info("Tip: Check your internet connection and HuggingFace access.")
        return

    # 4. Final Validation
    logger.info("Step 3: Final validation...")
    try:
        from chandra.model.hf import generate_hf
        logger.info("  - Import 'chandra.model.hf': SUCCESS")
    except Exception as e:
        logger.error(f"  - Import 'chandra.model.hf': FAILED ({e})")

    logger.info("--- Chandra OCR 2 Setup COMPLETE ---")
    logger.info("You can now run the AI Inference Hub.")

if __name__ == "__main__":
    setup_chandra()
