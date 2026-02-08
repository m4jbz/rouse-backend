import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from pydantic import EmailStr
from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlmodel import Field, Relationship, SQLModel


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"


class OrderStatus(StrEnum):
    PENDING = "pendiente"
    CONFIRMED = "confirmado"
    PREPARING = "preparando"
    DELIVERING = "en_camino"
    DELIVERED = "entregado"
    CANCELLED = "cancelado"


class PaymentStatus(StrEnum):
    PENDING = "pendiente"
    PAID = "pagado"
    REFUNDED = "reembolsado"


class PaymentMethod(StrEnum):
    CASH = "efectivo"
    CARD = "tarjeta"
    TRANSFER = "transferencia"


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = False
    name: str = Field(max_length=255)
    password_hash: str = Field(max_length=255)
    role: Role = Field(default=Role.USER)
    created_at: datetime = Field(default_factory=get_datetime_utc)


class Client(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    name: str = Field(max_length=255)
    phone_number: PhoneNumber = Field(max_length=20)
    password_hash: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=get_datetime_utc)

    orders: list["Order"] = Relationship(back_populates="client")

class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=get_datetime_utc)

    products: list["Product"] = Relationship(back_populates="category")

class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="category.id", index=True)
    name: str = Field(max_length=200)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=get_datetime_utc)

    category: Category = Relationship(back_populates="products")
    variants: list["ProductVariant"] = Relationship(
        back_populates="product", cascade_delete=True
    )

class ProductVariant(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    name: str = Field(max_length=100)
    price: Decimal = Field(max_digits=10, decimal_places=2)
    created_at: datetime = Field(default_factory=get_datetime_utc)

    product: Product = Relationship(back_populates="variants")

class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ticket_number: str = Field(max_length=50, unique=True)
    client_id: uuid.UUID | None = Field(
        default=None, foreign_key="client.id", index=True
    )
    client_name: str = Field(max_length=150)
    phone: str = Field(max_length=20)
    delivery_address: str
    status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)
    payment_method: PaymentMethod
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    notes: str | None = Field(default=None)
    total: Decimal = Field(max_digits=10, decimal_places=2)
    created_at: datetime = Field(default_factory=get_datetime_utc)

    client: Client | None = Relationship(back_populates="orders")
    details: list["OrderDetail"] = Relationship(
        back_populates="order", cascade_delete=True
    )

class OrderDetail(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    variant_name: str = Field(max_length=100)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(max_digits=10, decimal_places=2)
    subtotal: Decimal = Field(max_digits=10, decimal_places=2)

    order: Order = Relationship(back_populates="details")
    product: Product = Relationship()
