from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from app.core.db import get_db
from app.models import User, Role

import bcrypt

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterUser(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str

class LoginUser(BaseModel):
    email: EmailStr
    password_hash: str


@router.post("/register")
def register(user: RegisterUser, db: Session = Depends(get_db)):
    existing = db.exec(select(User).where(User.email == user.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    password_bytes = user.password.encode("utf-8")
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")


    new_user = User(
        email=user.email,
        name=user.name,
        password_hash=password_hash,
        is_active=True,
        role=Role(user.role),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"id": new_user.id, "email": new_user.email, "name": new_user.name}


@router.post("/login")
def login(login_user: LoginUser, db: Session = Depends(get_db)):
    user = db.exec(select(User).where(User.email == login_user.email)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    password_bytes = login_user.password_hash.encode("utf-8")
    if not bcrypt.checkpw(password_bytes, user.password_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "user_id": str(user.id)}
