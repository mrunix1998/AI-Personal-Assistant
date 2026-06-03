from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calendar_event import CalendarEvent
from app.models.task_item import TaskItem


class AgendaService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_daily_agenda(self, user_id: UUID, agenda_date: date) -> tuple[list[CalendarEvent], list[TaskItem]]:
        start = datetime.combine(agenda_date, time.min)
        end = datetime.combine(agenda_date, time.max)

        events = self.db.scalars(
            select(CalendarEvent)
            .where(CalendarEvent.user_id == user_id)
            .where(CalendarEvent.starts_at >= start)
            .where(CalendarEvent.starts_at <= end)
            .order_by(CalendarEvent.starts_at.asc())
        ).all()

        tasks = self.db.scalars(
            select(TaskItem)
            .where(TaskItem.user_id == user_id)
            .where((TaskItem.due_at == None) | ((TaskItem.due_at >= start) & (TaskItem.due_at <= end)))  # noqa: E711
            .order_by(TaskItem.due_at.asc().nulls_last())
        ).all()

        return list(events), list(tasks)
