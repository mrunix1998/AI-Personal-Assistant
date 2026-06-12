from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.reminder_engine import ReminderEngine
from app.workers.tasks import generate_upcoming_reminders, send_daily_agendas, send_due_reminders

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/status")
def automation_status() -> dict[str, Any]:
    return {
        "status": "enabled",
        "worker_task_names": ["generate_upcoming_reminders", "send_due_reminders", "send_daily_agendas"],
        "schedules": {
            "generate_upcoming_reminders": "every 5 minutes",
            "send_due_reminders": "every 1 minute",
            "send_daily_agendas": "daily 07:00 Europe/Berlin",
        },
    }


@router.post("/generate-reminders")
def generate_reminders_for_current_user(
    agenda_date: date,
    lead_minutes: int = Query(default=15, ge=1, le=1440),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ReminderEngine(db).generate_for_day(
        user_id=current_user.id,
        agenda_date=agenda_date,
        lead_minutes=lead_minutes,
    )


@router.post("/run-due-reminders")
async def run_due_reminders_now(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Runs inline for UI/debug. Celery Beat runs the same logic automatically.
    return await ReminderEngine(db).send_due_reminders(limit=limit)


@router.post("/send-daily-agenda")
async def send_daily_agenda_now(
    agenda_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Runs only for authenticated user's day, not every user.
    engine = ReminderEngine(db)
    from app.services.unified_agenda_service import UnifiedAgendaService

    agenda = UnifiedAgendaService(db).build_daily_agenda(current_user.id, agenda_date)
    web = next((msg for msg in agenda.channel_messages if msg.channel == "web"), None)
    title = web.subject if web and web.subject else f"Daily agenda for {agenda_date}"
    message = web.message if web else f"Your agenda for {agenda_date} is ready."
    delivery = await engine.delivery.deliver_to_user(
        user_id=current_user.id,
        title=title,
        message=message,
        source="manual_daily_agenda",
    )
    return {"agenda_date": agenda_date.isoformat(), "delivery": delivery}


@router.post("/enqueue/generate-reminders")
def enqueue_generate_reminders(days_ahead: int = 1, lead_minutes: int = 15):
    result = generate_upcoming_reminders.delay(days_ahead=days_ahead, lead_minutes=lead_minutes)
    return {"status": "queued", "task_id": result.id}


@router.post("/enqueue/run-due-reminders")
def enqueue_due_reminders(limit: int = 100):
    result = send_due_reminders.delay(limit=limit)
    return {"status": "queued", "task_id": result.id}


@router.post("/enqueue/send-daily-agendas")
def enqueue_daily_agendas(agenda_date: date | None = None):
    result = send_daily_agendas.delay(agenda_date.isoformat() if agenda_date else None)
    return {"status": "queued", "task_id": result.id}
