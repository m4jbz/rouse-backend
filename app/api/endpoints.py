from fastapi import APIRouter

from app.api.routes import users, clients, categories, orders, products

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(clients.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)
