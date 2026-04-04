import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("products.id"), nullable=False)
    batch_number: Mapped[str] = mapped_column(Text, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    manufacture_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    selling_price: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
