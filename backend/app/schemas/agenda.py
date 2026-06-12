from datetime import datetime, date
from pydantic import BaseModel
import uuid

class MeetingItem(BaseModel):
    id: uuid.UUID
    title: str
    source: str
    calendar_name: str | None = None
    starts_at: datetime
    ends_at: datetime
    location: str | None = None

class AgendaTaskItem(BaseModel):
    id: uuid.UUID
    title: str
    source: str
    due_at: datetime | None = None
    is_completed: bool
    is_overdue: bool = False

class ChannelMessage(BaseModel):
    channel: str
    subject: str | None = None
    message: str
    payload: dict

class UnifiedDailyAgenda(BaseModel):
    date: date
    timezone: str = "Europe/Berlin"
    stats: dict
    meetings: list[MeetingItem]
    tasks: list[AgendaTaskItem]
    timeline: list[dict]
    channel_messages: list[ChannelMessage]
