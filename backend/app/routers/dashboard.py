from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.rbac import require_dashboard_analytics, require_dashboard_summary
from app.models.user import User
from app.models.enums import UserRole
from app.models.store import Store
from app.schemas.dashboard import DashboardSummary, SalesTrendPoint, StoreBrief, StorePerformanceRow
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_dashboard_summary)],
    store_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> DashboardSummary:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date_from must be <= date_to")
    if _user.role != UserRole.ADMIN:
        store_id = _user.store_id
    return dashboard_service.get_summary(db, store_id=store_id, date_from=date_from, date_to=date_to)


@router.get("/sales-trend", response_model=list[SalesTrendPoint])
def sales_trend(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_dashboard_analytics)],
    store_id: Annotated[UUID, Query()],
    date_from: Annotated[date, Query()],
    date_to: Annotated[date, Query()],
) -> list[SalesTrendPoint]:
    if date_from > date_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date_from must be <= date_to")
    if _user.role != UserRole.ADMIN:
        store_id = _user.store_id
    return dashboard_service.get_sales_trend(db, store_id=store_id, date_from=date_from, date_to=date_to)


@router.get("/store-performance", response_model=list[StorePerformanceRow])
def store_performance(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_dashboard_analytics)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[StorePerformanceRow]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date_from must be <= date_to")
    if _user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Store performance comparison requires ADMIN role")
    return dashboard_service.get_store_performance(db, date_from=date_from, date_to=date_to)


@router.get("/stores", response_model=list[StoreBrief])
def list_stores_for_filters(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_dashboard_analytics)],
) -> list[StoreBrief]:
    if _user.role != UserRole.ADMIN:
        rows = db.scalars(select(Store).where(Store.id == _user.store_id)).all()
    else:
        rows = db.scalars(select(Store).where(Store.is_active.is_(True)).order_by(Store.name.asc())).all()
    return [StoreBrief.model_validate(s) for s in rows]
