import os
import sys

# Add backend directory to import path to allow app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.user import User
from app.models.store import Store
from app.models.mapping import UserStoreMapping
from sqlalchemy import select

from datetime import datetime, timezone

def main():
    with SessionLocal() as db:
        # Fetch Medico Hub Central store
        store = db.scalar(select(Store).where(Store.name == "Medico Hub Central"))
        if not store:
            print("Store 'Medico Hub Central' not found! Creating it...")
            store = Store(
                name="Medico Hub Central",
                location="Main Branch",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(store)
            db.commit()
            db.refresh(store)
            print(f"Created store: {store.id}")

        usernames_to_map = ["amartyabranch", "amartyainventory", "amartyastaff"]
        for un in usernames_to_map:
            user = db.scalar(select(User).where(User.username == un))
            if not user:
                print(f"User {un} not found.")
                continue
            
            mapping = db.scalar(select(UserStoreMapping).where(UserStoreMapping.user_id == user.id))
            if not mapping:
                mapping = UserStoreMapping(user_id=user.id, store_id=store.id)
                db.add(mapping)
                try:
                    db.commit()
                    print(f"Successfully mapped user {un} to store {store.name}.")
                except Exception as e:
                    db.rollback()
                    print(f"Error mapping {un}: {e}")
            else:
                print(f"User {un} is already mapped.")

if __name__ == "__main__":
    main()
