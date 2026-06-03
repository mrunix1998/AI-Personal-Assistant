from fastapi import APIRouter

from app.api.v1.endpoints import agenda, auth, health, integrations

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(agenda.router)
api_router.include_router(integrations.router)
