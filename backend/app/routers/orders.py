from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.rbac import require_order_creator, require_order_reader
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.order import OrderCreate, OrderOut
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    body: OrderCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_order_creator)],
) -> OrderOut:
    if user.role != UserRole.ADMIN:
        body = body.model_copy(update={"store_id": user.store_id})
    return order_service.create_order(db, body=body, user_id=user.id)


@router.get("", response_model=list[OrderOut])
def list_orders(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_order_reader)],
    store_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[OrderOut]:
    if _user.role != UserRole.ADMIN:
        store_id = _user.store_id
    return order_service.list_orders(db, store_id=store_id, date_from=date_from, date_to=date_to)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_order_reader)],
) -> OrderOut:
    out = order_service.get_order_detail(db, order_id=order_id)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if _user.role != UserRole.ADMIN and out.store_id != _user.store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this order")
    return out
