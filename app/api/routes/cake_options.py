from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from app.core.db import get_db
from app.core.deps import get_current_user, require_admin
from app.models import CakeFlavor, CakeFilling, CakeTopping, User

router = APIRouter(prefix="/cake-options", tags=["cake-options"])


# ============================================================
# Schemas
# ============================================================

class CakeOptionCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class CakeOptionUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip() if v else v


class CakeOptionPublic(BaseModel):
    id: int
    name: str
    is_active: bool


# ============================================================
# Flavors
# ============================================================

@router.get("/flavors", response_model=list[CakeOptionPublic])
def list_flavors(active_only: bool = True, db: Session = Depends(get_db)):
    query = select(CakeFlavor)
    if active_only:
        query = query.where(CakeFlavor.is_active == True)
    return db.exec(query).all()


@router.post("/flavors", response_model=CakeOptionPublic, status_code=201)
def create_flavor(
    data: CakeOptionCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    flavor = CakeFlavor(name=data.name)
    db.add(flavor)
    db.commit()
    db.refresh(flavor)
    return flavor


@router.patch("/flavors/{flavor_id}", response_model=CakeOptionPublic)
def update_flavor(
    flavor_id: int,
    data: CakeOptionUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    flavor = db.get(CakeFlavor, flavor_id)
    if not flavor:
        raise HTTPException(status_code=404, detail="Flavor not found")

    update_data = data.model_dump(exclude_unset=True)
    flavor.sqlmodel_update(update_data)
    db.add(flavor)
    db.commit()
    db.refresh(flavor)
    return flavor


@router.delete("/flavors/{flavor_id}", status_code=204)
def delete_flavor(
    flavor_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    flavor = db.get(CakeFlavor, flavor_id)
    if not flavor:
        raise HTTPException(status_code=404, detail="Flavor not found")
    db.delete(flavor)
    db.commit()


# ============================================================
# Fillings
# ============================================================

@router.get("/fillings", response_model=list[CakeOptionPublic])
def list_fillings(active_only: bool = True, db: Session = Depends(get_db)):
    query = select(CakeFilling)
    if active_only:
        query = query.where(CakeFilling.is_active == True)
    return db.exec(query).all()


@router.post("/fillings", response_model=CakeOptionPublic, status_code=201)
def create_filling(
    data: CakeOptionCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    filling = CakeFilling(name=data.name)
    db.add(filling)
    db.commit()
    db.refresh(filling)
    return filling


@router.patch("/fillings/{filling_id}", response_model=CakeOptionPublic)
def update_filling(
    filling_id: int,
    data: CakeOptionUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    filling = db.get(CakeFilling, filling_id)
    if not filling:
        raise HTTPException(status_code=404, detail="Filling not found")

    update_data = data.model_dump(exclude_unset=True)
    filling.sqlmodel_update(update_data)
    db.add(filling)
    db.commit()
    db.refresh(filling)
    return filling


@router.delete("/fillings/{filling_id}", status_code=204)
def delete_filling(
    filling_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    filling = db.get(CakeFilling, filling_id)
    if not filling:
        raise HTTPException(status_code=404, detail="Filling not found")
    db.delete(filling)
    db.commit()


# ============================================================
# Toppings
# ============================================================

@router.get("/toppings", response_model=list[CakeOptionPublic])
def list_toppings(active_only: bool = True, db: Session = Depends(get_db)):
    query = select(CakeTopping)
    if active_only:
        query = query.where(CakeTopping.is_active == True)
    return db.exec(query).all()


@router.post("/toppings", response_model=CakeOptionPublic, status_code=201)
def create_topping(
    data: CakeOptionCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    topping = CakeTopping(name=data.name)
    db.add(topping)
    db.commit()
    db.refresh(topping)
    return topping


@router.patch("/toppings/{topping_id}", response_model=CakeOptionPublic)
def update_topping(
    topping_id: int,
    data: CakeOptionUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    topping = db.get(CakeTopping, topping_id)
    if not topping:
        raise HTTPException(status_code=404, detail="Topping not found")

    update_data = data.model_dump(exclude_unset=True)
    topping.sqlmodel_update(update_data)
    db.add(topping)
    db.commit()
    db.refresh(topping)
    return topping


@router.delete("/toppings/{topping_id}", status_code=204)
def delete_topping(
    topping_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    topping = db.get(CakeTopping, topping_id)
    if not topping:
        raise HTTPException(status_code=404, detail="Topping not found")
    db.delete(topping)
    db.commit()


# ============================================================
# Predefined sizes (no DB table, just constants)
# ============================================================

CAKE_SIZES = [
    {"id": "chico", "name": "Chico"},
    {"id": "mediano", "name": "Mediano"},
    {"id": "grande", "name": "Grande"},
]


@router.get("/sizes")
def list_sizes():
    """Returns predefined cake sizes."""
    return CAKE_SIZES
