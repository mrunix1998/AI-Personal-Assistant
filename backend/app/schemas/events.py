import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class EventCreate(BaseModel):
    provider_name: str = Field(min_length=1)
    external_event_id: str
    calendar_id: str | None = None
    calendar_name: str | None = None
    title: str
    description: str | None = None
    location: str | None = None
    starts_at: datetime
    ends_at: datetime
    timezone: str | None = "Europe/Berlin"

class EventRead(BaseModel):
    id: uuid.UUID
    provider_name: str
    external_event_id: str
    calendar_id: str | None
    calendar_name: str | None
    title: str
    description: str | None
    location: str | None
    starts_at: datetime
    ends_at: datetime
    timezone: str | None
    model_config = {"from_attributes": True}

class EventImportRequest(BaseModel):
    provider_name: str
    events: list[EventCreate]
