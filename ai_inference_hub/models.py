import torch
import gc
import logging
from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer, AutoProcessor
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
        
        self.chandra_path = os.getenv("CHANDRA_MODEL_PATH", "microsoft/Florence-2-large") # Chandra-1 style
        self.bert_model_name = os.getenv("BERTSCORE_MODEL_NAME", "microsoft/deberta-base-mnli")
        
    def load_chandra(self):
        """Load Chandra VLM optimized for 8GB RAM."""
        if self.chandra_model is None:
            logger.info(f"Loading Chandra from {self.chandra_path}...")
            # Using 4-bit quantization if possible, else low memory usage
            try:
                self.chandra_model = AutoModelForCausalLM.from_pretrained(
                    self.chandra_path,
                    trust_remote_code=True,
                    torch_dtype=torch.float32, # CPU usually likes float32 or bfloat16
                    device_map="cpu"
                ).eval()
                self.chandra_processor = AutoProcessor.from_pretrained(self.chandra_path, trust_remote_code=True)
                logger.info("Chandra loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Chandra: {e}")
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
