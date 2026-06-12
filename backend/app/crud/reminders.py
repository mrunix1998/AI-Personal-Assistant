from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reminder import Reminder


class ReminderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def exists_for_user_at_time(self, user_id: UUID, title: str, remind_at: datetime) -> bool:
        reminder = self.db.scalar(
            select(Reminder)
            .where(Reminder.user_id == user_id)
            .where(Reminder.title == title)
            .where(Reminder.remind_at == remind_at)
        )
        return reminder is not None

    def create(self, user_id: UUID, title: str, message: str, remind_at: datetime, channel: str = "all") -> Reminder:
        reminder = Reminder(user_id=user_id, title=title, message=message, remind_at=remind_at, channel=channel, status="pending")
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder

    def list_for_user(self, user_id: UUID, status: str | None = None) -> list[Reminder]:
        stmt = select(Reminder).where(Reminder.user_id == user_id).order_by(Reminder.remind_at.asc())
        if status is not None:
            stmt = stmt.where(Reminder.status == status)
        return list(self.db.scalars(stmt).all())

    def list_due(self, user_id: UUID, now: datetime) -> list[Reminder]:
        return list(
            self.db.scalars(
                select(Reminder)
                .where(Reminder.user_id == user_id)
                .where(Reminder.status == "pending")
                .where(Reminder.remind_at <= now)
                .order_by(Reminder.remind_at.asc())
            ).all()
        )

    def mark_sent(self, reminder: Reminder) -> Reminder:
        reminder.status = "sent"
        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)
        return reminder
