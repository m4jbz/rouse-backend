import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlmodel import Session, select

from app.core.db import get_db
from app.models import Client

router = APIRouter(prefix="/clients", tags=["clients"])

# Body de la petición para registrar un cliente nuevo
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
    def password_not_empty(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


# Body de la petición para login de cliente
class LoginClient(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(client: RegisterClient, db: Session = Depends(get_db)):
    # Verifica si ya existe un cliente con el mismo email
    existing = db.exec(
        select(Client).where(Client.email == client.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash de la contraseña usando bcrypt
    password_bytes = client.password.encode("utf-8")
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    new_client = Client(
        email=client.email,
        name=client.name,
        phone=str(client.phone),
        password_hash=password_hash,
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    return {
        "id": new_client.id,
        "email": new_client.email,
        "name": new_client.name,
        "phone": new_client.phone,
    }


@router.post("/login")
def login(data: LoginClient, db: Session = Depends(get_db)):
    # Verifica si el cliente existe
    client = db.exec(
        select(Client).where(Client.email == data.email)
    ).first()
    if not client:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verifica si la contraseña es correcta
    password_bytes = data.password.encode("utf-8")
    if not bcrypt.checkpw(password_bytes, client.password_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "client_id": str(client.id)}
