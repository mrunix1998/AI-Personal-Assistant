from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ProviderNameForSecret = Literal[
    "telegram",
    "email",
    "whatsapp",
    "notion",
    "jira",
    "trello",
    "google",
    "microsoft",
]


class ProviderSecretCreate(BaseModel):
    provider: ProviderNameForSecret
    secret_key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1)
    display_name: str | None = Field(default=None, max_length=255)


class ProviderSecretRead(BaseModel):
    id: UUID
    provider: str
    secret_key: str
    display_name: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TelegramBotTokenCreate(BaseModel):
    bot_token: str = Field(min_length=20)
    display_name: str | None = Field(default="Telegram Bot Token", max_length=255)
