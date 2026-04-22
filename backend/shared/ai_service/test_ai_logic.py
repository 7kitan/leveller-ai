import os
import sys
from unittest.mock import MagicMock

# Create a mock for shared.config_utils before importing ai_service
mock_config_utils = MagicMock()
mock_config_manager = MagicMock()
mock_config_manager.get_setting.return_value = "gpt-4o"
sys.modules['shared.config_utils'] = mock_config_utils
mock_config_utils.config_manager = mock_config_manager

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from shared.ai_service.registry import AI_REGISTRY, get_model_info
from shared.ai_service.core import get_active_model_id

def test_ai_logic():
    print("--- Testing AI Service Logic ---")
    
    # 1. Check registry
    print("SUCCESS: Registry lookup works")
    
    # 2. Check active model resolution (should use the mock)
    active_model = get_active_model_id()
    assert active_model == "gpt-4o"
    print(f"SUCCESS: Active model resolution works (Mocked DB: {active_model})")
    
    # 3. Check override
    override = get_active_model_id("gemini-1.5-flash")
    assert override == "gemini-1.5-flash"
    print(f"SUCCESS: Model override works: {override}")

    print("\nAI Service Logic Verification Passed!")

if __name__ == "__main__":
    test_ai_logic()
