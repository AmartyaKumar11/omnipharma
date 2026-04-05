import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from app.services.ai_service import ACTIVE_LLM_ENDPOINT, ACTIVE_LLM_MODEL, ACTIVE_API_KEY, call_llm

async def main():
    print("--- CONNECTIVITY SMOKE TEST ---")
    print(f"Resolved endpoint: {ACTIVE_LLM_ENDPOINT}")
    print(f"Resolved model:    {ACTIVE_LLM_MODEL}")
    
    if not ACTIVE_API_KEY:
        print("ERROR: No valid API key detected.")
        sys.exit(1)
        
    print(f"Using key prefix:  {ACTIVE_API_KEY[:6]}...")
    
    test_prompt = "Format output exactly like this JSON object: {\"status\": \"ok\", \"message\": \"connectivity success\"}. Output nothing else."
    print("\nSending PING to resolved model...")
    try:
        raw_res = await call_llm(test_prompt)
        print("\nSuccess/Error response string received:")
        print(raw_res)
    except Exception as e:
        print("\nERROR generating response:")
        print(str(e))

if __name__ == "__main__":
    asyncio.run(main())
