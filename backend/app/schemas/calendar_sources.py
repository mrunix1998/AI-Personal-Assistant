from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class CalendarProviderRead(BaseModel):
    provider: str
    label: str
    connection_type: str
    status: str


class IcsCalendarSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    ics_url: HttpUrl
    provider: str = Field(default="generic_ics", pattern="^(generic_ics|apple_ics)$")


class CalendarSourceRead(BaseModel):
    id: UUID
    provider: str
    name: str
    external_id: str
    is_enabled: bool
    last_synced_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CalendarSourceTestResponse(BaseModel):
    status: str
    provider: str
    name: str
    event_count_preview: int = 0
    message: str


class CalendarSyncResponse(BaseModel):
    status: str
    provider: str
    source_id: UUID | None = None
    synced_count: int
    deleted_count: int = 0


class CalendarEventRead(BaseModel):
    id: UUID
    provider_name: str
    external_event_id: str
    title: str
    description: str | None = None
    location: str | None = None
    starts_at: datetime
    ends_at: datetime
    timezone: str | None = None

    model_config = {"from_attributes": True}
