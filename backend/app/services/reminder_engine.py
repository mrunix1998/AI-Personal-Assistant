from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.calendar_events import CalendarEvent
from app.models.reminder import Reminder
from app.models.user import User
from app.services.notification_delivery_service import NotificationDeliveryService
from app.services.unified_agenda_service import UnifiedAgendaService


class ReminderEngine:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.delivery = NotificationDeliveryService(db)

    def generate_for_day(self, *, user_id: UUID, agenda_date: date, lead_minutes: int = 15) -> dict[str, Any]:
        start = datetime.combine(agenda_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(agenda_date, time.max, tzinfo=timezone.utc)
        events = (
            self.db.query(CalendarEvent)
            .filter(CalendarEvent.user_id == user_id)
            .filter(CalendarEvent.starts_at >= start)
            .filter(CalendarEvent.starts_at <= end)
            .order_by(CalendarEvent.starts_at.asc())
            .all()
        )
        now = datetime.now(timezone.utc)
        created = 0
        skipped = 0
        for event in events:
            remind_at = event.starts_at - timedelta(minutes=lead_minutes)
            remind_at_cmp = remind_at if remind_at.tzinfo else remind_at.replace(tzinfo=timezone.utc)
            if remind_at_cmp <= now:
                skipped += 1
                continue
            exists = (
                self.db.query(Reminder)
                .filter(Reminder.user_id == user_id)
                .filter(Reminder.calendar_event_id == event.id)
                .filter(Reminder.remind_at == remind_at)
                .first()
            )
            if exists:
                skipped += 1
                continue
            local_time = event.starts_at.strftime("%H:%M")
            reminder = Reminder(
                user_id=user_id,
                calendar_event_id=event.id,
                title=f"Reminder: {event.title}",
                message=f"{event.title} starts at {local_time}." + (f" Location: {event.location}." if event.location else ""),
                channel="all",
                status="pending",
                remind_at=remind_at,
            )
            self.db.add(reminder)
            created += 1
        self.db.commit()
        return {"created_count": created, "skipped_count": skipped, "event_count": len(events)}

    def generate_for_all_users(self, *, days_ahead: int = 1, lead_minutes: int = 15) -> dict[str, Any]:
        today = datetime.now(timezone.utc).date()
        users = self.db.query(User).all()
        totals = {"users": len(users), "created_count": 0, "skipped_count": 0}
        for user in users:
            for offset in range(days_ahead + 1):
                result = self.generate_for_day(user_id=user.id, agenda_date=today + timedelta(days=offset), lead_minutes=lead_minutes)
                totals["created_count"] += result["created_count"]
                totals["skipped_count"] += result["skipped_count"]
        return totals

    async def send_due_reminders(self, *, limit: int = 50) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        due = (
            self.db.query(Reminder)
            .filter(Reminder.status == "pending")
            .filter(Reminder.remind_at <= now)
            .order_by(Reminder.remind_at.asc())
            .limit(limit)
            .all()
        )
        sent = 0
        failed = 0
        results: list[dict[str, Any]] = []
        for reminder in due:
            delivery = await self.delivery.deliver_to_user(
                user_id=reminder.user_id,
                title=reminder.title,
                message=reminder.message,
                source="reminder_engine",
            )
            ok = any(item.get("ok") for item in delivery if item.get("channel") in {"telegram", "email", "web"})
            reminder.status = "sent" if ok else "failed"
            self.db.add(reminder)
            sent += 1 if ok else 0
            failed += 0 if ok else 1
            results.append({"reminder_id": str(reminder.id), "status": reminder.status, "delivery": delivery})
        self.db.commit()
        return {"processed_count": len(due), "sent_count": sent, "failed_count": failed, "results": results}

    async def send_daily_agendas(self, *, agenda_date: date | None = None) -> dict[str, Any]:
        day = agenda_date or datetime.now(timezone.utc).date()
        users = self.db.query(User).all()
        sent_users = 0
        results: list[dict[str, Any]] = []
        for user in users:
            agenda = UnifiedAgendaService(self.db).build_daily_agenda(user.id, day)
            web = next((msg for msg in agenda.channel_messages if msg.channel == "web"), None)
            title = web.subject if web and web.subject else f"Daily agenda for {day}"
            message = web.message if web else f"Your agenda for {day} is ready."
            delivery = await self.delivery.deliver_to_user(
                user_id=user.id,
                title=title,
                message=message,
                source="daily_agenda_scheduler",
            )
            sent_users += 1
            results.append({"user_id": str(user.id), "delivery": delivery})
        return {"agenda_date": day.isoformat(), "user_count": len(users), "sent_user_count": sent_users, "results": results}
