import os
import sys

# Add backend directory to import path to allow app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.user import User
from app.models.store import Store
from app.models.mapping import UserStoreMapping
from sqlalchemy import select

def main():
    with SessionLocal() as db:
        # Fetch Medico Hub Central store
        store = db.scalar(select(Store).where(Store.name == "Medico Hub Central"))
        if not store:
            # Let's try to fetch any store if Medico Hub Central is not found
            store = db.scalar(select(Store).limit(1))
            if not store:
                print("No stores found in the database. Please create one.")
                return
            else:
                print(f"'Medico Hub Central' not found! Falling back to: {store.name}")

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
