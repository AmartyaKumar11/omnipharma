from uuid import UUID

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    total_sales: float = Field(description="Sum of completed order totals in range")
    total_orders: int
    average_order_value: float
    low_stock_count: int
    expiring_soon_count: int


class SalesTrendPoint(BaseModel):
    date: str
    sales: float


class StorePerformanceRow(BaseModel):
    store_id: UUID
    store_name: str
    total_sales: float
    order_count: int


class StoreBrief(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}
