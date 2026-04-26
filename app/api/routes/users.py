import uuid
import ipaddress
import logging
import hashlib
from collections import OrderedDict

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
from pyrate_limiter import Duration, InMemoryBucket, Limiter, Rate, RateItem
from pyrate_limiter.abstracts.bucket import BucketFactory
from pyrate_limiter.clocks import MonotonicClock
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/users", tags=["users"])

logger = logging.getLogger(__name__)


class PerKeyInMemoryBucketFactory(BucketFactory):
    """Create a separate in-memory bucket per key.

    pyrate_limiter's default Limiter(Rate(...)) builds a single InMemoryBucket
    shared across all keys, effectively rate-limiting everyone together.
    """

    def __init__(self, rates: list[Rate], max_buckets: int = 2048):
        self._rates = rates
        self._buckets: "OrderedDict[str, InMemoryBucket]" = OrderedDict()
        self._max_buckets = max_buckets
        self._clock = MonotonicClock()

    def wrap_item(self, name: str, weight: int = 1) -> RateItem:
        return RateItem(name, self._clock.now(), weight=weight)

    def get(self, item: RateItem) -> InMemoryBucket:
        key = item.name
        bucket = self._buckets.get(key)
        if bucket is not None:
            self._buckets.move_to_end(key)
            return bucket

        bucket = InMemoryBucket(self._rates)
        self.schedule_leak(bucket)
        self._buckets[key] = bucket

        # Best-effort cap to avoid unbounded memory usage if keys explode.
        if len(self._buckets) > self._max_buckets:
            _, old_bucket = self._buckets.popitem(last=False)
            try:
                self.dispose(old_bucket)
            except Exception:
                pass

        return bucket


_LOGIN_LIMITER = Limiter(
    PerKeyInMemoryBucketFactory([Rate(3, Duration.MINUTE * 10)], max_buckets=4096)
)


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
    ua = (request.headers.get("User-Agent") or "").strip()
    al = (request.headers.get("Accept-Language") or "").strip()
    fp = hashlib.sha256(f"{ua}|{al}".encode("utf-8")).hexdigest()[:16]
    return f"{ip}:{fp}:admin-login"


async def default_callback(request: Request, response: Response):
    # Log enough to debug proxy/IP issues without exposing credentials.
    ip = _get_client_ip(request)
    ua = (request.headers.get("User-Agent") or "").strip()
    al = (request.headers.get("Accept-Language") or "").strip()
    fp = hashlib.sha256(f"{ua}|{al}".encode("utf-8")).hexdigest()[:16]
    logger.warning(
        "Rate limit hit on /users/login ip=%s fp=%s xff=%s xri=%s cf=%s",
        ip,
        fp,
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
            "X-RateLimit-Client-FP": fp,
        },
    )

# ---- Endpoints ----


@router.post(
    "/login",
    dependencies=[
        Depends(
            RateLimiter(
                limiter=_LOGIN_LIMITER,
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
