from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud.notifications import NotificationRepository
from app.services.unified_agenda_service import UnifiedAgendaService


class NotificationCenterService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_daily_agenda_notification(self, *, user_id: UUID, agenda_date: date):
        agenda = UnifiedAgendaService(self.db).build_daily_agenda(user_id=user_id, agenda_date=agenda_date)
        web_message = next((message for message in agenda.channel_messages if message.channel == "web"), None)
        title = web_message.subject if web_message and web_message.subject else f"Daily agenda for {agenda_date.isoformat()}"
        message = web_message.message if web_message else f"Your agenda for {agenda_date.isoformat()} is ready."
        agenda_datetime = datetime.combine(agenda_date, time.min).replace(tzinfo=timezone.utc)
        return NotificationRepository(self.db).create(
            user_id=user_id,
            title=title,
            message=message,
            source="unified_agenda",
            channel="web",
            agenda_date=agenda_datetime,
        )
