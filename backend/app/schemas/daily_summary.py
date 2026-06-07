from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DailySummaryStats(BaseModel):
    event_count: int
    task_count: int
    overdue_task_count: int
    free_slot_count: int
    total_free_minutes: int


class TimelineItem(BaseModel):
    id: UUID
    title: str
    start: datetime
    end: datetime
    location: str | None = None
    provider_name: str
    label: str


class FreeSlotRead(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: int
    label: str


class PriorityItem(BaseModel):
    id: UUID
    title: str
    due_at: datetime | None = None
    provider_name: str
    is_overdue: bool


class DailySummaryRead(BaseModel):
    date: str
    headline: str
    summary: str
    stats: DailySummaryStats
    timeline: list[TimelineItem]
    free_slots: list[FreeSlotRead]
    priorities: list[PriorityItem]
    suggestions: list[str]
