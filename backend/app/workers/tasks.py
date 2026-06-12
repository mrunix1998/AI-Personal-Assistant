from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from app.db.session import SessionLocal
from app.services.reminder_engine import ReminderEngine
from app.workers.celery_app import celery_app


def _run(coro):
    return asyncio.run(coro)


@celery_app.task(name="generate_upcoming_reminders")
def generate_upcoming_reminders(days_ahead: int = 1, lead_minutes: int = 15) -> dict[str, Any]:
    db = SessionLocal()
    try:
        return ReminderEngine(db).generate_for_all_users(days_ahead=days_ahead, lead_minutes=lead_minutes)
    finally:
        db.close()


@celery_app.task(name="send_due_reminders")
def send_due_reminders(limit: int = 100) -> dict[str, Any]:
    db = SessionLocal()
    try:
        return _run(ReminderEngine(db).send_due_reminders(limit=limit))
    finally:
        db.close()


@celery_app.task(name="send_daily_agendas")
def send_daily_agendas(agenda_date: str | None = None) -> dict[str, Any]:
    db = SessionLocal()
    try:
        parsed_date = date.fromisoformat(agenda_date) if agenda_date else None
        return _run(ReminderEngine(db).send_daily_agendas(agenda_date=parsed_date))
    finally:
        db.close()
