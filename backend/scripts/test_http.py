import httpx
import asyncio

async def test_endpoint():
    print("Beginning HTTP Mock Request...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login
        login_res = await client.post(
            "http://127.0.0.1:8020/auth/login",
            json={"username": "amartyabranch", "password": "password123"}
        )
        print(f"Login Status: {login_res.status_code}")
        if login_res.status_code != 200:
            print("Login failed:", login_res.text)
            return
        
        token = login_res.json()["access_token"]
        
        # 2. Query AI
        print("Sending standard fast_match Query...")
        res = await client.post(
            "http://127.0.0.1:8020/ai/query",
            json={"query": "low stock items"},
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"AI Query Status: {res.status_code}")
        print("AI Response Keys:", list(res.json().keys()))
        print("AI Title:", res.json().get("title"))

        # 3. Query LLM Parse
        print("\nSending complex LLM parsing Query...")
        res2 = await client.post(
            "http://127.0.0.1:8020/ai/query",
            json={"query": "which store is doing best?"},
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"AI Query 2 Status: {res2.status_code}")
        print("AI Response 2 Keys:", list(res2.json().keys()))
        print("AI Title 2:", res2.json().get("title"))
        print("AI Error Summary:", res2.json().get("summary"))

if __name__ == "__main__":
    asyncio.run(test_endpoint())
