from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReminderRead(BaseModel):
    id: UUID
    title: str
    message: str
    scheduled_for: datetime
    status: str

    model_config = {"from_attributes": True}


class GenerateRemindersResponse(BaseModel):
    agenda_date: str
    lead_minutes: int
    created_count: int
    skipped_count: int
    reminders: list[ReminderRead]


class ReminderSimulationResponse(BaseModel):
    sent_count: int
    reminders: list[ReminderRead]
