import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from app.core.db import get_db
from app.models import Role, User

router = APIRouter(prefix="/users", tags=["users"])

# Body de la petición para registrar un usuario nuevo
class RegisterUser(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Role


# Body de la petición para login de usuario
class LoginUser(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
def register(user: RegisterUser, db: Session = Depends(get_db)):
    # Verifica si ya existe un usuario con el mismo email
    existing = db.exec(select(User).where(User.email == user.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash de la contraseña usando bcrypt
    password_bytes = user.password.encode("utf-8")
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    new_user = User(
        email=user.email,
        name=user.name,
        password_hash=password_hash,
        is_active=True,
        role=user.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "name": new_user.name,
        "is_active": new_user.is_active,
    }


@router.post("/login")
def login(data: LoginUser, db: Session = Depends(get_db)):
    # Verifica si el usuario existe
    user = db.exec(select(User).where(User.email == data.email)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verifica si la contraseña es correcta
    password_bytes = data.password.encode("utf-8")
    if not bcrypt.checkpw(password_bytes, user.password_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "user_id": str(user.id)}
