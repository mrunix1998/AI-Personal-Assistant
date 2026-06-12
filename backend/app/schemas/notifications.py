from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
import uuid

class TelegramConnectManual(BaseModel):
    chat_id: str
    display_name: str | None = None

class TelegramBotTokenConfig(BaseModel):
    bot_token: str

class EmailConnectManual(BaseModel):
    email: EmailStr
    display_name: str | None = None

class SmtpConfig(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from_email: EmailStr

class NotificationChannelRead(BaseModel):
    id: uuid.UUID
    channel: str
    destination: str
    display_name: str | None
    is_enabled: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class ProviderSecretRead(BaseModel):
    provider_name: str
    secret_name: str

class NotificationCreate(BaseModel):
    title: str
    message: str
    source: str = "system"
    channel: str = "web"

class NotificationRead(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    source: str
    channel: str
    status: str
    agenda_date: datetime | None
    created_at: datetime
    read_at: datetime | None
    model_config = {"from_attributes": True}

class WebPushSubscriptionCreate(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None = None

class WebPushSubscriptionRead(BaseModel):
    id: uuid.UUID
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None
    is_enabled: bool
    created_at: datetime
    model_config = {"from_attributes": True}
