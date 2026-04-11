import torch
from models import hub
import logging
from PIL import Image
import io
import base64
import os
import tempfile
from pdf2image import convert_from_bytes
from typing import List

logger = logging.getLogger("ai_engine")

async def run_chandra_on_image(image: Image.Image) -> str:
    """Helper command to run VLM inference on a single PIL Image."""
    # Ensure image is RGB
    if image.mode != "RGB":
        image = image.convert("RGB")
        
    # Inference logic (Assuming Florence-2 style API for Chandra-1)
    prompt = "<OCR>" # Example task - replace with actual Chandra prompt if known
    inputs = hub.chandra_processor(text=prompt, images=image, return_tensors="pt").to("cpu")
    
    with torch.no_grad():
        generated_ids = hub.chandra_model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3
        )
    
    parsed_answer = hub.chandra_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return parsed_answer

async def process_ocr_task(payload: dict):
    """
    Heavy task: OCR with Chandra VLM.
    Supports both single images and multi-page PDFs.
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
            if file_ext == ".pdf" or file_ext == "pdf":
                # PDF case: Convert to images
                logger.info("Converting PDF to images inside Hub...")
                images_to_process = convert_from_bytes(file_bytes, dpi=200)
            else:
                # Other file types treated as single images
                images_to_process.append(Image.open(io.BytesIO(file_bytes)))

        if not images_to_process:
            return {"error": "Failed to extract images from provided data"}

        logger.info(f"Processing {len(images_to_process)} page(s) via Chandra...")
        results = []
        for i, img in enumerate(images_to_process):
            logger.info(f"Inferencing page {i+1}/{len(images_to_process)}...")
            page_text = await run_chandra_on_image(img)
            results.append(page_text)
            
        return {"text": "\n\n---\n\n".join(results)}
        
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
        for skill in jd_skills:
            # Parallelize over CV skills using BERTScore's vectorization
            P, R, F1 = hub.bert_scorer.score(cv_skills, [skill] * len(cv_skills))
            
            # Find best match
            best_idx = F1.argmax().item()
            best_score = F1[best_idx].item()
            
            results[skill] = {
                "best_match": cv_skills[best_idx],
                "score": round(best_score, 4),
                "status": "PASS" if best_score > 0.88 else "PARTIAL" if best_score > 0.70 else "MISSING"
            }
        
        # Return object depends on input type
        if jd_skill and len(jd_skills) == 1:
            return results[jd_skill]
        return results
    except Exception as e:
        logger.error(f"BERTScore Error: {e}")
        return {"error": str(e)}
