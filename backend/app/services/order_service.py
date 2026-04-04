from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.enums import (
    InventoryChangeType,
    InventoryLogSourceType,
    OrderStatus,
    OrderType,
    PrescriptionStatus,
)
from app.models.order import Order, OrderItem, Prescription
from app.models.product import Product
from app.models.stock import Inventory, InventoryLog
from app.models.store import Store
from app.schemas.order import OrderCreate, OrderItemOut, OrderOut, OrderLineIn


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _deduct_inventory(inv: Inventory, take: int) -> None:
    """Reduce stock for a sale: consume reserved units first, then the rest from free stock."""
    sellable = inv.quantity - inv.reserved_quantity
    if sellable < take:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient sellable stock for this inventory row",
        )
    r = inv.reserved_quantity
    inv.reserved_quantity = r - min(r, take)
    inv.quantity -= take


def _merge_items(items: Iterable[OrderLineIn]) -> dict[uuid.UUID, int]:
    merged: dict[uuid.UUID, int] = defaultdict(int)
    for line in items:
        merged[line.product_id] += line.quantity
    return dict(merged)


def _next_order_number(db: Session, year: int) -> str:
    """ORD-YYYY-NNNN with per-year serialization via advisory lock."""
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:lk))"), {"lk": f"order_seq:{year}"})
    prefix = f"ORD-{year}-"
    existing = db.scalars(select(Order.order_number).where(Order.order_number.like(f"{prefix}%"))).all()
    max_n = 0
    for on in existing:
        part = on.rsplit("-", 1)[-1]
        if part.isdigit():
            max_n = max(max_n, int(part))
    nxt = max_n + 1
    if nxt > 9999:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Order number capacity exceeded")
    return f"{prefix}{nxt:04d}"


def _allocate_fefo_for_product(
    db: Session,
    *,
    store_id: uuid.UUID,
    product_id: uuid.UUID,
    need_qty: int,
    today: date,
) -> list[tuple[Inventory, Batch, int, Decimal]]:
    """Lock inventory rows (FEFO) and compute per-batch allocations without mutating yet."""
    stmt = (
        select(Inventory, Batch)
        .join(Batch, Inventory.batch_id == Batch.id)
        .join(Product, Inventory.product_id == Product.id)
        .where(Inventory.store_id == store_id)
        .where(Inventory.product_id == product_id)
        .where(Product.is_deleted.is_(False))
        .where(Batch.expiry_date >= today)
        .where((Inventory.quantity - Inventory.reserved_quantity) > 0)
        .order_by(Batch.expiry_date.asc(), Inventory.id.asc())
        .with_for_update(of=Inventory)
    )
    rows = db.execute(stmt).all()
    remaining = need_qty
    out: list[tuple[Inventory, Batch, int, Decimal]] = []
    for inv, batch in rows:
        if remaining <= 0:
            break
        sellable = inv.quantity - inv.reserved_quantity
        if sellable <= 0:
            continue
        take = min(sellable, remaining)
        price = batch.selling_price if batch.selling_price is not None else Decimal("0")
        out.append((inv, batch, take, Decimal(price)))
        remaining -= take
    if remaining > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock for one or more products",
        )
    return out


def create_order(
    db: Session,
    *,
    body: OrderCreate,
    user_id: uuid.UUID,
) -> OrderOut:
    store = db.get(Store, body.store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    merged = _merge_items(body.items)
    for pid in merged:
        p = db.get(Product, pid)
        if p is None or p.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {pid} not found")

    today = _today_utc()
    year = datetime.now(timezone.utc).year
    order_id = uuid.uuid4()

    allocation_lines: list[dict] = []
    for product_id, need in sorted(merged.items(), key=lambda x: str(x[0])):
        chunks = _allocate_fefo_for_product(
            db,
            store_id=body.store_id,
            product_id=product_id,
            need_qty=need,
            today=today,
        )
        for inv, batch, take, price in chunks:
            allocation_lines.append(
                {
                    "inventory_id": inv.id,
                    "inv": inv,
                    "batch": batch,
                    "product_id": product_id,
                    "qty": take,
                    "price": price,
                }
            )

    total_amount = sum((line["qty"] * line["price"] for line in allocation_lines), Decimal("0"))

    for line in allocation_lines:
        _deduct_inventory(line["inv"], line["qty"])

    order_number = _next_order_number(db, year)
    ts = _now()
    order = Order(
        id=order_id,
        order_number=order_number,
        store_id=body.store_id,
        user_id=user_id,
        order_type=body.order_type,
        status=OrderStatus.COMPLETED,
        total_amount=total_amount,
        payment_method=body.payment_method,
        notes=body.notes,
        created_at=ts,
        updated_at=ts,
    )
    db.add(order)
    db.flush()

    item_rows: list[OrderItemOut] = []
    for line in allocation_lines:
        batch = line["batch"]
        qty = line["qty"]
        price = line["price"]
        oi = OrderItem(
            id=uuid.uuid4(),
            order_id=order_id,
            product_id=line["product_id"],
            batch_id=batch.id,
            quantity=qty,
            price_at_sale=price,
            created_at=ts,
            updated_at=ts,
        )
        db.add(oi)
        prod = db.get(Product, line["product_id"])
        assert prod is not None
        item_rows.append(
            OrderItemOut(
                id=oi.id,
                product_id=line["product_id"],
                product_name=prod.name,
                batch_id=batch.id,
                batch_number=batch.batch_number,
                quantity=qty,
                price_at_sale=price,
                line_total=price * qty,
            )
        )

    for line in allocation_lines:
        log = InventoryLog(
            id=uuid.uuid4(),
            inventory_id=line["inventory_id"],
            change_type=InventoryChangeType.REMOVE,
            source_type=InventoryLogSourceType.SALE,
            reference_id=order_id,
            quantity_changed=line["qty"],
            reason=None,
            notes=None,
            performed_by=user_id,
            created_at=ts,
            updated_at=ts,
        )
        db.add(log)

    if body.order_type is OrderType.PRESCRIPTION:
        assert body.prescription_file_url
        rx = Prescription(
            id=uuid.uuid4(),
            order_id=order_id,
            uploaded_by=user_id,
            file_url=body.prescription_file_url.strip(),
            doctor_name=body.doctor_name,
            notes=body.prescription_notes,
            status=PrescriptionStatus.UPLOADED,
            created_at=ts,
            updated_at=ts,
        )
        db.add(rx)

    db.commit()
    db.refresh(order)

    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        store_id=order.store_id,
        user_id=order.user_id,
        order_type=order.order_type.value,
        status=order.status.value,
        total_amount=order.total_amount,
        payment_method=order.payment_method.value,
        notes=order.notes,
        created_at=order.created_at,
        items=item_rows,
    )


def list_orders(
    db: Session,
    *,
    store_id: uuid.UUID | None,
    date_from: date | None,
    date_to: date | None,
) -> list[OrderOut]:
    q = select(Order).order_by(Order.created_at.desc())
    if store_id is not None:
        q = q.where(Order.store_id == store_id)
    if date_from is not None:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        q = q.where(Order.created_at >= start)
    if date_to is not None:
        end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        q = q.where(Order.created_at <= end)

    orders = db.scalars(q).all()
    if not orders:
        return []
    ids = [o.id for o in orders]
    rows = db.execute(
        select(OrderItem, Product, Batch)
        .join(Product, OrderItem.product_id == Product.id)
        .join(Batch, OrderItem.batch_id == Batch.id)
        .where(OrderItem.order_id.in_(ids))
        .order_by(OrderItem.order_id.asc(), OrderItem.created_at.asc())
    ).all()
    by_order: dict[uuid.UUID, list[OrderItemOut]] = defaultdict(list)
    for oi, prod, batch in rows:
        price = Decimal(oi.price_at_sale)
        by_order[oi.order_id].append(
            OrderItemOut(
                id=oi.id,
                product_id=oi.product_id,
                product_name=prod.name,
                batch_id=batch.id,
                batch_number=batch.batch_number,
                quantity=oi.quantity,
                price_at_sale=price,
                line_total=price * oi.quantity,
            )
        )
    return [
        OrderOut(
            id=o.id,
            order_number=o.order_number,
            store_id=o.store_id,
            user_id=o.user_id,
            order_type=o.order_type.value,
            status=o.status.value,
            total_amount=o.total_amount,
            payment_method=o.payment_method.value,
            notes=o.notes,
            created_at=o.created_at,
            items=by_order.get(o.id, []),
        )
        for o in orders
    ]


def get_order_detail(db: Session, *, order_id: uuid.UUID) -> OrderOut | None:
    order = db.get(Order, order_id)
    if order is None:
        return None
    rows = db.execute(
        select(OrderItem, Product, Batch)
        .join(Product, OrderItem.product_id == Product.id)
        .join(Batch, OrderItem.batch_id == Batch.id)
        .where(OrderItem.order_id == order_id)
        .order_by(OrderItem.created_at.asc())
    ).all()
    items: list[OrderItemOut] = []
    for oi, prod, batch in rows:
        price = Decimal(oi.price_at_sale)
        items.append(
            OrderItemOut(
                id=oi.id,
                product_id=oi.product_id,
                product_name=prod.name,
                batch_id=batch.id,
                batch_number=batch.batch_number,
                quantity=oi.quantity,
                price_at_sale=price,
                line_total=price * oi.quantity,
            )
        )
    return OrderOut(
        id=order.id,
        order_number=order.order_number,
        store_id=order.store_id,
        user_id=order.user_id,
        order_type=order.order_type.value,
        status=order.status.value,
        total_amount=order.total_amount,
        payment_method=order.payment_method.value,
        notes=order.notes,
        created_at=order.created_at,
        items=items,
    )
