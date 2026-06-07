from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    notes: str | None = None
    due_at: datetime | None = None
    estimated_duration_minutes: int = Field(default=60, ge=15, le=480)
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    notes: str | None = None
    due_at: datetime | None = None
    is_completed: bool | None = None
    estimated_duration_minutes: int | None = Field(default=None, ge=15, le=480)
    priority: str | None = Field(default=None, pattern="^(low|medium|high|urgent)$")


class TaskRead(BaseModel):
    id: UUID
    title: str
    notes: str | None
    due_at: datetime | None
    is_completed: bool
    provider_name: str
    estimated_duration_minutes: int
    priority: str

    class Config:
        from_attributes = True
