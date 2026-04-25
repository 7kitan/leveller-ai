import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logger(name: str, log_file: str = None, level=logging.INFO):
    """
    Cấu hình logger tập trung cho hệ thống.
    
    Quy tắc:
    - Luôn ghi log ra Console.
    - Nếu ENVIRONMENT là 'production' -> KHÔNG ghi log ra file.
    - Nếu ENVIRONMENT là 'dev'/'development' (hoặc không set) -> Ghi log ra file nếu có log_file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Tránh duplicate handlers nếu logger đã được setup
    if logger.hasHandlers():
        return logger

    # 1. Console Handler (Luôn luôn có)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (Chỉ ở môi trường DEV)
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env != "production" and log_file:
        # Tạo thư mục logs nếu chưa có
        log_dir = "logs"
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except Exception:
                # Nếu không tạo được thư mục (vd: permissions), log ra console rồi skip
                logger.warning(f"Could not create log directory '{log_dir}'. Skipping file logging.")
                return logger
                
        log_path = os.path.join(log_dir, log_file)
        
        try:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
            file_handler = RotatingFileHandler(
                log_path, 
                maxBytes=10 * 1024 * 1024, # 10MB
                backupCount=5
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            logger.info(f"File logging initialized at: {log_path}")
        except Exception as e:
            logger.warning(f"Could not initialize file handler for {log_file}: {e}")

    return logger
