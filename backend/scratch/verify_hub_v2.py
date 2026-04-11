import os
import asyncio
from dotenv import load_dotenv
import httpx
import json

load_dotenv()

async def test_hub_health():
    api_url = os.getenv("CHANDRA_API_URL")
    if not api_url:
        print("Error: CHANDRA_API_URL not set")
        return
    
    base_url = api_url.replace("/tasks/ocr", "")
    print(f"Testing AI Hub Health at: {base_url}/health")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/health")
            print(f"Health Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Health Data: {resp.json()}")
    except Exception as e:
        print(f"Health test failed: {e}")

async def test_bert_score():
    api_url = os.getenv("BERTSCORE_API_URL")
    api_key = os.getenv("BERTSCORE_API_KEY")
    
    print(f"\nTesting BERTScore API at: {api_url}")
    if not api_url:
        print("Error: BERTSCORE_API_URL not set")
        return

    payload = {
        "cv_skills": ["Python", "FastAPI", "PostgreSQL"],
        "jd_skill": "Advanced Python Backend Development"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if not api_key:
                print("Error: BERTSCORE_API_KEY environment variable is not set!")
                return
            
            headers = {"X-AI-Key": api_key}
            resp = await client.post(api_url, json=payload, headers=headers)
            print(f"Post Task Status: {resp.status_code}")
            if resp.status_code == 200:
                task_data = resp.json()
                task_id = task_data.get("task_id")
                print(f"Task Created: {task_id}")
                
                # Poll for result
                base_url = api_url.replace("/tasks/bertscore", "")
                poll_url = f"{base_url}/tasks/{task_id}"
                
                print(f"Polling status at: {poll_url}")
                for i in range(5):
                    await asyncio.sleep(2)
                    poll_resp = await client.get(poll_url, headers=headers)
                    data = poll_resp.json()
                    print(f"Status: {data.get('status')}")
                    if data.get("status") == "completed":
                        print(f"Result: {json.dumps(data.get('result'), indent=2)}")
                        break
                    elif data.get("status") == "failed":
                        print(f"Error: {data.get('error')}")
                        break
            else:
                print(f"Response Body: {resp.text}")
    except Exception as e:
        print(f"BERTScore test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_hub_health())
    asyncio.run(test_bert_score())
