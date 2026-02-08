import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.db import get_db
from app.models import (
    Order,
    OrderDetail,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Product,
)

router = APIRouter(prefix="/orders", tags=["orders"])

# Estos dos schemas son necesarios para la relación de Orders con OrderDetails
class OrderDetailCreate(BaseModel):
    product_id: int
    variant_name: str
    quantity: int
    unit_price: Decimal


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
    delivery_address: str
    payment_method: PaymentMethod
    notes: str | None = None
    details: list[OrderDetailCreate]


class OrderUpdate(BaseModel):
    payment_status: PaymentStatus | None = None
    notes: str | None = None

# Body de la peticion para listar y obtener las órdenes
class OrderPublic(BaseModel):
    id: int
    ticket_number: str
    client_id: uuid.UUID | None
    client_name: str
    phone: str
    delivery_address: str
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

@router.get("/", response_model=list[OrderPublic])
def list_orders(
    status: OrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    db: Session = Depends(get_db),
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
def get_order(order_id: int, db: Session = Depends(get_db)):
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

    # Verifica que todos los productos existan
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

    # Genera numero de ticket
    ticket = _generate_ticket(db)

    order = Order(
        ticket_number=ticket,
        client_id=data.client_id,
        client_name=data.client_name,
        phone=data.phone,
        delivery_address=data.delivery_address,
        payment_method=data.payment_method,
        notes=data.notes,
        total=Decimal("0"),
    )
    db.add(order)
    db.flush()

    # Flush permite obtener el ID de la órden sin hacer commit todavía,
    # lo cual es necesario para crear los detalles de la órden con el order_id correcto
    for d in data.details:
        detail = OrderDetail(
            order_id=order.id,
            product_id=d.product_id,
            variant_name=d.variant_name,
            quantity=d.quantity,
            unit_price=d.unit_price,
            subtotal=Decimal("0"),
        )
        db.add(detail)

    # Una vez completado lo anterior ahora si puede completar la query
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}", response_model=OrderPublic)
def update_order(
    order_id: int, data: OrderUpdate, db: Session = Depends(get_db)
):
    # Busca si la órden existe
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    update_data = data.model_dump(exclude_unset=True)
    order.sqlmodel_update(update_data)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    # Busca si la órden existe
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
