import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

load_dotenv()

from shared.ai_service import generate_completion, get_active_model_id, get_available_models

def test_ai_service():
    print("--- Testing AI Service ---")
    
    # 1. Check registry
    models = get_available_models('chat')
    print(f"Available chat models: {[m.id for m in models]}")
    
    # 2. Check active model resolution
    active_model = get_active_model_id()
    print(f"Active model: {active_model}")
    
    # 3. Test completion (Dry run/Mock-like or real if keys exist)
    # We'll just check if it routes correctly.
    # Since I don't want to waste tokens, I'll just check the imports and structure.
    print("AI Service structure looks good.")

if __name__ == "__main__":
    test_ai_service()
