import os
import sys
from unittest.mock import MagicMock, patch

# Mock các module phụ thuộc trước khi import llm_utils
mock_redis = MagicMock()
sys.modules["redis"] = mock_redis
sys.modules["shared.redis_client"] = MagicMock()

# Thêm đường dẫn backend vào sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock config_utils để tránh gọi Redis/DB thực tế
sys.modules["shared.config_utils"] = MagicMock()
import shared.config_utils
shared.config_utils.config_manager = MagicMock()

from shared.llm_utils import LLMFactory, get_chat_completion

def test_provider_mapping():
    print("Testing provider mapping...")
    assert LLMFactory.get_provider("gemini-1.5-flash") == "google"
    assert LLMFactory.get_provider("gpt-4o") == "openai"
    assert LLMFactory.get_provider("claude-3-5-sonnet") == "anthropic"
    assert LLMFactory.get_provider("unknown-model") == "openai" # Default
    print("✓ Provider mapping OK")

def test_dynamic_model_retrieval():
    print("\nTesting dynamic model retrieval...")
    
    # Mock config_manager
    mock_config = shared.config_utils.config_manager
    
    # Case 1: Model từ DB -> Gemini
    mock_config.get_setting.return_value = "gemini-1.5-flash"
    
    with patch("google.generativeai.configure"):
        with patch("google.generativeai.GenerativeModel") as mock_genai:
            mock_instance = mock_genai.return_value
            mock_instance.generate_content.return_value.text = '{"success": true}'
            
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
                res = get_chat_completion("Hello", json_mode=True)
                print(f"Result with Gemini: {res}")
                assert res == '{"success": true}'
                mock_genai.assert_called_once()
                
    # Case 2: Model từ OpenAI
    mock_config.get_setting.return_value = "gpt-4o-mini"
    with patch("shared.llm_utils.LLMFactory.get_openai_client") as mock_oa:
        mock_client = mock_oa.return_value
        mock_client.chat.completions.create.return_value.choices[0].message.content = "OpenAI Hello"
        
        res = get_chat_completion("Hello")
        print(f"Result with OpenAI: {res}")
        assert res == "OpenAI Hello"
            
    print("✓ Dynamic model retrieval OK")

if __name__ == "__main__":
    try:
        test_provider_mapping()
        test_dynamic_model_retrieval()
        print("\nALL VERIFICATIONS PASSED!")
    except Exception as e:
        print(f"\nVERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
