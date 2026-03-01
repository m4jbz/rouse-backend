import uuid

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlmodel import Session, select

from app.core.db import get_db
from app.core.deps import get_current_client
from app.core.email import send_password_reset_email, send_verification_email
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_email_verification_token,
    decode_password_reset_token,
    decode_refresh_token,
)
from app.models import Client, ClientCartItem

router = APIRouter(prefix="/clients", tags=["clients"])


# ---------- Schemas ----------


class RegisterClient(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: PhoneNumber

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class LoginClient(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class ResendVerificationRequest(BaseModel):
    email: EmailStr


# ---------- Endpoints ----------


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(client: RegisterClient, db: Session = Depends(get_db)):
    # Check for duplicate email
    existing = db.exec(
        select(Client).where(Client.email == client.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    password_bytes = client.password.encode("utf-8")
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    new_client = Client(
        email=client.email,
        name=client.name,
        phone=str(client.phone),
        password_hash=password_hash,
        is_verified=False,
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    # Send verification email
    token = create_email_verification_token(new_client.id)
    email_sent = send_verification_email(str(new_client.email), new_client.name, token)

    message = (
        "Registro exitoso. Revisa tu correo para verificar tu cuenta."
        if email_sent
        else "Registro exitoso, pero no pudimos enviar el correo de verificación. "
             "Usa la opción de reenviar verificación."
    )

    return {
        "message": message,
        "client_id": str(new_client.id),
    }


@router.post("/login")
def login(data: LoginClient, db: Session = Depends(get_db)):
    """Login a client. Returns access and refresh tokens."""
    client = db.exec(
        select(Client).where(Client.email == data.email)
    ).first()
    if not client:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Check password
    password_bytes = data.password.encode("utf-8")
    if not bcrypt.checkpw(password_bytes, client.password_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Check email verification
    if not client.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Debes verificar tu correo electrónico antes de iniciar sesión.",
        )

    access_token = create_access_token(client.id)
    refresh_token = create_refresh_token(client.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(client.id),
            "email": str(client.email),
            "name": client.name,
            "phone": str(client.phone),
            "created_at": client.created_at.isoformat(),
        },
    }


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify the client's email address using the token from the email link."""
    try:
        payload = decode_email_verification_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="El enlace de verificación ha expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Enlace de verificación inválido.")

    client_id = payload.get("sub")
    client = db.exec(
        select(Client).where(Client.id == uuid.UUID(client_id))
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    if client.is_verified:
        return {"message": "Tu cuenta ya está verificada."}

    client.is_verified = True
    db.add(client)
    db.commit()

    return {"message": "Correo verificado exitosamente. Ya puedes iniciar sesión."}


@router.post("/resend-verification")
def resend_verification(data: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend the verification email if the client hasn't verified yet."""
    client = db.exec(
        select(Client).where(Client.email == data.email)
    ).first()

    # Always return success to avoid email enumeration
    if not client or client.is_verified:
        return {"message": "Si el correo está registrado y no verificado, recibirás un enlace."}

    token = create_email_verification_token(client.id)
    send_verification_email(str(client.email), client.name, token)

    return {"message": "Correo de verificación enviado. Revisa tu bandeja de entrada."}


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send a password reset email. Always returns success to avoid email enumeration."""
    client = db.exec(
        select(Client).where(Client.email == data.email)
    ).first()

    # Always return the same message regardless of whether the email exists
    if client:
        token = create_password_reset_token(client.id)
        send_password_reset_email(str(client.email), client.name, token)

    return {"message": "Si el correo está registrado, recibirás un enlace para restablecer tu contraseña."}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset the client's password using the token from the email link."""
    try:
        payload = decode_password_reset_token(data.token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="El enlace ha expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Enlace inválido.")

    client_id = payload.get("sub")
    client = db.exec(
        select(Client).where(Client.id == uuid.UUID(client_id))
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    # Hash new password
    password_bytes = data.new_password.encode("utf-8")
    salt = bcrypt.gensalt()
    client.password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    db.add(client)
    db.commit()

    return {"message": "Contraseña restablecida exitosamente."}


@router.post("/refresh")
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Get a new access token using a valid refresh token."""
    try:
        payload = decode_refresh_token(data.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Refresh token inválido.")

    client_id = payload.get("sub")
    client = db.exec(
        select(Client).where(Client.id == uuid.UUID(client_id))
    ).first()

    if not client:
        raise HTTPException(status_code=401, detail="Cliente no encontrado.")

    new_access_token = create_access_token(client.id)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.get("/me")
def get_me(client: Client = Depends(get_current_client)):
    """Get the current authenticated client's profile."""
    return {
        "id": str(client.id),
        "email": str(client.email),
        "name": client.name,
        "phone": str(client.phone),
        "created_at": client.created_at.isoformat(),
    }


# ---------- Cart schemas ----------


class CartItemData(BaseModel):
    product_id: str
    product_name: str
    product_price: float
    product_image: str
    product_badge: str | None = None
    quantity: int


class CartSyncRequest(BaseModel):
    items: list[CartItemData]


# ---------- Cart endpoints ----------


@router.get("/cart")
def get_cart(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Get the authenticated client's saved cart."""
    rows = db.exec(
        select(ClientCartItem).where(ClientCartItem.client_id == client.id)
    ).all()

    return {
        "items": [
            {
                "product_id": r.product_id,
                "product_name": r.product_name,
                "product_price": r.product_price,
                "product_image": r.product_image,
                "product_badge": r.product_badge,
                "quantity": r.quantity,
            }
            for r in rows
        ]
    }


@router.put("/cart")
def sync_cart(
    data: CartSyncRequest,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Replace the client's entire cart with the provided items."""
    # Delete existing cart items
    existing = db.exec(
        select(ClientCartItem).where(ClientCartItem.client_id == client.id)
    ).all()
    for item in existing:
        db.delete(item)

    # Insert new items
    for item_data in data.items:
        cart_item = ClientCartItem(
            client_id=client.id,
            product_id=item_data.product_id,
            product_name=item_data.product_name,
            product_price=item_data.product_price,
            product_image=item_data.product_image,
            product_badge=item_data.product_badge,
            quantity=item_data.quantity,
        )
        db.add(cart_item)

    db.commit()
    return {"message": "Carrito actualizado."}


@router.delete("/cart")
def clear_server_cart(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Clear the client's saved cart."""
    existing = db.exec(
        select(ClientCartItem).where(ClientCartItem.client_id == client.id)
    ).all()
    for item in existing:
        db.delete(item)
    db.commit()
    return {"message": "Carrito vaciado."}
