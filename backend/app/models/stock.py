import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import InventoryChangeType, InventoryLogSourceType


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("products.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_restocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("inventory.id"), nullable=False)
    change_type: Mapped[InventoryChangeType] = mapped_column(
        Enum(
            InventoryChangeType,
            name="inventory_change_type",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    source_type: Mapped[InventoryLogSourceType] = mapped_column(
        Enum(
            InventoryLogSourceType,
            name="inventory_log_source_type",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    quantity_changed: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
