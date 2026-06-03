from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CalendarEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_name: str
    external_event_id: str
    title: str
    description: str | None = None
    location: str | None = None
    starts_at: datetime
    ends_at: datetime
    timezone: str | None = None


class TaskItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_name: str
    external_task_id: str
    title: str
    notes: str | None = None
    due_at: datetime | None = None
    is_completed: bool


class DailyAgendaRead(BaseModel):
    date: str
    events: list[CalendarEventRead]
    tasks: list[TaskItemRead]
