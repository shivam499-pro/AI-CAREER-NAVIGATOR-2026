import httpx
import os
from dotenv import load_dotenv
import json

load_dotenv()

async def test_serpapi():
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("❌ Error: SERPAPI_KEY not found in .env file")
        return

    print(f"✅ Key found beginning with: {api_key[:5]}...")
    
    params = {
        "q": "Mobile App Developer jobs Chennai",
        "api_key": api_key,
        "engine": "google_jobs"
    }

    try:
        print(f"📡 Sending request to SerpAPI for 'Mobile App Developer jobs Chennai'...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://serpapi.com/search",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("jobs_results", [])
                
                if results:
                    print(f"🎉 Success! Found {len(results)} live job results.")
                    print("\n--- SAMPLE JOBS FOUND ---")
                    for i, job in enumerate(results[:3]):
                        print(f"{i+1}. {job.get('title')} at {job.get('company_name')} ({job.get('location')})")
                else:
                    print("⚠️ Request succeeded but no jobs_results found in JSON.")
                    print("Full keys in response:", data.keys())
                    if "error" in data:
                        print("Error message from SerpAPI:", data["error"])
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print("Response text:", response.text)

    except Exception as e:
        print(f"❌ Request failed with exception: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_serpapi())
