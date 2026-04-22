import torch
import numpy as np
from models import hub
import logging
from PIL import Image
import io
import base64
import os
import gc
import time
import asyncio
from pdf2image import convert_from_bytes
from typing import List

logger = logging.getLogger("ai_engine")

# --- Chandra OCR 2 specific imports ---
from chandra.model.hf import generate_hf
from chandra.model.schema import BatchInputItem
from chandra.output import parse_markdown

def ensure_safe_image_size(image: Image.Image, max_dim: int = 1536) -> Image.Image:
    """Resize image if its largest dimension exceeds max_dim, preserving aspect ratio."""
    width, height = image.size
    if max(width, height) > max_dim:
        scale = max_dim / max(width, height)
        new_size = (int(width * scale), int(height * scale))
        logger.info(f"DEBUG ENGINE: Resizing large image from {image.size} to {new_size}")
        return image.resize(new_size, Image.Resampling.LANCZOS)
    return image


async def run_chandra_on_image(image: Image.Image) -> str:
    """Run Chandra OCR 2 inference on a single PIL Image.
    Returns structured Markdown preserving layout, headings, tables, etc.
    """
    logger.info(f"DEBUG ENGINE: [Checkpoint 0] Prepared image for inference. Size: {image.size}, Mode: {image.mode}")
    
    # Ensure image is RGB
    if image.mode != "RGB":
        logger.info("DEBUG ENGINE: [Checkpoint 0.1] Converting image mode to RGB")
        image = image.convert("RGB")
    
    # Chandra uses BatchInputItem with prompt_type="ocr_layout" for layout-preserving OCR
    batch = [
        BatchInputItem(
            image=image,
            prompt_type="ocr_layout"
        )
    ]
    
    logger.info("DEBUG ENGINE: [Checkpoint 1] Preparation complete. CUDA check: {} | Memory Allocated: {:.2f}GB".format(
        torch.cuda.is_available(), 
        torch.cuda.memory_allocated() / 1024**3 if torch.cuda.is_available() else 0.0
    ))
    
    start_time = time.time()
    
    # Run inference using Chandra's HuggingFace helper
    # IMPORTANT: Offload to thread to prevent blocking the async loop on CPU-only nodes
    try:
        def sync_inference():
            with torch.no_grad():
                logger.info(f"DEBUG ENGINE: [LLM REQUEST] Dispatching Batch to Chandra. Prompt Type: {batch[0].prompt_type}, Image Size: {batch[0].image.size}")
                local_start = time.time()
                res = generate_hf(batch, hub.chandra_model)
                logger.info(f"DEBUG ENGINE: [Checkpoint 2.1] generate_hf call finished in {time.time() - local_start:.2f}s")
                return res[0]

        result = await asyncio.to_thread(sync_inference)
        logger.info(f"DEBUG ENGINE: [Checkpoint 3] result received in main loop. Raw result type: {type(result)}")
        logger.info(f"DEBUG ENGINE: [LLM RAW RESPONSE]\n{'='*50}\n{result.raw}\n{'='*50}")
    except Exception as ge:
        logger.error(f"DEBUG ENGINE: [Checkpoint ERROR] Failure inside generate_hf/thread: {ge}")
        raise ge
        
    end_time = time.time()
    logger.info(f"DEBUG ENGINE: [Checkpoint 4] Total Inference took {end_time - start_time:.2f}s. Parsing Markdown...")
    
    # Parse raw output into clean Markdown
    markdown_output = parse_markdown(result.raw)
    
    logger.info(f"DEBUG ENGINE: [LLM PARSED MARKDOWN]\n{'='*50}\n{markdown_output}\n{'='*50}")
    logger.info(f"DEBUG ENGINE: [Checkpoint 5] Parsing complete. Markdown length: {len(markdown_output)}")
    return markdown_output


async def process_ocr_task(payload: dict):
    """
    Heavy task: OCR with Chandra OCR 2 (datalab-to/chandra-ocr-2).
    Supports both single images and multi-page PDFs.
    Output: Structured Markdown preserving layout context.
    """
    # Accept either image_base64 or file_base64 + file_ext
    image_data = payload.get("image_base64")
    file_data = payload.get("file_base64")
    file_ext = payload.get("file_ext", "").lower()
    
    if not image_data and not file_data:
        return {"error": "No image or file data provided"}

    try:
        images_to_process: List[Image.Image] = []
        
        if image_data:
            # Single image case
            image_bytes = base64.b64decode(image_data)
            images_to_process.append(Image.open(io.BytesIO(image_bytes)))
        elif file_data:
            file_bytes = base64.b64decode(file_data)
            if file_ext in (".pdf", "pdf"):
                # PDF case: Convert to images
                logger.info("Converting PDF to images inside Hub...")
                images_to_process = convert_from_bytes(file_bytes, dpi=200)
            else:
                # Other file types treated as single images
                images_to_process.append(Image.open(io.BytesIO(file_bytes)))

        if not images_to_process:
            logger.error("DEBUG ENGINE: [TASK-OCR] No images extracted from payload.")
            return {"error": "Failed to extract images from provided data"}

        total_pages = len(images_to_process)
        logger.info(f"Processing {total_pages} page(s) via Chandra OCR 2...")
        
        results = []
        for i, img in enumerate(images_to_process):
            logger.info(f"DEBUG ENGINE: [TASK-OCR] Starting Page {i+1}/{total_pages}...")
            page_start = time.time()
            
            # Safety: Ensure image size is manageable to avoid OOM/Segfault
            img = ensure_safe_image_size(img)
            
            # Explicitly log memory before heavy page
            if torch.cuda.is_available():
                logger.info(f"DEBUG ENGINE: [TASK-OCR] GPU Mem before Page {i+1}: {torch.cuda.memory_allocated()/1024**2:.1f}MB")

            page_markdown = await run_chandra_on_image(img)
            
            page_end = time.time()
            logger.info(f"DEBUG ENGINE: [TASK-OCR] Page {i+1}/{total_pages} Completed in {page_end - page_start:.2f}s")
            
            # Add page marker for multi-page context preservation
            if total_pages > 1:
                page_markdown = f"<!-- PAGE {i+1} / {total_pages} -->\n{page_markdown}"
            results.append(page_markdown)
            
            # Free image memory after processing each page
            del img
            gc.collect()
            
        # Join pages with clear separator  
        full_text = "\n\n---\n\n".join(results)
        
        return {
            "text": full_text,
            "metadata": {
                "total_pages": total_pages,
                "engine": "chandra-ocr-2",
                "output_format": "markdown"
            }
        }
        
    except Exception as e:
        logger.error(f"OCR Error: {e}")
        return {"error": str(e)}

# async def calculate_bertscore_task(payload: dict):
#     """Heavy task: BERTScore calculation. Supports single jd_skill or list of jd_skills."""
#     logger.info(f"DEBUG HUB: Received BERTScore Payload keys: {list(payload.keys())}")
#     
#     cv_skills = payload.get("cv_skills") or payload.get("cv_text") or []
#     jd_skill = payload.get("jd_skill")
#     jd_skills = payload.get("jd_skills") or []
#     
#     # Force wrap single skill into list if plural is missing
#     if jd_skill and not jd_skills:
#         jd_skills = [jd_skill]
#         
#     logger.info(f"DEBUG HUB: CV Skills Count: {len(cv_skills)}, JD Skills Count: {len(jd_skills)}")
#     
#     if not cv_skills or not jd_skills:
#         logger.error(f"DEBUG HUB: Validation Failed. CV: {len(cv_skills)}, JD: {len(jd_skills)}")
#         return {"error": "Missing skills for comparison", "received_keys": list(payload.keys())}
# 
#     # Ensure all elements are strings to prevent 'int too big to convert' tokenizer crashes
#     # and filter out any empty strings
#     try:
#         cv_skills = [str(s).strip() for s in cv_skills if str(s).strip()]
#         jd_skills = [str(s).strip() for s in jd_skills if str(s).strip()]
#     except Exception as e:
#         logger.error(f"DEBUG HUB: Failed to sanitize input skills mapping: {e}")
#         return {"error": f"Invalid skill data types: {e}"}
# 
#     if not cv_skills or not jd_skills:
#         logger.error("DEBUG HUB: Validation Failed AFTER sanitization. Empty skill lists.")
#         return {"error": "Missing valid string skills for comparison"}
# 
#     try:
#         results = {}
#         logger.info(f"DEBUG HUB: Comparing {len(cv_skills)} CV Skills. First 3: {cv_skills[:3]}")
#         
#         # Create Cartesian product of pairs (JD Skill, CV Skill)
#         # This allows the Cross-Encoder to see both concepts simultaneously.
#         all_pairs = []
#         for jd_skill_item in jd_skills:
#             for cv_skill_item in cv_skills:
#                 all_pairs.append((jd_skill_item, cv_skill_item))
#         
#         logger.info(f"DEBUG HUB: Batch matching {len(all_pairs)} pairs using Cross-Encoder...")
#         
#         # Batch prediction on GPU
#         all_scores = hub.skill_matcher.predict(all_pairs, batch_size=32, show_progress_bar=False)
#         
#         # Aggregate Results
#         # For each JD skill, we find the best match in the CV.
#         idx = 0
#         for jd_skill_item in jd_skills:
#             jd_scores = all_scores[idx : idx + len(cv_skills)]
#             idx += len(cv_skills)
#             
#             # Find best match in this JD skill's result slice
#             best_cv_idx = int(np.argmax(jd_scores))
#             best_score = float(jd_scores[best_cv_idx])
#             
#             # Calibrate Status: Cross-Encoder scores are more discriminative.
#             # 0.7+ is usually a strong match. 0.3-0.7 is partial/related.
#             results[jd_skill_item] = {
#                 "best_match": cv_skills[best_cv_idx],
#                 "score": round(best_score, 4),
#                 "status": "PASS" if best_score >= 0.7 else "PARTIAL" if best_score > 0.3 else "MISSING"
#             }
#             
#             logger.info(f"DEBUG HUB: Result for '{jd_skill_item}': BestMatch='{cv_skills[best_cv_idx]}' Score={round(best_score, 4)} Status={results[jd_skill_item]['status']}")
#         
#         # Return object depends on input type
#         if jd_skill and len(jd_skills) == 1:
#             return results[jd_skill]
#         return results
#     except Exception as e:
#         import traceback
#         tb_str = traceback.format_exc()
#         logger.error(f"BERTScore Error: {e}\n{tb_str}")
#         return {"error": str(e), "traceback": tb_str}

