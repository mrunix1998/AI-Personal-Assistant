from __future__ import annotations

import uuid
from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task_item import TaskItem
from app.schemas.tasks import TaskCreate, TaskUpdate


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_local_task(self, user_id: UUID, payload: TaskCreate) -> TaskItem:
        task = TaskItem(
            user_id=user_id,
            connected_account_id=None,
            provider_name="local_tasks",
            external_task_id=f"local:{uuid.uuid4()}",
            title=payload.title,
            notes=payload.notes,
            due_at=payload.due_at,
            is_completed=False,
            estimated_duration_minutes=payload.estimated_duration_minutes,
            priority=payload.priority,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def list_tasks(
        self,
        user_id: UUID,
        include_completed: bool = False,
        due_date: date | None = None,
    ) -> list[TaskItem]:
        stmt = select(TaskItem).where(TaskItem.user_id == user_id)

        if not include_completed:
            stmt = stmt.where(TaskItem.is_completed == False)  # noqa: E712

        if due_date is not None:
            start = datetime.combine(due_date, time.min)
            end = datetime.combine(due_date, time.max)
            stmt = stmt.where(TaskItem.due_at != None).where(TaskItem.due_at >= start).where(TaskItem.due_at <= end)  # noqa: E711

        stmt = stmt.order_by(TaskItem.is_completed.asc(), TaskItem.due_at.asc().nulls_last())
        return list(self.db.scalars(stmt).all())

    def get_owned_task(self, user_id: UUID, task_id: UUID) -> TaskItem | None:
        return self.db.scalar(select(TaskItem).where(TaskItem.user_id == user_id).where(TaskItem.id == task_id))

    def update_task(self, task: TaskItem, payload: TaskUpdate) -> TaskItem:
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete_task(self, task: TaskItem) -> None:
        self.db.delete(task)
        self.db.commit()
