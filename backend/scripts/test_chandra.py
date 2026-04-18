import asyncio
import os
import sys

# Thêm đường dẫn backend vào sys.path để import được worker.langgraph_agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import directly from file to avoid loading the whole LangGraph stack which might have DLL issues in this environment
from worker.langgraph_agents.gap_v3.utils.ocr_client import ocr_client

async def test_chandra():
    print("=== Testing Chandra OCR Client ===")
    print(f"API_URL: {ocr_client.api_url}")
    print(f"API_KEY: {ocr_client.api_key[:8]}...{ocr_client.api_key[-4:] if ocr_client.api_key else 'None'}")
    
    # Giả lập file ảo để test logic gửi request (sẽ lỗi file not found nếu không có file thật)
    test_file = "test_cv.pdf"
    if not os.path.exists(test_file):
        with open(test_file, "w") as f:
            f.write("%PDF-1.4 dummy content")
    
    print(f"Testing with file: {test_file}")
    result = await ocr_client.ocr_file(test_file)
    print(f"Result: {result}")
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(test_chandra())
