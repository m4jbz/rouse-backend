import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def create_access_token(client_id: uuid.UUID) -> str:
    # Crea un token de acceso de corta duración.
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(client_id),
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(client_id: uuid.UUID) -> str:
    # Crea un token de actualización de larga duración.
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(client_id),
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm="HS256")


def create_email_verification_token(client_id: uuid.UUID) -> str:
    # Crea un token enviado por correo para la verificación de email.
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.EMAIL_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(client_id),
        "type": "email_verification",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_EMAIL_SECRET, algorithm="HS256")


def create_password_reset_token(client_id: uuid.UUID) -> str:
    # Crea un token enviado por correo para el restablecimiento de contraseña.
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(client_id),
        "type": "password_reset",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_PASSWORD_RESET_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    # Decodifica y valida un token de acceso.
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict:
    # Decodifica y valida un token de actualización. 
    payload = jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=["HS256"])
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def decode_email_verification_token(token: str) -> dict:
    # Decodifica y valida un token de verificación de email.
    payload = jwt.decode(token, settings.JWT_EMAIL_SECRET, algorithms=["HS256"])
    if payload.get("type") != "email_verification":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def decode_password_reset_token(token: str) -> dict:
    # Decodifica y valida un token de restablecimiento de contraseña.
    payload = jwt.decode(token, settings.JWT_PASSWORD_RESET_SECRET, algorithms=["HS256"])
    if payload.get("type") != "password_reset":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


# ---- Admin tokens ----


def create_admin_access_token(user_id: uuid.UUID) -> str:
    # Crea un token de acceso de corta duración para usuarios administradores.
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "type": "admin_access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_admin_refresh_token(user_id: uuid.UUID) -> str:
    # Crea un token de actualización de larga duración para usuarios administradores.
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(user_id),
        "type": "admin_refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm="HS256")


def decode_admin_access_token(token: str) -> dict:
    # Decodifica y valida un token de acceso de administrador.
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") != "admin_access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def decode_admin_refresh_token(token: str) -> dict:
    # Decodifica y valida un token de actualización de administrador.
    payload = jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=["HS256"])
    if payload.get("type") != "admin_refresh":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload
