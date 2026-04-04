from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import OrderType, PaymentMethod


class OrderLineIn(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    store_id: UUID
    items: list[OrderLineIn] = Field(min_length=1)
    payment_method: PaymentMethod
    order_type: OrderType = OrderType.OTC
    prescription_file_url: str | None = None
    doctor_name: str | None = None
    prescription_notes: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def prescription_requires_file(self):
        if self.order_type == OrderType.PRESCRIPTION:
            if not self.prescription_file_url or not str(self.prescription_file_url).strip():
                raise ValueError("prescription_file_url is required for PRESCRIPTION orders")
        return self


class OrderItemOut(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    batch_id: UUID
    batch_number: str
    quantity: int
    price_at_sale: Decimal
    line_total: Decimal


class OrderOut(BaseModel):
    id: UUID
    order_number: str
    store_id: UUID
    user_id: UUID
    order_type: str
    status: str
    total_amount: Decimal
    payment_method: str
    notes: str | None
    created_at: datetime
    items: list[OrderItemOut]


class OrderListItem(BaseModel):
    id: UUID
    order_number: str
    store_id: UUID
    user_id: UUID
    order_type: str
    status: str
    total_amount: Decimal
    payment_method: str
    created_at: datetime
    item_count: int
