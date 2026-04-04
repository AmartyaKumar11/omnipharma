import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
