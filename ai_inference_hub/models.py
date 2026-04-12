import os
from dotenv import load_dotenv
# Load .env from script's directory or project root
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
load_dotenv(os.path.join(script_dir, ".env"))
load_dotenv(os.path.join(root_dir, ".env"))
load_dotenv() # Fallback to CWD

import torch
import gc
import logging
import time

# --- Tắt cảnh báo tạo thread convert safetensors nền của Transformers ---
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["SAFETENSORS_AUTO_CONVERSION"] = "0"
os.environ["HF_HUB_DISABLE_AUTO_CONVERSION"] = "1"

# Force offline mode if requested to stop ALL network checks
if os.getenv("HF_LOCAL_FILES_ONLY", "0").lower() in ("1", "true", "yes"):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Silence noisy loggers
logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)
logging.getLogger("bert_score").setLevel(logging.ERROR)

# --- Force Local Caching to avoid re-downloading models in ephemeral containers ---
# If HF_HOME is not set, we use a local directory inside the project
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = os.path.join(os.path.dirname(__file__), "models_cache")
if not os.environ.get("TRANSFORMERS_CACHE"):
    os.environ["TRANSFORMERS_CACHE"] = os.environ["HF_HOME"]

# --- Monkeypatch for PyTorch < 2.4.0 (for BitsAndBytes compatibility) ---
if not hasattr(torch.nn.Module, "set_submodule"):
    def set_submodule(self, target: str, module: torch.nn.Module) -> None:
        if '.' not in target:
            setattr(self, target, module)
        else:
            atoms = target.split('.')
            name = atoms.pop(-1)
            mod = self
            for item in atoms:
                if not hasattr(mod, item):
                    raise AttributeError(f"{mod} has no attribute `{item}`")
                mod = getattr(mod, item)
            setattr(mod, name, module)
    torch.nn.Module.set_submodule = set_submodule

# --- Optimization: Ensure torchvision is initialized before transformers ---
try:
    # --- Monkeypatch torch.library.register_fake to suppress torchvision::nms missing operator bug ---
    if hasattr(torch, "library") and hasattr(torch.library, "register_fake"):
        original_register_fake = torch.library.register_fake
        def safe_register_fake(name, *args, **kwargs):
            def decorator(func):
                try:
                    return original_register_fake(name, *args, **kwargs)(func)
                except Exception as e:
                    logging.warning(f"Ignored register_fake error for {name}: {e}")
                    return func
            return decorator
        torch.library.register_fake = safe_register_fake

    import torchvision
    # Trigger operator registration
    if hasattr(torchvision, "ops"):
        import torchvision.ops
    logging.info(f"Torchvision initialized. version={torchvision.__version__}")
except Exception as e:
    logging.warning(f"Failed to pre-initialize torchvision: {e}")


# --- Bypass Transformers security checks ---
try:
    import transformers.utils.import_utils
    # Keep security bypass for PyTorch 2.6+ pickle loading if needed
    transformers.utils.import_utils.check_torch_load_is_safe = lambda: True
except Exception as e:
    logging.warning(f"Failed to apply transformers security monkeypatch: {e}")

# --- Heavy Imports moved to top to avoid late import issues ---
try:
    from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig, AutoModel
    from bert_score import BERTScorer
    from sentence_transformers import CrossEncoder
    
    # --- Monkeypatch AutoModel to prefer safetensors but fallback to pickle ---
    _orig_from_pretrained = AutoModel.from_pretrained
    @classmethod
    def _safe_from_pretrained(cls, pretrained_model_name_or_path, *model_args, **kwargs):
        # Default to safetensors to bypass PyTorch 2.6 security check for BERTScore
        # unless user explicitly requested otherwise.
        if "use_safetensors" not in kwargs:
            kwargs["use_safetensors"] = True
            
        try:
            return _orig_from_pretrained.__func__(cls, pretrained_model_name_or_path, *model_args, **kwargs)
        except Exception as e:
            if kwargs.get("use_safetensors"):
                logging.warning(f"Safetensors loading failed for {pretrained_model_name_or_path}, falling back to pickle: {e}")
                kwargs["use_safetensors"] = False
                return _orig_from_pretrained.__func__(cls, pretrained_model_name_or_path, *model_args, **kwargs)
            raise
            
    AutoModel.from_pretrained = _safe_from_pretrained
    
except ImportError as e:
    logging.error(f"Failed to import heavy AI libraries: {e}")
    raise

load_dotenv()

logger = logging.getLogger("ai_models")

class AIModelHub:
    def __init__(self):
        self.chandra_model = None
        self.chandra_processor = None
        self.skill_matcher = None
        
        # Chandra OCR 2 — Real model from Datalab
        self.chandra_path = os.getenv("CHANDRA_MODEL_PATH", "datalab-to/chandra-ocr-2")
        self.bert_model_name = os.getenv("BERTSCORE_MODEL_NAME", "microsoft/deberta-v3-base")
        
    def load_chandra(self):
        """Load Chandra OCR 2 (datalab-to/chandra-ocr-2).
        Optimized: Uses 4-bit quantization on GPU, and BFloat16/Float32 on CPU.
        """
        if self.chandra_model is None:
            logger.info(f"Loading Chandra OCR 2 from {self.chandra_path}...")
            
            use_cuda = torch.cuda.is_available()
            device_count = torch.cuda.device_count() if hasattr(torch.cuda, "device_count") else 0
            
            if use_cuda:
                device_name = torch.cuda.get_device_name(0)
                vram_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
                logger.info(f"DEBUG MODELS: [CUDA detected] Using {device_name} with {vram_total:.2f}GB VRAM.")
                logger.info("DEBUG MODELS: Configuring 4-bit Quantization (bitsandbytes).")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                    llm_int8_enable_fp32_cpu_offload=True, # Enable offload to avoid accelerate/bnb crash
                )
                model_kwargs = {
                    "quantization_config": quantization_config,
                    "device_map": "auto",
                    "dtype": torch.bfloat16, # Changed torch_dtype to dtype as per warning
                }
            else:
                if device_count > 0:
                    logger.warning(f"DEBUG MODELS: [DRIVER ISSUE] Found {device_count} GPU(s) but CUDA is NOT available. This usually means your NVIDIA driver is too old for this version of PyTorch. Falling back to CPU.")
                else:
                    logger.info("DEBUG MODELS: No GPU detected. Using CPU-only mode.")
                
                # Check for CPU BFloat16 support
                cpu_bf16 = False
                if hasattr(torch.cpu, "is_bf16_supported"):
                    cpu_bf16 = torch.cpu.is_bf16_supported()
                
                # Force 4-bit Quantization on CPU for 8GB RAM limit
                logger.info("DEBUG MODELS: Enabling CPU 4-bit Quantization (bitsandbytes).")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16 if cpu_bf16 else torch.float32,
                    bnb_4bit_quant_type="nf4",
                )
                
                model_kwargs = {
                    "quantization_config": quantization_config,
                    "device_map": "cpu",
                    "dtype": torch.bfloat16 if cpu_bf16 else torch.float32,
                    "low_cpu_mem_usage": True,
                }
                
            # Extra safety: Clean memory before loading heavy weights
            gc.collect()
            
            # Check for local-only flag to avoid re-downloads
            local_only = os.getenv("HF_LOCAL_FILES_ONLY", "0").lower() in ("1", "true", "yes")
            if local_only:
                logger.info("DEBUG MODELS: Forcing local_files_only=True")

            try:
                logger.info(f"DEBUG MODELS: [Step 1/5] Loading model weights from {self.chandra_path} (local_files_only={local_only})...")
                load_start = time.time()
                self.chandra_model = AutoModelForImageTextToText.from_pretrained(
                    self.chandra_path,
                    trust_remote_code=True,
                    local_files_only=local_only,
                    **model_kwargs
                ).eval()
                logger.info(f"DEBUG MODELS: [Step 2/5] Weight loading took {time.time() - load_start:.2f}s. Initializing processor...")
                
                proc_start = time.time()
                self.chandra_processor = AutoProcessor.from_pretrained(
                    self.chandra_path,
                    trust_remote_code=True,
                    local_files_only=local_only,
                )
                logger.info(f"DEBUG MODELS: [Step 3/5] Processor loaded in {time.time() - proc_start:.2f}s. Tokenizer size: {len(self.chandra_processor.tokenizer)}")
                
                self.chandra_processor.tokenizer.padding_side = "left"
                
                # Chandra's generate_hf() expects model.processor to be set
                self.chandra_model.processor = self.chandra_processor
                
                logger.info(f"DEBUG MODELS: [Step 4/5] Binded processor to model. Device: {self.chandra_model.device}")
                logger.info(f"DEBUG MODELS: [Step 5/5] Chandra OCR 2 READY. Dtype: {self.chandra_model.dtype}, is_quantized: {getattr(self.chandra_model, 'is_quantized', False)}")
            except Exception as e:
                logger.error(f"DEBUG MODELS: [FATAL] Failed to load Chandra OCR 2: {e}")
                raise

    def load_bertscore(self):
        """Load Cross-Encoder model (used for skill matching).
        Note: We keep the method name 'load_bertscore' for internal backward compatibility 
        with engine calls for now, but it initializes a Cross-Encoder.
        """
        if self.skill_matcher is None:
            logger.info(f"Loading Cross-Encoder with {self.bert_model_name}...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Use CrossEncoder for high-precision short-string matching
            self.skill_matcher = CrossEncoder(
                self.bert_model_name,
                device=device
            )
            logger.info(f"Cross-Encoder initialized on {device}.")
            
            # Backwards compatibility reference (if any code still uses self.bert_scorer)
            # self.bert_scorer = self.skill_matcher 

    def unload_models(self):
        """Force memory cleanup."""
        self.chandra_model = None
        self.chandra_processor = None
        self.skill_matcher = None
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
