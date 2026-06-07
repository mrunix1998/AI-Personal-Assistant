from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.calendar_event import CalendarEvent
from app.models.task_item import TaskItem
from app.services.agenda_service import AgendaService


@dataclass(frozen=True)
class FreeSlot:
    start: datetime
    end: datetime

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


def _format_clock(value: datetime) -> str:
    return value.strftime("%H:%M")


def _format_duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h {mins}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


class DailySummaryService:
    """Builds an assistant-like daily summary from synced calendar events and tasks.

    This first version is deterministic and does not depend on an external LLM.
    Later we can pass the same structured context to an AI provider.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def build_summary(
        self,
        user_id: UUID,
        agenda_date: date,
        day_start: time = time(hour=8),
        day_end: time = time(hour=20),
    ) -> dict:
        events, tasks = AgendaService(self.db).get_daily_agenda(user_id=user_id, agenda_date=agenda_date)
        busy_events = sorted(events, key=lambda event: event.starts_at)
        open_tasks = [task for task in tasks if not task.is_completed]
        overdue_tasks = self._get_overdue_tasks(user_id=user_id, before_date=agenda_date)
        free_slots = self._calculate_free_slots(agenda_date, day_start, day_end, busy_events)

        headline = self._build_headline(agenda_date, busy_events, open_tasks, overdue_tasks)
        narrative = self._build_narrative(busy_events, open_tasks, overdue_tasks, free_slots)
        suggestions = self._build_suggestions(busy_events, open_tasks, overdue_tasks, free_slots)

        return {
            "date": agenda_date.isoformat(),
            "headline": headline,
            "summary": narrative,
            "stats": {
                "event_count": len(busy_events),
                "task_count": len(open_tasks),
                "overdue_task_count": len(overdue_tasks),
                "free_slot_count": len(free_slots),
                "total_free_minutes": sum(slot.duration_minutes for slot in free_slots),
            },
            "timeline": [self._event_to_timeline_item(event) for event in busy_events],
            "free_slots": [
                {
                    "start": slot.start,
                    "end": slot.end,
                    "duration_minutes": slot.duration_minutes,
                    "label": f"{_format_clock(slot.start)}-{_format_clock(slot.end)}",
                }
                for slot in free_slots
            ],
            "priorities": [
                {
                    "id": task.id,
                    "title": task.title,
                    "due_at": task.due_at,
                    "provider_name": str(task.provider_name),
                    "is_overdue": False,
                }
                for task in open_tasks[:5]
            ]
            + [
                {
                    "id": task.id,
                    "title": task.title,
                    "due_at": task.due_at,
                    "provider_name": str(task.provider_name),
                    "is_overdue": True,
                }
                for task in overdue_tasks[:5]
            ],
            "suggestions": suggestions,
        }

    def _get_overdue_tasks(self, user_id: UUID, before_date: date) -> list[TaskItem]:
        # Reuse AgendaService behavior only for same-day tasks; here we need overdue tasks separately.
        from sqlalchemy import select

        start_of_day = datetime.combine(before_date, time.min)
        tasks = self.db.scalars(
            select(TaskItem)
            .where(TaskItem.user_id == user_id)
            .where(TaskItem.is_completed == False)  # noqa: E712
            .where(TaskItem.due_at != None)  # noqa: E711
            .where(TaskItem.due_at < start_of_day)
            .order_by(TaskItem.due_at.asc())
        ).all()
        return list(tasks)

    def _calculate_free_slots(
        self,
        agenda_date: date,
        day_start: time,
        day_end: time,
        events: Iterable[CalendarEvent],
    ) -> list[FreeSlot]:
        window_start = datetime.combine(agenda_date, day_start)
        window_end = datetime.combine(agenda_date, day_end)
        free_slots: list[FreeSlot] = []
        cursor = window_start

        for event in events:
            event_start = max(event.starts_at.replace(tzinfo=None), window_start)
            event_end = min(event.ends_at.replace(tzinfo=None), window_end)

            if event_end <= window_start or event_start >= window_end:
                continue

            if event_start > cursor:
                gap_minutes = int((event_start - cursor).total_seconds() // 60)
                if gap_minutes >= 30:
                    free_slots.append(FreeSlot(start=cursor, end=event_start))

            if event_end > cursor:
                cursor = event_end

        if cursor < window_end:
            gap_minutes = int((window_end - cursor).total_seconds() // 60)
            if gap_minutes >= 30:
                free_slots.append(FreeSlot(start=cursor, end=window_end))

        return free_slots

    def _build_headline(
        self,
        agenda_date: date,
        events: list[CalendarEvent],
        tasks: list[TaskItem],
        overdue_tasks: list[TaskItem],
    ) -> str:
        if not events and not tasks and not overdue_tasks:
            return f"Your schedule is clear for {agenda_date.isoformat()}."

        parts: list[str] = []
        if events:
            parts.append(f"{len(events)} calendar event{'s' if len(events) != 1 else ''}")
        if tasks:
            parts.append(f"{len(tasks)} open task{'s' if len(tasks) != 1 else ''}")
        if overdue_tasks:
            parts.append(f"{len(overdue_tasks)} overdue task{'s' if len(overdue_tasks) != 1 else ''}")

        return "Today you have " + ", ".join(parts) + "."

    def _build_narrative(
        self,
        events: list[CalendarEvent],
        tasks: list[TaskItem],
        overdue_tasks: list[TaskItem],
        free_slots: list[FreeSlot],
    ) -> str:
        lines: list[str] = []

        if events:
            first = events[0]
            last = events[-1]
            lines.append(f"Your first event is '{first.title}' at {_format_clock(first.starts_at)}.")
            if len(events) > 1:
                lines.append(f"Your last event ends at {_format_clock(last.ends_at)}.")
        else:
            lines.append("You have no calendar events synced for this day.")

        if free_slots:
            best_slot = max(free_slots, key=lambda slot: slot.duration_minutes)
            lines.append(
                f"Your longest free slot is {_format_duration(best_slot.duration_minutes)} "
                f"from {_format_clock(best_slot.start)} to {_format_clock(best_slot.end)}."
            )
        else:
            lines.append("There are no free slots of at least 30 minutes inside your planning window.")

        if overdue_tasks:
            lines.append(f"You also have {len(overdue_tasks)} overdue task(s) to review.")
        elif tasks:
            lines.append(f"You have {len(tasks)} open task(s) planned for today.")

        return " ".join(lines)

    def _build_suggestions(
        self,
        events: list[CalendarEvent],
        tasks: list[TaskItem],
        overdue_tasks: list[TaskItem],
        free_slots: list[FreeSlot],
    ) -> list[str]:
        suggestions: list[str] = []

        if overdue_tasks:
            suggestions.append("Start by reviewing overdue tasks before adding new commitments.")

        if free_slots and (tasks or overdue_tasks):
            best_slot = max(free_slots, key=lambda slot: slot.duration_minutes)
            suggestions.append(
                f"Use the {_format_clock(best_slot.start)}-{_format_clock(best_slot.end)} free slot "
                "for your highest-priority task."
            )

        if events:
            suggestions.append("Check meeting links, locations, and preparation notes before your first event.")

        if len(events) >= 5:
            suggestions.append("Your calendar looks busy; avoid scheduling additional deep-work tasks today.")
        elif not events and not tasks and not overdue_tasks:
            suggestions.append("This is a good day for deep work, planning, or catching up.")

        return suggestions[:4]

    def _event_to_timeline_item(self, event: CalendarEvent) -> dict:
        return {
            "id": event.id,
            "title": event.title,
            "start": event.starts_at,
            "end": event.ends_at,
            "location": event.location,
            "provider_name": str(event.provider_name),
            "label": f"{_format_clock(event.starts_at)}-{_format_clock(event.ends_at)}",
        }
