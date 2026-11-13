from datetime import datetime
from typing import Literal
import uuid

from pydantic import BaseModel, Field


Role = Literal["admin", "operator"]
MovementType = Literal["entrada", "saida", "ajuste"]


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: Role
    last_access: datetime | None = None


class ProductBase(BaseModel):
    sku: str
    name: str
    category: str
    unit_cost: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    stock: int = Field(ge=0)
    min_stock: int = Field(ge=0)
    reorder_point: int = Field(ge=0)
    supplier: str = "Fornecedor não informado"


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MovementCreate(BaseModel):
    product_id: str
    type: MovementType
    quantity: int = Field(gt=0)
    reason: str = "Registro manual"


class Movement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_sku: str
    product_name: str
    type: MovementType
    quantity: int
    reason: str
    user_name: str
    user_role: Role
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ForecastItem(BaseModel):
    product_id: str
    sku: str
    name: str
    category: str
    stock: int
    avg_daily_demand: float
    forecast_days: int
    forecast_demand: int
    days_of_stock: int | None
    reorder_quantity: int
    estimated_cost: float
    priority: Literal["Urgente", "Normal", "Baixa"]
    status: Literal["Crítico", "Baixo", "Saudável", "Excesso"]


class ForecastResponse(BaseModel):
    days: int
    model_name: str
    generated_at: datetime
    items: list[ForecastItem]


class DashboardResponse(BaseModel):
    total_inventory_value: float
    total_products: int
    critical_stock_count: int
    forecast_shortage_count: int
    turnover_rate: float
    stock_distribution: dict[str, int]
    category_summary: list[dict[str, str | int | float]]
    demand_series: list[dict[str, str | int]]
    critical_products: list[ForecastItem]
    recent_movements: list[Movement]
    as_of_date: str


class ImportProductsRequest(BaseModel):
    products: list[ProductCreate]


class ImportProductsResponse(BaseModel):
    imported: int
    updated: int
    errors: list[str]


class SupplierAlertProduct(BaseModel):
    product_id: str
    sku: str
    name: str
    stock: int
    reorder_point: int
    min_stock: int
    suggested_quantity: int
    estimated_cost: float
    priority: Literal["Urgente", "Normal"]


class SupplierAlert(BaseModel):
    supplier: str
    product_count: int
    urgent_count: int
    total_estimated_cost: float
    products: list[SupplierAlertProduct]