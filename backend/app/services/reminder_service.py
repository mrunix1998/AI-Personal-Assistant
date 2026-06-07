from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud.reminders import ReminderRepository
from app.models.enums import ReminderStatus
from app.models.reminder import Reminder
from app.services.agenda_service import AgendaService


class ReminderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ReminderRepository(db)

    def generate_event_reminders(self, user_id: UUID, agenda_date: date, lead_minutes: int = 30) -> tuple[list[Reminder], int]:
        events, _ = AgendaService(self.db).get_daily_agenda(user_id=user_id, agenda_date=agenda_date)
        created: list[Reminder] = []
        skipped_count = 0

        for event in events:
            scheduled_for = event.starts_at - timedelta(minutes=lead_minutes)
            now = datetime.now(timezone.utc)
            if scheduled_for.tzinfo is None:
                scheduled_for_cmp = scheduled_for.replace(tzinfo=timezone.utc)
            else:
                scheduled_for_cmp = scheduled_for

            if scheduled_for_cmp < now:
                skipped_count += 1
                continue

            title = f"Reminder: {event.title}"
            message = f"You have '{event.title}' at {event.starts_at.strftime('%H:%M')}."
            if event.location:
                message += f" Location: {event.location}."

            if self.repo.exists_for_user_at_time(user_id=user_id, title=title, scheduled_for=scheduled_for):
                skipped_count += 1
                continue

            created.append(self.repo.create(user_id=user_id, title=title, message=message, scheduled_for=scheduled_for))

        return created, skipped_count

    def list_reminders(self, user_id: UUID, status: ReminderStatus | None = None) -> list[Reminder]:
        return self.repo.list_for_user(user_id=user_id, status=status)

    def simulate_due_reminders(self, user_id: UUID) -> list[Reminder]:
        due = self.repo.list_due(user_id=user_id, now=datetime.now(timezone.utc))
        return [self.repo.mark_sent(reminder) for reminder in due]
