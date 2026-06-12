from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    notes: str | None = None
    due_at: datetime | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    due_at: datetime | None = None
    is_completed: bool | None = None

class TaskRead(BaseModel):
    id: uuid.UUID
    title: str
    notes: str | None = None
    due_at: datetime | None = None
    is_completed: bool
    provider_name: str
    model_config = {"from_attributes": True}
