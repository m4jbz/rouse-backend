import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from app.core.db import get_db
from app.core.deps import get_current_client, get_current_user
from app.models import (
    Client,
    Order,
    OrderDetail,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Product,
    ProductVariant,
    User,
)

router = APIRouter(prefix="/orders", tags=["orders"])
bearer_scheme = HTTPBearer(auto_error=False)

# Estos dos schemas son necesarios para la relación de Orders con OrderDetails
class OrderDetailCreate(BaseModel):
    product_id: int
    variant_name: str
    quantity: int
    unit_price: Decimal

    @field_validator("variant_name")
    @classmethod
    def variant_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Variant name cannot be empty")
        return v.strip()

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("unit_price")
    @classmethod
    def unit_price_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Unit price must be greater than 0")
        return v


class OrderDetailPublic(BaseModel):
    id: int
    product_id: int
    variant_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


# Body de las peticiones para crear y actualizar órdenes
class OrderCreate(BaseModel):
    client_id: uuid.UUID | None = None
    client_name: str
    phone: str
    delivery_address: str | None = None
    payment_method: PaymentMethod
    notes: str | None = None
    details: list[OrderDetailCreate]

    @field_validator("client_name")
    @classmethod
    def client_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Client name cannot be empty")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def phone_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Phone cannot be empty")
        # Strip everything non-digit: "tel:+52-733-136-1624" → "527331361624"
        digits = "".join(c for c in v if c.isdigit())
        # Strip Mexico country code prefix
        if digits.startswith("52") and len(digits) == 12:
            digits = digits[2:]
        if not digits:
            raise ValueError("Phone must contain digits")
        return digits

    @field_validator("delivery_address")
    @classmethod
    def delivery_address_normalize(cls, v: str | None) -> str | None:
        if v is not None and v.strip():
            return v.strip()
        return None


class OrderUpdate(BaseModel):
    status: OrderStatus | None = None
    payment_status: PaymentStatus | None = None
    notes: str | None = None

# Body de la peticion para listar y obtener las órdenes
class OrderPublic(BaseModel):
    id: int
    ticket_number: str
    client_id: uuid.UUID | None
    client_name: str
    phone: str
    delivery_address: str | None
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    notes: str | None
    total: Decimal
    details: list[OrderDetailPublic] = []

# Genera el número de ticket basado en el último ID de órden en la base de datos
def _generate_ticket(db: Session) -> str:
    last = db.exec(select(Order).order_by(Order.id.desc())).first()
    next_num = (last.id + 1) if last else 1
    return f"TK-{next_num:04d}"

@router.get("/my-orders", response_model=list[OrderPublic])
def list_my_orders(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Lista las órdenes del cliente autenticado."""
    query = (
        select(Order)
        .where(Order.client_id == client.id)
        .order_by(Order.id.desc())
    )
    orders = db.exec(query).all()
    return orders


@router.get("/", response_model=list[OrderPublic])
def list_orders(
    status: OrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Busqueda y ordenamiento por id
    query = select(Order).order_by(Order.id.desc())
    # Si el estado de la órden fue proporcionado solo se traen las órdenes con ese estado
    if status is not None:
        query = query.where(Order.status == status)
    # Si el estado del pago fue proporcionado solo se traen las órdenes con ese estado de pago
    if payment_status is not None:
        query = query.where(Order.payment_status == payment_status)
    orders = db.exec(query).all()
    return orders


@router.get("/{order_id}", response_model=OrderPublic)
def get_order(order_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    order = db.get(Order, order_id)
    # Si no se encuentra la órden se devuelve un error 404
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/", response_model=OrderPublic, status_code=201)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    # Debe de tener al menos un detalle
    if not data.details:
        raise HTTPException(
            status_code=400, detail="Order must have at least one detail"
        )

    # Verifica que el client_id exista si fue proporcionado
    if data.client_id is not None:
        client = db.get(Client, data.client_id)
        if not client:
            raise HTTPException(
                status_code=404,
                detail=f"Client {data.client_id} not found",
            )

    # Verifica que todos los productos existan y estén activos
    product_ids = {d.product_id for d in data.details}
    for pid in product_ids:
        product = db.get(Product, pid)
        if not product:
            raise HTTPException(
                status_code=404, detail=f"Product {pid} not found"
            )
        if not product.is_active:
            raise HTTPException(
                status_code=400, detail=f"Product {pid} is not active"
            )

    # Verifica que cada variante exista para su producto y que el unit_price coincida
    for d in data.details:
        variant = db.exec(
            select(ProductVariant).where(
                ProductVariant.product_id == d.product_id,
                ProductVariant.name == d.variant_name,
            )
        ).first()
        if not variant:
            raise HTTPException(
                status_code=404,
                detail=f"Variant '{d.variant_name}' not found for product {d.product_id}",
            )
        if variant.price != d.unit_price:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unit price {d.unit_price} does not match variant "
                    f"'{d.variant_name}' price {variant.price} for product {d.product_id}"
                ),
            )

    # Genera numero de ticket
    ticket = _generate_ticket(db)

    # Calcula subtotales y total en Python (sin stored procedure)
    order_total = Decimal("0")
    detail_objects: list[OrderDetail] = []
    for d in data.details:
        subtotal = d.unit_price * d.quantity
        order_total += subtotal
        detail_objects.append(
            OrderDetail(
                order_id=0,  # se asigna después del flush
                product_id=d.product_id,
                variant_name=d.variant_name,
                quantity=d.quantity,
                unit_price=d.unit_price,
                subtotal=subtotal,
            )
        )

    order = Order(
        ticket_number=ticket,
        client_id=data.client_id,
        client_name=data.client_name,
        phone=data.phone,
        delivery_address=data.delivery_address or "Recoger en tienda",
        payment_method=data.payment_method,
        notes=data.notes,
        total=order_total,
    )
    db.add(order)
    db.flush()

    # Flush permite obtener el ID de la órden sin hacer commit todavía
    for detail in detail_objects:
        detail.order_id = order.id
        db.add(detail)

    db.commit()
    db.refresh(order)
    return order


# Transiciones de estado válidas para las órdenes
VALID_STATUS_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.DELIVERING, OrderStatus.CANCELLED],
    OrderStatus.DELIVERING: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
}


@router.patch("/{order_id}", response_model=OrderPublic)
def update_order(
    order_id: int, data: OrderUpdate, db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Busca si la órden existe
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Valida que la transición de estado sea coherente
    if data.status is not None:
        allowed = VALID_STATUS_TRANSITIONS.get(order.status, [])
        if data.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot transition from '{order.status}' to '{data.status}'. "
                    f"Allowed transitions: {[s.value for s in allowed] if allowed else 'none'}"
                ),
            )

    update_data = data.model_dump(exclude_unset=True)
    order.sqlmodel_update(update_data)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    # Busca si la órden existe
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
