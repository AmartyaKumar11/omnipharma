import os
import sys
import uuid
import random
from decimal import Decimal
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.store import Store
from app.models.user import User
from app.models.mapping import UserStoreMapping
from app.models.product import Product
from app.models.stock import Inventory, InventoryLog, InventoryChangeType, InventoryLogSourceType
from app.models.order import Order, OrderItem
from app.models.enums import UserRole, OrderType, OrderStatus, PaymentMethod

def generate_random_date():
    now = datetime.now(timezone.utc)
    days_ago = random.randint(0, 30)
    return now - timedelta(days=days_ago)

def main():
    print("Running granular Order seeding for Neon connection limits...")
    with SessionLocal() as db:
        if db.query(Order).count() > 0:
            print("Orders already seeded. Skipping.")
            return

        stores = db.query(Store).all()
        users = db.query(User).all()
        inventories = db.query(Inventory).all()
        
        admin_id = next((u.id for u in users if u.role == UserRole.ADMIN), None)
        if not admin_id:
            print("No admin found!")
            return

        mappings = db.query(UserStoreMapping).all()

        print("Generating 50 orders...")
        orders = []
        for i in range(50):
            store = random.choice(stores)
            
            store_users = [
                u for u in users 
                if any(m.user_id == u.id and m.store_id == store.id for m in mappings)
            ]
            user_id = random.choice(store_users).id if store_users else admin_id
            
            order_date = generate_random_date()
            o_id = uuid.uuid4()
            o = Order(
                id=o_id,
                store_id=store.id,
                user_id=user_id,
                order_number=f"ORD-{order_date.strftime('%Y%m%d')}-{random.randint(1000,9999)}",
                order_type=random.choice(list(OrderType)),
                status=OrderStatus.COMPLETED,
                payment_method=random.choice(list(PaymentMethod)),
                total_amount=0,
                created_at=order_date,
                updated_at=order_date
            )
            db.add(o)
            
            # Add 1 to 3 items
            store_invs = [inv for inv in inventories if inv.store_id == store.id and inv.quantity > 0]
            if not store_invs:
                continue
                
            num_items = random.randint(1, min(3, len(store_invs)))
            chosen_invs = random.sample(store_invs, num_items)
            
            total_amt = Decimal("0.00")
            for inv in chosen_invs:
                p = db.query(Product).filter(Product.id == inv.product_id).first()
                price = getattr(p, 'unit_price', Decimal("10.00"))
                qty = random.randint(1, min(5, inv.quantity))
                
                oi = OrderItem(
                    id=uuid.uuid4(),
                    order_id=o_id,
                    product_id=inv.product_id,
                    batch_id=inv.batch_id,
                    quantity=qty,
                    price_at_sale=price,
                    created_at=order_date,
                    updated_at=order_date
                )
                db.add(oi)
                total_amt += price
                
                log = InventoryLog(
                    id=uuid.uuid4(),
                    inventory_id=inv.id,
                    change_type=InventoryChangeType.REMOVE,
                    source_type=InventoryLogSourceType.SALE,
                    reference_id=str(o_id),
                    quantity_changed=-qty,
                    reason="Sale",
                    performed_by=user_id,
                    created_at=order_date,
                    updated_at=order_date
                )
                db.add(log)
                
            o.total_amount = total_amt
            orders.append(o)
            
            # Commit every 10 orders to prevent Neon timeout
            if len(orders) % 10 == 0:
                print(f"Committing {len(orders)} orders/logs...")
                db.commit()

        # Commit remaining
        db.commit()
        print("🚀 Successfully seeded remaining Orders, OrderItems, and InventoryDeductions safely!")

if __name__ == "__main__":
    main()
