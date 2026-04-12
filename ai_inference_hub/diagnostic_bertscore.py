import os
import torch
from bert_score import BERTScorer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diagnostic")

def test_bertscore():
    model_name = "microsoft/deberta-base-mnli"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    logger.info(f"Initializing BERTScorer with {model_name} on {device}...")
    scorer = BERTScorer(model_type=model_name, device=device)
    
    # Check tokenizer max length
    if hasattr(scorer, "_tokenizer"):
        tokenizer = scorer._tokenizer
        logger.info(f"Tokenizer model_max_length: {tokenizer.model_max_length}")
        if tokenizer.model_max_length > 1000000:
            tokenizer.model_max_length = 512
            logger.info("Capped tokenizer length to 512")

    test_pairs = [
        ("Android", "Android"),
        ("Android", "Python"),
        ("iOS", "Python"),
        ("C", "Java"),
        ("C", "C++"),
        ("SQL", "Python")
    ]
    
    logger.info("Starting scoring tests...")
    for cands, refs in test_pairs:
        # BERTScore.score expects (candidate_list, reference_list)
        P, R, F1 = scorer.score([cands], [refs])
        score = F1.item()
        logger.info(f"Score for ('{cands}', '{refs}'): {score:.4f}")
        if score > 0.99 and cands != refs:
            logger.error(f"  CRITICAL: '{cands}' and '{refs}' scored 1.0 but are different!")

if __name__ == "__main__":
    test_bertscore()
