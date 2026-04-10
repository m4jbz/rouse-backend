import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from sqlmodel import Session, select

from app.core.db import get_db
from app.core.deps import get_current_user, get_current_client_optional
from app.models import CustomCakeRequest, CustomCakeRequestStatus, Client, User

router = APIRouter(prefix="/custom-cake-requests", tags=["custom-cake-requests"])


# ============================================================
# Schemas
# ============================================================

class CustomCakeRequestCreate(BaseModel):
    client_name: str
    client_email: EmailStr
    client_phone: str
    cake_size: str  # 'chico' | 'mediano' | 'grande'
    cake_layers: int = 1
    cake_flavor: str
    filling: str | None = None
    topping: str | None = None
    custom_text: str | None = None
    reference_images: list[str] | None = None
    delivery_date: date
    delivery_time: str | None = None
    additional_notes: str | None = None

    @field_validator("client_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Client name cannot be empty")
        return v.strip()

    @field_validator("cake_size")
    @classmethod
    def size_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("chico", "mediano", "grande"):
            raise ValueError("Size must be 'chico', 'mediano' or 'grande'")
        return v

    @field_validator("cake_layers")
    @classmethod
    def layers_valid(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Layers must be between 1 and 5")
        return v

    @field_validator("delivery_date")
    @classmethod
    def date_in_future(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Delivery date must be in the future")
        return v


class CustomCakeRequestUpdate(BaseModel):
    """For admin to update status and quote."""
    status: CustomCakeRequestStatus | None = None
    quoted_price: Decimal | None = None
    admin_notes: str | None = None


class CustomCakeRequestPublic(BaseModel):
    id: int
    client_id: uuid.UUID | None
    client_name: str
    client_email: str
    client_phone: str
    cake_size: str
    cake_layers: int
    cake_flavor: str
    filling: str | None
    topping: str | None
    custom_text: str | None
    reference_images: list[str] | None
    delivery_date: date
    delivery_time: str | None
    additional_notes: str | None
    status: CustomCakeRequestStatus
    quoted_price: Decimal | None
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime


# ============================================================
# Public endpoints (client-facing)
# ============================================================

@router.post("/", response_model=CustomCakeRequestPublic, status_code=201)
def create_custom_cake_request(
    data: CustomCakeRequestCreate,
    db: Session = Depends(get_db),
    client: Client | None = Depends(get_current_client_optional),
):
    """
    Create a new custom cake request.
    If the user is logged in as a client, associate the request with them.
    """
    request = CustomCakeRequest(
        client_id=client.id if client else None,
        client_name=data.client_name,
        client_email=data.client_email,
        client_phone=data.client_phone,
        cake_size=data.cake_size,
        cake_layers=data.cake_layers,
        cake_flavor=data.cake_flavor,
        filling=data.filling,
        topping=data.topping,
        custom_text=data.custom_text,
        reference_images=data.reference_images,
        delivery_date=data.delivery_date,
        delivery_time=data.delivery_time,
        additional_notes=data.additional_notes,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.get("/my-requests", response_model=list[CustomCakeRequestPublic])
def list_my_requests(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_client_optional),
):
    """List all custom cake requests for the logged-in client."""
    if not client:
        raise HTTPException(status_code=401, detail="Not authenticated")

    requests = db.exec(
        select(CustomCakeRequest)
        .where(CustomCakeRequest.client_id == client.id)
        .order_by(CustomCakeRequest.created_at.desc())
    ).all()
    return requests


# ============================================================
# Admin endpoints
# ============================================================

@router.get("/", response_model=list[CustomCakeRequestPublic])
def list_all_requests(
    status: CustomCakeRequestStatus | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List all custom cake requests (admin only)."""
    query = select(CustomCakeRequest).order_by(CustomCakeRequest.created_at.desc())
    if status:
        query = query.where(CustomCakeRequest.status == status)
    return db.exec(query).all()


@router.get("/{request_id}", response_model=CustomCakeRequestPublic)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get a specific custom cake request (admin only)."""
    request = db.get(CustomCakeRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@router.patch("/{request_id}", response_model=CustomCakeRequestPublic)
def update_request(
    request_id: int,
    data: CustomCakeRequestUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Update a custom cake request (admin only)."""
    request = db.get(CustomCakeRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        request.sqlmodel_update(update_data)
        db.add(request)
        db.commit()
        db.refresh(request)

    return request


@router.delete("/{request_id}", status_code=204)
def delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Delete a custom cake request (admin only)."""
    request = db.get(CustomCakeRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    db.delete(request)
    db.commit()
