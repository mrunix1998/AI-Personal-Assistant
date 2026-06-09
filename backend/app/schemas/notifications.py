from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

NotificationChannelName = Literal["telegram", "email", "whatsapp"]


class NotificationChannelCreate(BaseModel):
    channel: NotificationChannelName = "telegram"
    destination: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    is_enabled: bool = True


class TelegramConnectManual(BaseModel):
    chat_id: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)


class NotificationChannelRead(BaseModel):
    id: UUID
    channel: str
    destination: str
    display_name: str | None
    is_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TelegramDailyAgendaResponse(BaseModel):
    status: str
    channel_id: UUID | None = None
    agenda_date: str
    n8n_response: Any
