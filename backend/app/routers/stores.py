from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.store import Store

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("")
def list_stores(db: Session = Depends(get_db)):
    """Public endpoint to fetch stores for the signup dropdown."""
    stores = db.scalars(select(Store).where(Store.is_active == True).order_by(Store.name)).all()
    return [{"id": str(s.id), "name": s.name} for s in stores]
