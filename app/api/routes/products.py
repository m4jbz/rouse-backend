from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from app.core.db import get_db
from app.core.deps import get_current_user, require_admin
from app.models import Category, Product, ProductVariant, OrderDetail, User

router = APIRouter(prefix="/products", tags=["products"])


# Body para crear variante por producto id
class VariantCreate(BaseModel):
    name: str
    price: Decimal

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Variant name cannot be empty")
        return v.strip()

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v


# Body para actualizar variante por producto id
class VariantUpdate(BaseModel):
    name: str | None = None
    price: Decimal | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Variant name cannot be empty")
        return v.strip() if v else v

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Price must be greater than 0")
        return v


# Body para obtener y listar variantes por producto id
class VariantPublic(BaseModel):
    id: int
    name: str
    price: Decimal
    image_path: str


# Body para las peticiones POST
class ProductCreate(BaseModel):
    category_id: int
    name: str
    description: str | None = None
    is_active: bool = True
    variants: list[VariantCreate] = []

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Product name cannot be empty")
        return v.strip()


# Body para las peticiones PATCH
class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Product name cannot be empty")
        return v.strip() if v else v


# Body para listar y obtener los productos
class ProductPublic(BaseModel):
    id: int
    category_id: int
    name: str
    description: str | None
    is_active: bool
    variants: list[VariantPublic] = []

@router.get("/", response_model=list[ProductPublic])
def list_products(
    category_id: int | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    query = select(Product)
    if category_id is not None:
        # Verifica que la categoría exista
        category = db.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        query = query.where(Product.category_id == category_id)
    # Devuelve solo productos activos
    if active_only:
        query = query.where(Product.is_active == True)
    products = db.exec(query).all()
    return products


@router.get("/products_with_variants", response_model=list[VariantPublic])
def list_products_with_variants(
    category_id: int | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    query = select(ProductVariant).join(Product)
    if category_id is not None:
        # Verifica que la categoría exista
        category = db.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        query = query.where(Product.category_id == category_id)
    # Devuelve solo productos activos
    if active_only:
        query = query.where(Product.is_active == True)
    variants = db.exec(query).all()
    return variants

@router.get("/{product_id}", response_model=ProductPublic)
def get_product(product_id: int, db: Session = Depends(get_db)):
    # Verifica que el producto exista
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/{product_id}/variants", response_model=list[VariantPublic])
def list_variants(product_id: int, db: Session = Depends(get_db)):
    # Verifica que el producto exista
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product.variants


@router.post("/", response_model=ProductPublic, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    # Verifica que la categoria exista
    category = db.get(Category, data.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    product = Product(
        category_id=data.category_id,
        name=data.name,
        description=data.description,
        is_active=data.is_active,
    )
    db.add(product)
    db.flush()

    # Crea las variantes asociadas al producto
    for v in data.variants:
        variant = ProductVariant(product_id=product.id, name=v.name, price=v.price)
        db.add(variant)

    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductPublic)
def update_product(
    product_id: int, data: ProductUpdate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    # Verifica que el producto exista
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.category_id is not None:
        # Verifica que la categoria exista
        category = db.get(Category, data.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    update_data = data.model_dump(exclude_unset=True)
    product.sqlmodel_update(update_data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db), _user: User = Depends(require_admin)):
    # Verifica que el producto exista
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # No se puede eliminar un producto que tenga detalles de orden asociados
    order_detail = db.exec(
        select(OrderDetail).where(OrderDetail.product_id == product_id)
    ).first()
    if order_detail:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete product with associated orders",
        )

    db.delete(product)
    db.commit()

@router.post(
    "/{product_id}/variants", response_model=VariantPublic, status_code=201
)
def create_variant(
    product_id: int, data: VariantCreate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    # Verifica que el producto exista
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    variant = ProductVariant(product_id=product_id, **data.model_dump())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.patch(
    "/{product_id}/variants/{variant_id}", response_model=VariantPublic
)
def update_variant(
    product_id: int,
    variant_id: int,
    data: VariantUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Verifica que la variante exista y que sea del producto correcto 
    variant = db.exec(
        select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id,
        )
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    update_data = data.model_dump(exclude_unset=True)
    variant.sqlmodel_update(update_data)
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.delete("/{product_id}/variants/{variant_id}", status_code=204)
def delete_variant(
    product_id: int, variant_id: int, db: Session = Depends(get_db), _user: User = Depends(require_admin)
):
    # Verifica que la variante exista y que sea del producto correcto 
    variant = db.exec(
        select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id,
        )
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    db.delete(variant)
    db.commit()
