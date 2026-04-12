import os
import sys
import logging

# Add current directory to path so we can import hub
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

print("--- Testing BERTScore Loading ---")
try:
    from models import hub
    # Mock some env vars if needed
    os.environ["HF_LOCAL_FILES_ONLY"] = "0" 
    
    print("Initializing BERTScorer...")
    hub.load_bertscore()
    
    if hub.bert_scorer is not None:
        print("✅ SUCCESS: BERTScorer initialized successfully.")
    else:
        print("❌ FAILURE: BERTScorer is None.")
        
except Exception as e:
    print(f"❌ FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("--- Test Complete ---")
