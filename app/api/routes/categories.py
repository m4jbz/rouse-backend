from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.db import get_db
from app.models import Category

router = APIRouter(prefix="/categories", tags=["categories"])

# Body de las peticiones post y patch para crear y actualizar categorías
class CategoryCreate(BaseModel):
    name: str
    description: str | None = None

class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

# Body de las peticiones para listar y obtener categorías
class CategoryPublic(BaseModel):
    id: int
    name: str
    description: str | None

@router.get("/", response_model=list[CategoryPublic])
def list_categories(db: Session = Depends(get_db)):
    categories = db.exec(select(Category)).all()
    return categories


@router.get("/{category_id}", response_model=CategoryPublic)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/", response_model=CategoryPublic, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    # Convierte el modelo a un diccionario y luego a un objeto Category
    # usando ** para pasar los campos como argumentos
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryPublic)
def update_category(
    category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)
):
    # Busca si la categoría existe
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # exclude_unset=True para solo incluir los campos que se enviaron
    update_data = data.model_dump(exclude_unset=True)
    category.sqlmodel_update(update_data)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    # Busca si la categoría existe
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.commit()
