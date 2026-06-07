from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

AgendaItemType = Literal["meeting", "task"]
AgendaChannel = Literal["web", "email", "telegram", "whatsapp"]


class UnifiedAgendaItem(BaseModel):
    id: UUID
    item_type: AgendaItemType
    source: str
    title: str
    description: str | None = None
    location: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    due_at: datetime | None = None
    is_completed: bool | None = None
    calendar_name: str | None = None
    external_id: str | None = None
    sort_at: datetime | None = None


class UnifiedAgendaStats(BaseModel):
    meeting_count: int
    task_count: int
    overdue_task_count: int
    completed_task_count: int
    total_count: int


class ChannelMessage(BaseModel):
    channel: AgendaChannel
    subject: str | None = None
    message: str
    payload: dict[str, Any] = {}


class UnifiedDailyAgendaRead(BaseModel):
    date: str
    timezone: str = "Europe/Berlin"
    stats: UnifiedAgendaStats
    meetings: list[UnifiedAgendaItem]
    tasks: list[UnifiedAgendaItem]
    timeline: list[UnifiedAgendaItem]
    channel_messages: list[ChannelMessage]


class UnifiedAgendaWorkflowResponse(BaseModel):
    status: str
    user_id: UUID
    agenda_date: str
    n8n_response: Any
