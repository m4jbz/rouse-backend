from fastapi import APIRouter

from app.api.routes import auth, categories, orders, products

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)
