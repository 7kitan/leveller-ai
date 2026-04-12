import torch
import sys
import time
import requests

def test_gpu_availability():
    print("--- System Check ---")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    if cuda_available:
        print(f"Device Name: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_memory_info(0)[1] / 1024**3:.2f} GB")
    else:
        print("ERROR: CUDA not found. Check your NVIDIA drivers.")
        # sys.exit(1)

def test_local_inference():
    print("\n--- Testing Local Model Loading (Models.py) ---")
    try:
        from models import hub
        start_time = time.time()
        hub.load_all()
        print(f"Models loaded successfully in {time.time() - start_time:.2f}s")
        
        if hub.chandra_model:
            print(f"Chandra Device: {hub.chandra_model.device}")
        if hub.bert_scorer:
             print(f"BERTScore Device: {hub.bert_scorer.device}")
    except Exception as e:
        print(f"Inference Test Failed: {e}")

if __name__ == "__main__":
    test_gpu_availability()
    # Uncomment the line below to test actual model loading (requires ~4GB VRAM and internet)
    # test_local_inference()
