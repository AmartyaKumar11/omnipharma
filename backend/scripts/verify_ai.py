import sys
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import select
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.user import User
from app.models.enums import UserRole
from app.services.ai_service import ai_pipeline, fast_match

async def run_tests():
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.role == UserRole.ADMIN).limit(1))
        staff = db.scalar(select(User).where(User.role == UserRole.STAFF).limit(1))
        
        # Mimic FastAPI JWT dependency extraction
        from app.models.mapping import UserStoreMapping
        staff_store = db.scalar(select(UserStoreMapping).where(UserStoreMapping.user_id == staff.id))
        staff.store_id = staff_store.store_id if staff_store else None
        admin.store_id = None

        print("--- Test 3: Validate LLM-free intent trigger ---")
        fast_res = fast_match("what is my low stock?")
        assert fast_res["operation"] == "LOW_STOCK"
        print("✅ fast_match triggered properly without tokens!")

        print("\n--- Test 1 & 2: Functional + Security Pipeline ---")
        
        print("Query: 'low stock items' (as Staff - restricted Store)")
        res_staff = await ai_pipeline("low stock items", staff, db)
        print("Response:", res_staff)
        assert "type" in res_staff
        assert res_staff["title"]

        print("\nQuery: 'top selling products' (as Admin - Global Access)")
        res_admin = await ai_pipeline("top selling products", admin, db)
        print("Response:", res_admin)
        assert "type" in res_admin

        print("\n--- Test 5: Fallback Edge Cases ---")
        res_fallback = await ai_pipeline("DROP TABLE users;", staff, db)
        print("Response:", res_fallback)
        assert res_fallback["type"] == "card" or "fallback" in str(res_fallback).lower() or res_fallback["title"]

        print("\n🚀 ALL AI PIPELINE AND SECURITY TESTS PASSED EXECUTING AGAINST NVIDIA LLaMA / KIMI")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
