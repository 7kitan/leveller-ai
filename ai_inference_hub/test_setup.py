import os
import sys
import torch
import logging
from dotenv import load_dotenv

# Set logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_setup")

def test_py_version():
    logger.info(f"Python Version: {sys.version}")
    assert sys.version_info >= (3, 10), "Python 3.10+ required"

def test_torch():
    logger.info(f"Torch Version: {torch.__version__}")
    logger.info(f"CUDA Available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        logger.info("Running on CPU mode.")

def test_bitsandbytes():
    try:
        import bitsandbytes
        logger.info(f"BitsAndBytes version: {getattr(bitsandbytes, '__version__', 'unknown')}")
        logger.info("BitsAndBytes imported successfully.")
    except Exception as e:
        logger.error(f"BitsAndBytes import failed: {e}")

def test_poppler():
    poppler_path = os.path.join(os.getcwd(), "bin", "poppler", "Library", "bin")
    # Some versions have it in Library/bin, others in just bin. Let's check both.
    if not os.path.exists(poppler_path):
        poppler_path = os.path.join(os.getcwd(), "bin", "poppler", "bin")
    
    logger.info(f"Checking Poppler in {poppler_path}...")
    
    import shutil
    pdftoppm = shutil.which("pdftoppm", path=poppler_path)
    if pdftoppm:
        logger.info(f"Poppler found: {pdftoppm}")
    else:
        logger.error("Poppler (pdftoppm) NOT found in the expected path.")

def test_transformers():
    try:
        from transformers import AutoConfig
        logger.info("Transformers imported. Fetching config for Chandra...")
        # Just fetch config to test network/HF access (if HF_LOCAL_FILES_ONLY=0)
        config = AutoConfig.from_pretrained("datalab-to/chandra-ocr-2", trust_remote_code=True)
        logger.info(f"Successfully fetched config. Model Type: {config.model_type}")
    except Exception as e:
        logger.error(f"Transformers test failed: {e}")

if __name__ == "__main__":
    load_dotenv()
    test_py_version()
    test_torch()
    test_bitsandbytes()
    test_poppler()
    test_transformers()
