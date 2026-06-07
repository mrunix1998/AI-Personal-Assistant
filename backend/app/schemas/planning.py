from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class PlanningFreeSlotRead(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: int
    label: str


class PlannedTaskRead(BaseModel):
    task_id: UUID
    title: str
    priority: str
    due_at: datetime | None
    estimated_duration_minutes: int
    scheduled_start: datetime
    scheduled_end: datetime
    source: str = "rule_based_planner"


class UnscheduledTaskRead(BaseModel):
    task_id: UUID
    title: str
    priority: str
    due_at: datetime | None
    estimated_duration_minutes: int
    reason: str


class DailyPlanRead(BaseModel):
    date: date
    planning_window: dict
    stats: dict
    free_slots: list[PlanningFreeSlotRead]
    planned_tasks: list[PlannedTaskRead]
    unscheduled_tasks: list[UnscheduledTaskRead]
    assistant_message: str


class PlanningContextRead(BaseModel):
    date: date
    user: dict
    planning_window: dict
    events: list[dict]
    tasks: list[dict]
    free_slots: list[dict]
    rule_based_plan_preview: dict


class PlanningWorkflowResponse(BaseModel):
    status: str
    user_id: UUID
    agenda_date: date
    n8n_response: dict
    saved_plan_id: UUID | None = None


class PlanningResultSaveRequest(BaseModel):
    plan_date: date
    source: str = "n8n_rule_based"
    status: str = "generated"
    plan_payload: dict


class PlanningResultRead(BaseModel):
    id: UUID
    plan_date: date
    source: str
    status: str
    plan_payload: dict
    created_at: datetime

    class Config:
        from_attributes = True
