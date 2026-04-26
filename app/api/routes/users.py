import uuid
import ipaddress
import logging

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
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

logger = logging.getLogger(__name__)


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

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Password cannot be empty")
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


def _get_client_ip(request: Request) -> str:
    # Behind Railway/reverse proxies, request.client.host is typically the proxy.
    # Prefer forwarded headers so the limiter key is per real client.
    def _clean_ip(value: str) -> str:
        v = value.strip().strip('"')
        # Strip IPv6 bracket form: "[2001:db8::1]"
        if v.startswith("[") and v.endswith("]"):
            v = v[1:-1]
        # Strip optional port (ipv4:port). IPv6 ports are rare here and already bracketed.
        if ":" in v and v.count(":") == 1 and "]" not in v:
            v = v.split(":", 1)[0]
        return v

    def _is_public_ip(value: str) -> bool:
        try:
            ip = ipaddress.ip_address(value)
        except ValueError:
            return False
        return ip.is_global

    # Common client-IP headers used by CDNs/proxies.
    for header in (
        "CF-Connecting-IP",
        "True-Client-IP",
        "Fly-Client-IP",
        "X-Client-IP",
        "X-Real-IP",
    ):
        v = request.headers.get(header)
        if v:
            ip = _clean_ip(v)
            if ip:
                return ip

    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # Prefer the first public IP; fall back to the first entry.
        parts = [_clean_ip(p) for p in xff.split(",")]
        parts = [p for p in parts if p]
        for p in parts:
            if _is_public_ip(p):
                return p
        if parts:
            return parts[0]

    forwarded = request.headers.get("Forwarded")
    if forwarded:
        # Forwarded: for=1.2.3.4;proto=https;host=..., for=...
        for entry in forwarded.split(","):
            for part in entry.split(";"):
                part = part.strip()
                if part.lower().startswith("for="):
                    ip = _clean_ip(part[4:])
                    if ip:
                        return ip

    if request.client:
        return request.client.host

    return "unknown"


async def admin_login_identifier(request: Request) -> str:
    ip = _get_client_ip(request)
    return f"{ip}:admin-login"


async def default_callback(request: Request, response: Response):
    # Log enough to debug proxy/IP issues without exposing credentials.
    ip = _get_client_ip(request)
    logger.warning(
        "Rate limit hit on /users/login ip=%s xff=%s xri=%s cf=%s",
        ip,
        request.headers.get("X-Forwarded-For"),
        request.headers.get("X-Real-IP"),
        request.headers.get("CF-Connecting-IP"),
    )
    raise HTTPException(
        status_code=429,
        detail="Muchas solicitudes. Por favor, inténtalo de nuevo en 10 minutos.",
        headers={
            "Retry-After": "600",
            # Helps debug proxy/IP issues from the browser Network tab.
            "X-RateLimit-Client-IP": ip,
        },
    )

# ---- Endpoints ----


@router.post(
    "/login",
    dependencies=[
        Depends(
            RateLimiter(
                limiter=Limiter(Rate(3, Duration.MINUTE * 10)),
                identifier=admin_login_identifier,
                callback=default_callback,
            )
        )
    ],
)
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
