import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.endpoints import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)

app = FastAPI()

origin = settings.FRONTEND_HOST

# Solo permitir solicitudes desde el dominio específico para mejorar la seguridad y evitar problemas de CORS en producción.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Funcion para manejar errores globales que no son manejados por los endpoints
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor."},
    )


app.include_router(api_router)
