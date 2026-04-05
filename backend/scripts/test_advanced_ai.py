import os
import sys
import asyncio
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from app.database import SessionLocal
from app.services.ai_service import ai_pipeline
from app.models.enums import UserRole
from types import SimpleNamespace

async def main():
    print("--- ADVANCED AI INTENT TEST ---")
    queries = [
        "what will be demand next week",
        "what should I worry about",
        "what goes well with paracetamol"
    ]
    
    with SessionLocal() as db:
        from app.models.store import Store
        s1 = db.query(Store).filter(Store.name.like("%Medico%")).first()
        store_id = s1.id if s1 else None
        print(f"Using test store_id: {store_id}")
        
        mock_user = SimpleNamespace(username="admin", role=UserRole.ADMIN, store_id=store_id)
        
        for q in queries:
            print(f"\n[QUERY]: {q}")
            res = await ai_pipeline(query=q, user=mock_user, db=db)
            print(json.dumps(res, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
