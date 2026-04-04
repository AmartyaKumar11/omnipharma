from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.enums import OrderStatus
from app.models.order import Order
from app.models.product import Product
from app.models.stock import Inventory
from app.models.store import Store
from app.schemas.dashboard import DashboardSummary, SalesTrendPoint, StorePerformanceRow


def _utc_bounds(d_from: date | None, d_to: date | None) -> tuple[datetime | None, datetime | None]:
    start = datetime.combine(d_from, time.min, tzinfo=timezone.utc) if d_from else None
    end = datetime.combine(d_to, time.max, tzinfo=timezone.utc) if d_to else None
    return start, end


def get_summary(
    db: Session,
    *,
    store_id: uuid.UUID | None,
    date_from: date | None,
    date_to: date | None,
) -> DashboardSummary:
    """Aggregated KPIs using SQL; inventory counts respect optional store filter."""
    start, end = _utc_bounds(date_from, date_to)

    order_filters = [Order.status == OrderStatus.COMPLETED]
    if store_id is not None:
        order_filters.append(Order.store_id == store_id)
    if start is not None:
        order_filters.append(Order.created_at >= start)
    if end is not None:
        order_filters.append(Order.created_at <= end)

    agg = db.execute(
        select(
            func.coalesce(func.sum(Order.total_amount), 0),
            func.count(Order.id),
        ).where(and_(*order_filters))
    ).one()
    total_sales_dec: Decimal = agg[0]
    total_orders: int = int(agg[1])
    total_sales = float(total_sales_dec)
    average_order_value = (total_sales / total_orders) if total_orders else 0.0

    low_q = select(func.count()).select_from(Inventory).join(Product, Inventory.product_id == Product.id)
    low_q = low_q.where(
        Product.is_deleted.is_(False),
        Inventory.reorder_threshold.isnot(None),
        Inventory.quantity < Inventory.reorder_threshold,
    )
    if store_id is not None:
        low_q = low_q.where(Inventory.store_id == store_id)
    low_stock_count = int(db.scalar(low_q) or 0)

    today = datetime.now(timezone.utc).date()
    horizon = today + timedelta(days=30)
    exp_q = (
        select(func.count())
        .select_from(Inventory)
        .join(Batch, Inventory.batch_id == Batch.id)
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Product.is_deleted.is_(False),
            Inventory.quantity > 0,
            Batch.expiry_date >= today,
            Batch.expiry_date <= horizon,
        )
    )
    if store_id is not None:
        exp_q = exp_q.where(Inventory.store_id == store_id)
    expiring_soon_count = int(db.scalar(exp_q) or 0)

    return DashboardSummary(
        total_sales=total_sales,
        total_orders=total_orders,
        average_order_value=round(average_order_value, 2),
        low_stock_count=low_stock_count,
        expiring_soon_count=expiring_soon_count,
    )


def get_sales_trend(
    db: Session,
    *,
    store_id: uuid.UUID,
    date_from: date,
    date_to: date,
) -> list[SalesTrendPoint]:
    start, end = _utc_bounds(date_from, date_to)
    assert start and end

    day_bucket = func.date_trunc("day", Order.created_at).label("day")

    q = (
        select(day_bucket, func.coalesce(func.sum(Order.total_amount), 0))
        .where(
            Order.status == OrderStatus.COMPLETED,
            Order.store_id == store_id,
            Order.created_at >= start,
            Order.created_at <= end,
        )
        .group_by(day_bucket)
        .order_by(day_bucket)
    )

    rows = db.execute(q).all()
    out: list[SalesTrendPoint] = []
    for day_val, sales_dec in rows:
        d = day_val.date() if hasattr(day_val, "date") else day_val
        if isinstance(d, datetime):
            d = d.date()
        out.append(
            SalesTrendPoint(
                date=d.isoformat(),
                sales=float(sales_dec or 0),
            )
        )
    return out


def get_store_performance(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
) -> list[StorePerformanceRow]:
    start, end = _utc_bounds(date_from, date_to)

    filters = [Order.status == OrderStatus.COMPLETED]
    if start is not None:
        filters.append(Order.created_at >= start)
    if end is not None:
        filters.append(Order.created_at <= end)

    q = (
        select(
            Store.id,
            Store.name,
            func.coalesce(func.sum(Order.total_amount), 0),
            func.count(Order.id),
        )
        .join(Order, Order.store_id == Store.id)
        .where(and_(*filters))
        .group_by(Store.id, Store.name)
        .order_by(func.coalesce(func.sum(Order.total_amount), 0).desc())
    )

    rows = db.execute(q).all()
    return [
        StorePerformanceRow(
            store_id=r[0],
            store_name=r[1],
            total_sales=float(r[2] or 0),
            order_count=int(r[3] or 0),
        )
        for r in rows
    ]
