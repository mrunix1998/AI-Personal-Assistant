from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calendar_event import CalendarEvent
from app.models.task_item import TaskItem
from app.schemas.unified_agenda import (
    ChannelMessage,
    UnifiedAgendaItem,
    UnifiedAgendaStats,
    UnifiedDailyAgendaRead,
)


class UnifiedAgendaService:
    """Aggregates meetings and tasks from all connected providers into one daily view.

    This service does not create or schedule tasks. It only normalizes existing data
    from sources such as Google Calendar, Jira, Notion, Trello, Todoist, etc.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def build_daily_agenda(self, *, user_id: UUID, agenda_date: date) -> UnifiedDailyAgendaRead:
        day_start = datetime.combine(agenda_date, time.min).replace(tzinfo=timezone.utc)
        day_end = datetime.combine(agenda_date, time.max).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        events = self.db.scalars(
            select(CalendarEvent)
            .where(CalendarEvent.user_id == user_id)
            .where(CalendarEvent.starts_at >= day_start)
            .where(CalendarEvent.starts_at <= day_end)
            .order_by(CalendarEvent.starts_at.asc())
        ).all()

        # Include tasks due on this date and unscheduled tasks that are not completed.
        # Later Jira/Notion/Trello syncs should write into task_items with provider_name.
        tasks = self.db.scalars(
            select(TaskItem)
            .where(TaskItem.user_id == user_id)
            .where(
                (TaskItem.due_at == None)  # noqa: E711
                | ((TaskItem.due_at >= day_start) & (TaskItem.due_at <= day_end))
            )
            .order_by(TaskItem.due_at.asc().nulls_last())
        ).all()

        meeting_items = [self._event_to_item(event) for event in events]
        task_items = [self._task_to_item(task) for task in tasks]

        timeline = sorted(
            meeting_items + task_items,
            key=lambda item: item.sort_at or datetime.max.replace(tzinfo=timezone.utc),
        )

        overdue_task_count = sum(
            1
            for task in tasks
            if task.due_at is not None and not task.is_completed and self._as_aware_utc(task.due_at) < now
        )
        completed_task_count = sum(1 for task in tasks if task.is_completed)

        stats = UnifiedAgendaStats(
            meeting_count=len(meeting_items),
            task_count=len(task_items),
            overdue_task_count=overdue_task_count,
            completed_task_count=completed_task_count,
            total_count=len(meeting_items) + len(task_items),
        )

        channel_messages = self._build_channel_messages(
            agenda_date=agenda_date,
            stats=stats,
            timeline=timeline,
        )

        return UnifiedDailyAgendaRead(
            date=agenda_date.isoformat(),
            stats=stats,
            meetings=meeting_items,
            tasks=task_items,
            timeline=timeline,
            channel_messages=channel_messages,
        )

    def _event_to_item(self, event: CalendarEvent) -> UnifiedAgendaItem:
        return UnifiedAgendaItem(
            id=event.id,
            item_type="meeting",
            source=self._provider_value(event.provider_name),
            title=event.title,
            description=event.description,
            location=event.location,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            calendar_name=event.external_calendar_name,
            external_id=event.external_event_id,
            sort_at=event.starts_at,
        )

    def _task_to_item(self, task: TaskItem) -> UnifiedAgendaItem:
        return UnifiedAgendaItem(
            id=task.id,
            item_type="task",
            source=task.provider_name,
            title=task.title,
            description=task.notes,
            due_at=task.due_at,
            is_completed=task.is_completed,
            external_id=task.external_task_id,
            sort_at=task.due_at,
        )

    @staticmethod
    def _provider_value(provider: object) -> str:
        return getattr(provider, "value", str(provider))

    @staticmethod
    def _as_aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _build_channel_messages(
        self,
        *,
        agenda_date: date,
        stats: UnifiedAgendaStats,
        timeline: list[UnifiedAgendaItem],
    ) -> list[ChannelMessage]:
        subject = f"Daily agenda for {agenda_date.isoformat()}"
        if stats.total_count == 0:
            body = f"You have no synced meetings or tasks for {agenda_date.isoformat()}."
        else:
            lines = [
                f"Your agenda for {agenda_date.isoformat()}:",
                f"Meetings: {stats.meeting_count} | Tasks: {stats.task_count} | Overdue: {stats.overdue_task_count}",
                "",
            ]
            for item in timeline:
                prefix = "📅" if item.item_type == "meeting" else "✅"
                if item.starts_at:
                    when = item.starts_at.strftime("%H:%M")
                elif item.due_at:
                    when = f"due {item.due_at.strftime('%H:%M')}"
                else:
                    when = "no due time"
                lines.append(f"{prefix} {when} — {item.title} ({item.source})")
            body = "\n".join(lines)

        return [
            ChannelMessage(channel="web", subject=subject, message=body, payload={"total_count": stats.total_count}),
            ChannelMessage(channel="email", subject=subject, message=body, payload={"total_count": stats.total_count}),
            ChannelMessage(channel="telegram", subject=None, message=body, payload={"total_count": stats.total_count}),
            ChannelMessage(channel="whatsapp", subject=None, message=body, payload={"total_count": stats.total_count}),
        ]
