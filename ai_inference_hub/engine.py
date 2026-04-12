import torch
from models import hub
import logging
from PIL import Image
import io
import base64
import os
import gc
import time
from pdf2image import convert_from_bytes
from typing import List

logger = logging.getLogger("ai_engine")

# --- Chandra OCR 2 specific imports ---
from chandra.model.hf import generate_hf
from chandra.model.schema import BatchInputItem
from chandra.output import parse_markdown


async def run_chandra_on_image(image: Image.Image) -> str:
    """Run Chandra OCR 2 inference on a single PIL Image.
    Returns structured Markdown preserving layout, headings, tables, etc.
    """
    logger.info(f"DEBUG ENGINE: Prepared image for inference. Size: {image.size}, Mode: {image.mode}")
    
    # Ensure image is RGB
    if image.mode != "RGB":
        logger.info("DEBUG ENGINE: Converting image mode to RGB")
        image = image.convert("RGB")
    
    # Chandra uses BatchInputItem with prompt_type="ocr_layout" for layout-preserving OCR
    batch = [
        BatchInputItem(
            image=image,
            prompt_type="ocr_layout"
        )
    ]
    
    logger.info("DEBUG ENGINE: >>> Starting generate_hf inference loop...")
    start_time = time.time()
    
    # Run inference using Chandra's HuggingFace helper
    # This handles tokenization, generation, and decoding internally
    try:
        with torch.no_grad():
            logger.info("DEBUG ENGINE: Calling generate_hf...")
            result = generate_hf(batch, hub.chandra_model)[0]
    except Exception as ge:
        logger.error(f"DEBUG ENGINE: Error inside generate_hf: {ge}")
        raise ge
        
    end_time = time.time()
    logger.info(f"DEBUG ENGINE: <<< generate_hf finished in {end_time - start_time:.2f}s. Parsing results...")
    
    # Parse raw output into clean Markdown
    markdown_output = parse_markdown(result.raw)
    
    logger.info(f"DEBUG ENGINE: Parsing complete. Output length: {len(markdown_output)}")
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
            return {"error": "Failed to extract images from provided data"}

        total_pages = len(images_to_process)
        logger.info(f"Processing {total_pages} page(s) via Chandra OCR 2...")
        
        results = []
        for i, img in enumerate(images_to_process):
            logger.info(f"DEBUG ENGINE: [Page {i+1}/{total_pages}] Starting inference...")
            page_start = time.time()
            
            page_markdown = await run_chandra_on_image(img)
            
            page_end = time.time()
            logger.info(f"DEBUG ENGINE: [Page {i+1}/{total_pages}] Completed in {page_end - page_start:.2f}s")
            
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

async def calculate_bertscore_task(payload: dict):
    """Heavy task: BERTScore calculation. Supports single jd_skill or list of jd_skills."""
    logger.info(f"DEBUG HUB: Received BERTScore Payload keys: {list(payload.keys())}")
    
    cv_skills = payload.get("cv_skills") or payload.get("cv_text") or []
    jd_skill = payload.get("jd_skill")
    jd_skills = payload.get("jd_skills") or []
    
    # Force wrap single skill into list if plural is missing
    if jd_skill and not jd_skills:
        jd_skills = [jd_skill]
        
    logger.info(f"DEBUG HUB: CV Skills Count: {len(cv_skills)}, JD Skills Count: {len(jd_skills)}")
    
    if not cv_skills or not jd_skills:
        logger.error(f"DEBUG HUB: Validation Failed. CV: {len(cv_skills)}, JD: {len(jd_skills)}")
        return {"error": "Missing skills for comparison", "received_keys": list(payload.keys())}

    # If single skill provided, wrap it in a list
    if jd_skill and not jd_skills:
        jd_skills = [jd_skill]

    try:
        results = {}
        logger.info(f"DEBUG HUB: Comparing CV Skills: {cv_skills}")
        for skill in jd_skills:
            # Parallelize over CV skills using BERTScore's vectorization
            P, R, F1 = hub.bert_scorer.score(cv_skills, [skill] * len(cv_skills))
            
            # Find best match
            best_idx = F1.argmax().item()
            best_score = F1[best_idx].item()
            
            # SỬA: Đồng bộ threshold 0.85 (Strict High-Precision)
            results[skill] = {
                "best_match": cv_skills[best_idx],
                "score": round(best_score, 4),
                "status": "PASS" if best_score >= 0.85 else "PARTIAL" if best_score > 0.70 else "MISSING"
            }
            logger.info(f"DEBUG HUB: Result for '{skill}': Match='{cv_skills[best_idx]}' Score={round(best_score, 4)} Status={results[skill]['status']}")
        
        # Return object depends on input type
        if jd_skill and len(jd_skills) == 1:
            return results[jd_skill]
        return results
    except Exception as e:
        logger.error(f"BERTScore Error: {e}")
        return {"error": str(e)}
