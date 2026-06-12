from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_personal_assistant",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Berlin",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "generate-upcoming-reminders-every-5-minutes": {
            "task": "generate_upcoming_reminders",
            "schedule": 300.0,
            "kwargs": {"days_ahead": 1, "lead_minutes": 15},
        },
        "send-due-reminders-every-minute": {
            "task": "send_due_reminders",
            "schedule": 60.0,
            "kwargs": {"limit": 100},
        },
        "send-daily-agendas-at-7am-berlin": {
            "task": "send_daily_agendas",
            "schedule": crontab(hour=7, minute=0),
        },
    },
)
