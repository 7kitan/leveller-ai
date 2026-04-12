import asyncio
import os
import sys
import json
from unittest.mock import MagicMock

# Add current directory to path
sys.path.append(os.getcwd())

from services.analysis_service.engine.retriever import RequirementRetriever

# Set env for OpenAI (ensure API key is available in environment)
os.environ["LLM_PROVIDER"] = "openai"

async def main():
    db = MagicMock()
    retriever = RequirementRetriever(db)
    
    jd_text = """
    - Sử dụng tốt ít nhất 1 ngôn ngữ lập trình (C/C++/Java/Golang/Android/iOS)
    - Có kiến thức về Docker/Kubernetes là một lợi thế.
    - Kinh nghiệm làm việc với MySQL hoặc PostgreSQL.
    """
    
    print("Testing JD extraction...")
    try:
        requirements = await retriever._ai_extract(jd_text)
        
        print("\nExtracted Requirements:")
        print(json.dumps(requirements, indent=2))
        
        # Check if the specific group exists
        found_group = False
        for req in requirements:
            if req.get("type") == "group" and req.get("group_strategy") == "exclusive":
                skills = [s["skill"].lower() for s in req.get("skills", [])]
                if "c" in skills or "java" in skills or "golang" in skills:
                    found_group = True
                    print(f"\n✅ SUCCESS: Found exclusive group for languages: {req.get('group_name')}")
                    break
        
        if not found_group:
            print("\n❌ FAILURE: Could not find grouped languages as an exclusive group.")
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    asyncio.run(main())
