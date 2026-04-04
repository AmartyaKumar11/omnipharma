from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=2000)
    generic_name: str | None = None
    category: str | None = None
    manufacturer: str | None = None
    description: str | None = None
    is_prescription_required: bool = False


class ProductPublic(BaseModel):
    id: UUID
    name: str
    generic_name: str | None
    category: str | None
    manufacturer: str | None
    description: str | None
    is_prescription_required: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BatchCreate(BaseModel):
    product_id: UUID
    batch_number: str = Field(min_length=1, max_length=500)
    expiry_date: date
    manufacture_date: date | None = None
    purchase_price: Decimal | None = Field(default=None, ge=0)
    selling_price: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def manufacture_before_expiry(self):
        if self.manufacture_date is not None and self.expiry_date < self.manufacture_date:
            raise ValueError("expiry_date must be >= manufacture_date")
        return self


class BatchPublic(BaseModel):
    id: UUID
    product_id: UUID
    batch_number: str
    expiry_date: date
    manufacture_date: date | None
    purchase_price: Decimal | None
    selling_price: Decimal | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StockMutation(BaseModel):
    store_id: UUID
    batch_id: UUID
    quantity: int = Field(gt=0)


class StockReduce(BaseModel):
    store_id: UUID
    batch_id: UUID
    quantity: int = Field(gt=0)


class InventoryRowPublic(BaseModel):
    inventory_id: UUID
    store_id: UUID
    product: ProductPublic
    batch: BatchPublic
    quantity: int
    reserved_quantity: int
    reorder_threshold: int | None
    last_restocked_at: datetime | None


class AlertItem(BaseModel):
    alert_type: str
    severity: str
    store_id: UUID
    product_id: UUID
    product_name: str
    batch_id: UUID
    batch_number: str
    expiry_date: date | None
    quantity: int | None
    reorder_threshold: int | None
    message: str
    trigger_value: float | None = None
    threshold_value: float | None = None


class AlertsResponse(BaseModel):
    low_stock: list[AlertItem]
    expiry: list[AlertItem]


class InventoryAdjustRequest(BaseModel):
    store_id: UUID
    batch_id: UUID
    quantity_delta: int = Field(
        description="Positive adds stock, negative removes (adjustment).",
    )
    reason: str | None = Field(default=None, max_length=2000)


class InventoryLogRow(BaseModel):
    id: UUID
    username: str | None
    change_type: str
    source_type: str
    product_name: str
    batch_number: str
    quantity_changed: int
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
