import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_bertscore():
    api_url = os.getenv("BERTSCORE_API_URL")
    api_key = os.getenv("BERTSCORE_API_KEY")
    
    print(f"Testing BERTScore API at: {api_url}")
    
    payload = {
        "cv_skills": ["Python", "JavaScript", "React", "Node.js"],
        "jd_skill": "Advanced Python Programming"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                api_url, 
                json=payload, 
                headers={"X-AI-Key": api_key} if api_key else {}
            )
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_bertscore())
