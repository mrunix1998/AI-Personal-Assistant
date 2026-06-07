from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ProviderName, ProviderType


class ConnectedAccountRead(BaseModel):
    id: UUID
    provider_name: ProviderName
    provider_type: ProviderType
    external_account_id: str | None = None
    token_expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GoogleConnectResponse(BaseModel):
    authorization_url: str
    state: str


class GoogleCallbackResponse(BaseModel):
    message: str
    account: ConnectedAccountRead


class GoogleSyncResponse(BaseModel):
    provider: ProviderName
    synced_count: int
    deleted_count: int
    calendar_count: int | None = None
    events_by_calendar: dict[str, int] = Field(default_factory=dict)
    start_at: datetime
    end_at: datetime
