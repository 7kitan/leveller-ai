import torch
import gc
import logging
from bert_score import BERTScorer
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ai_models")

class AIModelHub:
    def __init__(self):
        self.chandra_model = None
        self.chandra_processor = None
        self.bert_scorer = None
        
        # Chandra OCR 2 — Real model from Datalab
        self.chandra_path = os.getenv("CHANDRA_MODEL_PATH", "datalab-to/chandra-ocr-2")
        self.bert_model_name = os.getenv("BERTSCORE_MODEL_NAME", "microsoft/deberta-base-mnli")
        
    def load_chandra(self):
        """Load Chandra OCR 2 (datalab-to/chandra-ocr-2) with 4-bit quantization for 8GB RAM."""
        if self.chandra_model is None:
            logger.info(f"Loading Chandra OCR 2 from {self.chandra_path}...")
            
            from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig
            
            # --- 4-bit Quantization để chạy trên 8GB RAM ---
            # Model 5B params: FP16 ~10GB → 4-bit ~3-4GB
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,  # Double quantization để tiết kiệm thêm RAM
            )
            
            try:
                self.chandra_model = AutoModelForImageTextToText.from_pretrained(
                    self.chandra_path,
                    quantization_config=quantization_config,
                    device_map="auto",  # Auto-map CPU/GPU
                    trust_remote_code=True,
                ).eval()
                
                self.chandra_processor = AutoProcessor.from_pretrained(
                    self.chandra_path,
                    trust_remote_code=True,
                )
                self.chandra_processor.tokenizer.padding_side = "left"
                
                # Chandra's generate_hf() expects model.processor to be set
                self.chandra_model.processor = self.chandra_processor
                
                logger.info("Chandra OCR 2 loaded successfully (4-bit quantized).")
            except Exception as e:
                logger.error(f"Failed to load Chandra OCR 2: {e}")
                raise

    def load_bertscore(self):
        """Load BERTScore model."""
        if self.bert_scorer is None:
            logger.info(f"Loading BERTScore with {self.bert_model_name}...")
            # DeBERTa-base is much lighter than RoBERTa-large for 8GB RAM
            self.bert_scorer = BERTScorer(model_type=self.bert_model_name, device="cpu")
            logger.info("BERTScore initialized.")

    def unload_models(self):
        """Force memory cleanup."""
        self.chandra_model = None
        self.chandra_processor = None
        self.bert_scorer = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Models unloaded and memory cleared.")

    def load_all(self):
        """Load all models at startup to avoid delay during requests."""
        logger.info("Initializing all AI models...")
        self.load_chandra()
        self.load_bertscore()
        logger.info("All AI models loaded successfully.")

# Global instance
hub = AIModelHub()
