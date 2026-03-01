import uuid

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_admin_access_token,
    create_admin_refresh_token,
    decode_admin_refresh_token,
)
from app.models import User
from pyrate_limiter import Duration, Limiter, Rate
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/users", tags=["users"])


# ---- Request / response schemas ----


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class UserPublic(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool

def default_callback(*args, **kwargs):
    raise HTTPException(status_code=429, detail="Muchas solicitudes. Por favor, inténtalo de nuevo más tarde.")

# ---- Endpoints ----


@router.post("/login", dependencies=[Depends(RateLimiter(limiter=Limiter(Rate(3, Duration.MINUTE * 60)), callback=default_callback))])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.exec(select(User).where(User.username == data.username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario desactivado")

    password_bytes = data.password.encode("utf-8")
    if not bcrypt.checkpw(password_bytes, user.password_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access_token = create_admin_access_token(user.id)
    refresh_token = create_admin_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
        },
    }


@router.get("/me", response_model=UserPublic)
def get_me(user: User = Depends(get_current_user)):
    return UserPublic(
        id=str(user.id),
        username=user.username,
        role=user.role,
        is_active=user.is_active,
    )


@router.post("/refresh")
def refresh_token(data: RefreshRequest, db: Session = Depends(get_db)):
    import jwt as pyjwt

    try:
        payload = decode_admin_refresh_token(data.refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.exec(select(User).where(User.id == uuid.UUID(user_id))).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    new_access_token = create_admin_access_token(user.id)
    return {"access_token": new_access_token}
