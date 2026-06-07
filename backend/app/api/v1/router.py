from fastapi import APIRouter

from app.api.v1.endpoints import agenda, auth, health, integrations, planning, reminders, tasks, unified_agenda

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(agenda.router)
api_router.include_router(integrations.router)
api_router.include_router(reminders.router)
api_router.include_router(tasks.router)
api_router.include_router(planning.router)
api_router.include_router(unified_agenda.router)
