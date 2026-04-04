from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.enums import AlertSeverity, AlertType, InventoryChangeType, InventoryLogSourceType
from app.models.product import Product
from app.models.stock import Inventory, InventoryLog
from app.models.store import Store
from app.schemas.inventory import AlertItem, AlertsResponse, BatchPublic, InventoryRowPublic, ProductPublic


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_product(db: Session, *, name: str, generic_name: str | None, category: str | None, manufacturer: str | None, description: str | None, is_prescription_required: bool) -> Product:
    ts = _now()
    p = Product(
        name=name.strip(),
        generic_name=generic_name,
        category=category,
        manufacturer=manufacturer,
        description=description,
        is_prescription_required=is_prescription_required,
        is_deleted=False,
        created_at=ts,
        updated_at=ts,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def create_batch(
    db: Session,
    *,
    product_id: uuid.UUID,
    batch_number: str,
    expiry_date: date,
    manufacture_date: date | None,
    purchase_price: Decimal | None,
    selling_price: Decimal | None,
) -> Batch:
    product = db.get(Product, product_id)
    if product is None or product.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    ts = _now()
    b = Batch(
        product_id=product_id,
        batch_number=batch_number.strip(),
        expiry_date=expiry_date,
        manufacture_date=manufacture_date,
        purchase_price=purchase_price,
        selling_price=selling_price,
        created_at=ts,
        updated_at=ts,
    )
    db.add(b)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Batch number already exists for this product",
        ) from e
    db.refresh(b)
    return b


def _append_inventory_log(
    db: Session,
    *,
    inventory_id: uuid.UUID,
    change_type: InventoryChangeType,
    source_type: InventoryLogSourceType,
    quantity_changed: int,
    performed_by: uuid.UUID,
    reference_id: uuid.UUID | None = None,
    reason: str | None = None,
    notes: str | None = None,
) -> None:
    ts = _now()
    log = InventoryLog(
        inventory_id=inventory_id,
        change_type=change_type,
        source_type=source_type,
        reference_id=reference_id,
        quantity_changed=quantity_changed,
        reason=reason,
        notes=notes,
        performed_by=performed_by,
        created_at=ts,
        updated_at=ts,
    )
    db.add(log)


def add_or_restock_inventory(
    db: Session,
    *,
    store_id: uuid.UUID,
    batch_id: uuid.UUID,
    quantity: int,
    performed_by: uuid.UUID,
) -> Inventory:
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="quantity must be positive")

    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    product = db.get(Product, batch.product_id)
    if product is None or product.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    stmt = (
        select(Inventory)
        .where(Inventory.store_id == store_id, Inventory.batch_id == batch_id)
        .with_for_update()
    )
    inv = db.execute(stmt).scalar_one_or_none()
    ts = _now()

    if inv is None:
        try:
            with db.begin_nested():
                inv = Inventory(
                    store_id=store_id,
                    product_id=batch.product_id,
                    batch_id=batch_id,
                    quantity=quantity,
                    reserved_quantity=0,
                    reorder_threshold=None,
                    last_restocked_at=ts,
                    created_at=ts,
                    updated_at=ts,
                )
                db.add(inv)
                db.flush()
        except IntegrityError:
            stmt = (
                select(Inventory)
                .where(Inventory.store_id == store_id, Inventory.batch_id == batch_id)
                .with_for_update()
            )
            inv = db.execute(stmt).scalar_one()
            inv.quantity += quantity
            inv.last_restocked_at = ts
    else:
        inv.quantity += quantity
        inv.last_restocked_at = ts

    _append_inventory_log(
        db,
        inventory_id=inv.id,
        change_type=InventoryChangeType.ADD,
        source_type=InventoryLogSourceType.RESTOCK,
        quantity_changed=quantity,
        performed_by=performed_by,
    )
    db.commit()
    db.refresh(inv)
    return inv


def reduce_inventory_for_sale(
    db: Session,
    *,
    store_id: uuid.UUID,
    batch_id: uuid.UUID,
    quantity: int,
    performed_by: uuid.UUID,
    reference_id: uuid.UUID | None = None,
) -> Inventory:
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="quantity must be positive")

    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    stmt = (
        select(Inventory)
        .where(Inventory.store_id == store_id, Inventory.batch_id == batch_id)
        .with_for_update()
    )
    inv = db.execute(stmt).scalar_one_or_none()
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No inventory for this store and batch",
        )

    if inv.quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock for this batch at this store",
        )

    inv.quantity -= quantity

    _append_inventory_log(
        db,
        inventory_id=inv.id,
        change_type=InventoryChangeType.REMOVE,
        source_type=InventoryLogSourceType.SALE,
        quantity_changed=quantity,
        performed_by=performed_by,
        reference_id=reference_id,
    )
    db.commit()
    db.refresh(inv)
    return inv


def list_inventory_rows(
    db: Session,
    *,
    store_id: uuid.UUID | None,
    product_id: uuid.UUID | None,
) -> list[InventoryRowPublic]:
    q = (
        select(Inventory, Product, Batch)
        .join(Product, Inventory.product_id == Product.id)
        .join(Batch, Inventory.batch_id == Batch.id)
        .where(Product.is_deleted.is_(False))
    )
    if store_id is not None:
        q = q.where(Inventory.store_id == store_id)
    if product_id is not None:
        q = q.where(Inventory.product_id == product_id)

    rows = db.execute(q).all()
    out: list[InventoryRowPublic] = []
    for inv, prod, bat in rows:
        out.append(
            InventoryRowPublic(
                inventory_id=inv.id,
                store_id=inv.store_id,
                product=ProductPublic.model_validate(prod),
                batch=BatchPublic.model_validate(bat),
                quantity=inv.quantity,
                reserved_quantity=inv.reserved_quantity,
                reorder_threshold=inv.reorder_threshold,
                last_restocked_at=inv.last_restocked_at,
            )
        )
    return out


def compute_alerts(db: Session, *, store_id: uuid.UUID | None, expiry_days: int) -> AlertsResponse:
    today = date.today()
    window_end = today + timedelta(days=expiry_days)

    low_q = (
        select(Inventory, Product, Batch, Store)
        .join(Product, Inventory.product_id == Product.id)
        .join(Batch, Inventory.batch_id == Batch.id)
        .join(Store, Inventory.store_id == Store.id)
        .where(Product.is_deleted.is_(False))
        .where(Inventory.reorder_threshold.isnot(None))
        .where(Inventory.quantity < Inventory.reorder_threshold)
    )
    if store_id is not None:
        low_q = low_q.where(Inventory.store_id == store_id)

    low_stock: list[AlertItem] = []
    for inv, prod, bat, sto in db.execute(low_q).all():
        low_stock.append(
            AlertItem(
                alert_type=AlertType.LOW_STOCK.value,
                severity=AlertSeverity.MEDIUM.value,
                store_id=sto.id,
                product_id=prod.id,
                product_name=prod.name,
                batch_id=bat.id,
                batch_number=bat.batch_number,
                expiry_date=bat.expiry_date,
                quantity=inv.quantity,
                reorder_threshold=inv.reorder_threshold,
                message=f"On-hand {inv.quantity} is below reorder threshold {inv.reorder_threshold}",
                trigger_value=float(inv.quantity),
                threshold_value=float(inv.reorder_threshold) if inv.reorder_threshold is not None else None,
            )
        )

    exp_q = (
        select(Inventory, Product, Batch, Store)
        .join(Product, Inventory.product_id == Product.id)
        .join(Batch, Inventory.batch_id == Batch.id)
        .join(Store, Inventory.store_id == Store.id)
        .where(Product.is_deleted.is_(False))
        .where(Batch.expiry_date <= window_end)
        .where(Inventory.quantity > 0)
    )
    if store_id is not None:
        exp_q = exp_q.where(Inventory.store_id == store_id)

    expiry_items: list[AlertItem] = []
    for inv, prod, bat, sto in db.execute(exp_q).all():
        if bat.expiry_date < today:
            sev = AlertSeverity.HIGH.value
            msg = f"Batch expired on {bat.expiry_date} with {inv.quantity} units on hand"
        elif bat.expiry_date <= window_end:
            sev = AlertSeverity.MEDIUM.value
            days_left = (bat.expiry_date - today).days
            msg = f"Expires on {bat.expiry_date} ({days_left} day(s)); {inv.quantity} units on hand"
        else:
            continue
        expiry_items.append(
            AlertItem(
                alert_type=AlertType.EXPIRY.value,
                severity=sev,
                store_id=sto.id,
                product_id=prod.id,
                product_name=prod.name,
                batch_id=bat.id,
                batch_number=bat.batch_number,
                expiry_date=bat.expiry_date,
                quantity=inv.quantity,
                reorder_threshold=inv.reorder_threshold,
                message=msg,
                trigger_value=float((bat.expiry_date - today).days),
                threshold_value=float(expiry_days),
            )
        )

    return AlertsResponse(low_stock=low_stock, expiry=expiry_items)
