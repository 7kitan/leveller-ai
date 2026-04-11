import os
import asyncio
from dotenv import load_dotenv
import httpx

load_dotenv()

async def test_chandra_api():
    api_url = os.getenv("CHANDRA_API_URL")
    api_key = os.getenv("CHANDRA_API_KEY")
    
    print(f"Testing Chandra API at: {api_url}")
    if not api_key:
        print("Error: CHANDRA_API_KEY not set")
        return

    # Simulate a dummy request (or actual if key was provided)
    # Since I don't have a real image here right now, I just check reachability
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(api_url.replace("/ocr", "")) # Try health check or parent path
            print(f"API Base Reachable: {resp.status_code}")
    except Exception as e:
        print(f"Reachability test failed: {e}")

async def test_bert_score():
    api_url = os.getenv("BERTSCORE_API_URL")
    api_key = os.getenv("BERTSCORE_API_KEY")
    
    print(f"Testing BERTScore API at: {api_url}")
    if not api_url:
        print("Error: BERTSCORE_API_URL not set")
        return

    payload = {
        "text1": "I am a Senior Python Developer with 5 years of experience in FastAPI and React.",
        "text2": "The ideal candidate should have strong experience in Python, web frameworks, and frontend libraries."
    }
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {"X-Api-Key": api_key} if api_key else {}
            resp = await client.post(api_url, json=payload, headers=headers)
            print(f"Response: {resp.status_code}")
            if resp.status_code == 200:
                print(f"BERTScore result: {resp.json()}")
    except Exception as e:
        print(f"BERTScore test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_chandra_api())
    asyncio.run(test_bert_score())
