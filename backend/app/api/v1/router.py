from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    integrations,
    agenda,
    tasks,
    reminders,
    notifications,
    planning,
    integration_actions,
    calendar,
    automation,
    monitoring,
    secrets,
)

api_router = APIRouter()

for router in [
    health.router,
    monitoring.router,
    auth.router,
    integrations.router,
    integration_actions.router,
    calendar.router,
    agenda.router,
    tasks.router,
    reminders.router,
    notifications.router,
    planning.router,
    automation.router,
    secrets.router,
]:
    api_router.include_router(router)
