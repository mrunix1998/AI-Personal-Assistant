from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.planning_result import PlanningResult
from app.models.task_item import TaskItem
from app.services.agenda_service import AgendaService
from app.services.daily_summary_service import DailySummaryService, FreeSlot, _format_clock


_PRIORITY_WEIGHT = {
    "urgent": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


class PlanningService:
    """Rule-based daily planning engine.

    V1 does not call an external LLM. It creates a deterministic plan by:
    1. reading calendar events and open tasks for the day,
    2. calculating free time slots,
    3. sorting tasks by priority and deadline,
    4. placing tasks into the earliest slot where they fit.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def build_context(
        self,
        *,
        user_id: UUID,
        user_email: str,
        agenda_date: date,
        day_start: time = time(hour=8),
        day_end: time = time(hour=20),
        min_break_minutes: int = 15,
    ) -> dict:
        events, tasks = AgendaService(self.db).get_daily_agenda(user_id=user_id, agenda_date=agenda_date)
        busy_events = sorted(events, key=lambda event: event.starts_at)
        free_slots = DailySummaryService(self.db)._calculate_free_slots(agenda_date, day_start, day_end, busy_events)
        plan_preview = self.build_daily_plan(
            user_id=user_id,
            agenda_date=agenda_date,
            day_start=day_start,
            day_end=day_end,
            min_break_minutes=min_break_minutes,
        )
        return {
            "date": agenda_date.isoformat(),
            "user": {"id": str(user_id), "email": user_email},
            "planning_window": {
                "start": day_start.isoformat(),
                "end": day_end.isoformat(),
                "min_break_minutes": min_break_minutes,
            },
            "events": [
                {
                    "id": str(event.id),
                    "title": event.title,
                    "starts_at": event.starts_at.isoformat(),
                    "ends_at": event.ends_at.isoformat(),
                    "location": event.location,
                    "provider_name": str(event.provider_name),
                    "calendar_name": getattr(event, "external_calendar_name", None),
                }
                for event in busy_events
            ],
            "tasks": [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "notes": task.notes,
                    "due_at": task.due_at.isoformat() if task.due_at else None,
                    "is_completed": task.is_completed,
                    "priority": getattr(task, "priority", "medium"),
                    "estimated_duration_minutes": getattr(task, "estimated_duration_minutes", 60),
                    "provider_name": task.provider_name,
                }
                for task in tasks
                if not task.is_completed
            ],
            "free_slots": [
                {
                    "start": slot.start.isoformat(),
                    "end": slot.end.isoformat(),
                    "duration_minutes": slot.duration_minutes,
                    "label": f"{_format_clock(slot.start)}-{_format_clock(slot.end)}",
                }
                for slot in free_slots
            ],
            "rule_based_plan_preview": self._json_safe(plan_preview),
        }

    def build_daily_plan(
        self,
        *,
        user_id: UUID,
        agenda_date: date,
        day_start: time = time(hour=8),
        day_end: time = time(hour=20),
        min_break_minutes: int = 15,
    ) -> dict:
        events, tasks = AgendaService(self.db).get_daily_agenda(user_id=user_id, agenda_date=agenda_date)
        busy_events = sorted(events, key=lambda event: event.starts_at)
        free_slots = DailySummaryService(self.db)._calculate_free_slots(agenda_date, day_start, day_end, busy_events)

        open_tasks = [task for task in tasks if not task.is_completed]
        sorted_tasks = sorted(open_tasks, key=self._task_sort_key)

        available_slots = [FreeSlot(start=slot.start, end=slot.end) for slot in free_slots]
        planned: list[dict] = []
        unscheduled: list[dict] = []

        for task in sorted_tasks:
            duration = self._safe_duration(task)
            placement = self._place_task(task, duration, available_slots, min_break_minutes)
            if placement is None:
                unscheduled.append(
                    {
                        "task_id": task.id,
                        "title": task.title,
                        "priority": task.priority,
                        "due_at": task.due_at,
                        "estimated_duration_minutes": duration,
                        "reason": "No free slot long enough inside the planning window.",
                    }
                )
                continue

            scheduled_start, scheduled_end, slot_index = placement
            planned.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "priority": task.priority,
                    "due_at": task.due_at,
                    "estimated_duration_minutes": duration,
                    "scheduled_start": scheduled_start,
                    "scheduled_end": scheduled_end,
                    "source": "rule_based_planner",
                }
            )

            next_start = scheduled_end + timedelta(minutes=min_break_minutes)
            current_slot = available_slots[slot_index]
            if next_start >= current_slot.end:
                available_slots.pop(slot_index)
            else:
                available_slots[slot_index] = FreeSlot(start=next_start, end=current_slot.end)

        planned = sorted(planned, key=lambda item: item["scheduled_start"])
        return {
            "date": agenda_date,
            "planning_window": {
                "start": day_start.isoformat(),
                "end": day_end.isoformat(),
                "min_break_minutes": min_break_minutes,
            },
            "stats": {
                "event_count": len(busy_events),
                "task_count": len(open_tasks),
                "planned_task_count": len(planned),
                "unscheduled_task_count": len(unscheduled),
                "free_slot_count": len(free_slots),
            },
            "free_slots": [
                {
                    "start": slot.start,
                    "end": slot.end,
                    "duration_minutes": slot.duration_minutes,
                    "label": f"{_format_clock(slot.start)}-{_format_clock(slot.end)}",
                }
                for slot in free_slots
            ],
            "planned_tasks": planned,
            "unscheduled_tasks": unscheduled,
            "assistant_message": self._build_assistant_message(planned, unscheduled),
        }

    def save_plan(self, *, user_id: UUID, plan_date: date, plan_payload: dict, source: str = "n8n_rule_based", status: str = "generated") -> PlanningResult:
        result = PlanningResult(
            user_id=user_id,
            plan_date=plan_date,
            source=source,
            status=status,
            plan_payload=plan_payload,
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get_latest_plan(self, *, user_id: UUID, plan_date: date) -> PlanningResult | None:
        return self.db.scalar(
            select(PlanningResult)
            .where(PlanningResult.user_id == user_id)
            .where(PlanningResult.plan_date == plan_date)
            .order_by(desc(PlanningResult.created_at))
        )

    def _task_sort_key(self, task: TaskItem) -> tuple:
        priority = _PRIORITY_WEIGHT.get(task.priority or "medium", 2)
        due_at = task.due_at or datetime.max
        return (priority, due_at, -self._safe_duration(task), task.title.lower())

    def _safe_duration(self, task: TaskItem) -> int:
        value = getattr(task, "estimated_duration_minutes", None) or 60
        return max(15, min(int(value), 480))

    def _place_task(
        self,
        task: TaskItem,
        duration_minutes: int,
        slots: list[FreeSlot],
        min_break_minutes: int,
    ) -> tuple[datetime, datetime, int] | None:
        for index, slot in enumerate(slots):
            if slot.duration_minutes >= duration_minutes:
                scheduled_start = slot.start
                scheduled_end = scheduled_start + timedelta(minutes=duration_minutes)
                return scheduled_start, scheduled_end, index
        return None

    def _build_assistant_message(self, planned: list[dict], unscheduled: list[dict]) -> str:
        if not planned and not unscheduled:
            return "You have no open tasks to schedule for this day."
        if planned and not unscheduled:
            return f"I scheduled {len(planned)} task(s) into your free time."
        if planned and unscheduled:
            return f"I scheduled {len(planned)} task(s), but {len(unscheduled)} task(s) did not fit into your free slots."
        return f"None of your {len(unscheduled)} task(s) fit into the current planning window."

    def _json_safe(self, value):
        if isinstance(value, dict):
            return {key: self._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        return value
