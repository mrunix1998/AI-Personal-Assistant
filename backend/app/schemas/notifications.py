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


class EmailConnectManual(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)


class EmailSMTPConfigCreate(BaseModel):
    smtp_host: str = Field(min_length=1, max_length=255, examples=["smtp.gmail.com"])
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = Field(min_length=1, max_length=255)
    smtp_password: str = Field(min_length=1)
    smtp_from_email: str = Field(min_length=3, max_length=255)
    smtp_use_tls: bool = True
    display_name: str | None = Field(default="SMTP Email Sender", max_length=255)


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


class EmailDailyAgendaResponse(BaseModel):
    status: str
    channel_id: UUID | None = None
    agenda_date: str
    n8n_response: Any | None = None
    email_response: Any | None = None
