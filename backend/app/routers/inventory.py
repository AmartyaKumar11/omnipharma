from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.rbac import require_admin, require_inventory_mutator, require_inventory_reader
from app.models.user import User
from app.schemas.inventory import (
    AlertsResponse,
    BatchCreate,
    BatchPublic,
    InventoryAdjustRequest,
    InventoryLogRow,
    InventoryRowPublic,
    ProductCreate,
    ProductPublic,
    StockMutation,
    StockReduce,
)
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/product", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
def create_product(
    body: ProductCreate,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_inventory_mutator)],
) -> ProductPublic:
    p = inventory_service.create_product(
        db,
        name=body.name,
        generic_name=body.generic_name,
        category=body.category,
        manufacturer=body.manufacturer,
        description=body.description,
        is_prescription_required=body.is_prescription_required,
    )
    return ProductPublic.model_validate(p)


@router.post("/batch", response_model=BatchPublic, status_code=status.HTTP_201_CREATED)
def create_batch(
    body: BatchCreate,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_inventory_mutator)],
) -> BatchPublic:
    b = inventory_service.create_batch(
        db,
        product_id=body.product_id,
        batch_number=body.batch_number,
        expiry_date=body.expiry_date,
        manufacture_date=body.manufacture_date,
        purchase_price=body.purchase_price,
        selling_price=body.selling_price,
    )
    return BatchPublic.model_validate(b)


@router.post("/stock", response_model=dict)
def add_stock(
    body: StockMutation,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_inventory_mutator)],
) -> dict[str, str]:
    inv = inventory_service.add_or_restock_inventory(
        db,
        store_id=body.store_id,
        batch_id=body.batch_id,
        quantity=body.quantity,
        performed_by=user.id,
    )
    return {"status": "ok", "inventory_id": str(inv.id)}


@router.post("/reduce", response_model=dict)
def reduce_stock(
    body: StockReduce,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_inventory_mutator)],
) -> dict[str, str]:
    inv = inventory_service.reduce_inventory_for_sale(
        db,
        store_id=body.store_id,
        batch_id=body.batch_id,
        quantity=body.quantity,
        performed_by=user.id,
        reference_id=None,
    )
    return {"status": "ok", "inventory_id": str(inv.id)}


@router.post("/adjust", response_model=dict)
def adjust_inventory(
    body: InventoryAdjustRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_inventory_mutator)],
) -> dict[str, str]:
    inv = inventory_service.adjust_inventory(
        db,
        store_id=body.store_id,
        batch_id=body.batch_id,
        quantity_delta=body.quantity_delta,
        reason=body.reason,
        performed_by=user.id,
    )
    return {"status": "ok", "inventory_id": str(inv.id)}


@router.get("/logs", response_model=list[InventoryLogRow])
def inventory_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_admin)],
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[InventoryLogRow]:
    return inventory_service.list_inventory_audit_logs(db, limit=limit)


@router.get("", response_model=list[InventoryRowPublic])
def list_inventory(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_inventory_reader)],
    store_id: Annotated[UUID | None, Query()] = None,
    product_id: Annotated[UUID | None, Query()] = None,
    sort_by: Annotated[str | None, Query()] = None,
    sort_dir: Annotated[str, Query()] = "asc",
) -> list[InventoryRowPublic]:
    return inventory_service.list_inventory_rows(
        db,
        store_id=store_id,
        product_id=product_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/alerts", response_model=AlertsResponse)
def inventory_alerts(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_inventory_reader)],
    store_id: Annotated[UUID | None, Query()] = None,
    expiry_days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> AlertsResponse:
    return inventory_service.compute_alerts(db, store_id=store_id, expiry_days=expiry_days)
