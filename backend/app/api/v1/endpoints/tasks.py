from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.crud.tasks import TaskRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.tasks import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    return TaskRepository(db).create_local_task(user_id=current_user.id, payload=payload)


@router.get("", response_model=list[TaskRead])
def list_tasks(
    include_completed: bool = False,
    due_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskRead]:
    return TaskRepository(db).list_tasks(
        user_id=current_user.id,
        include_completed=include_completed,
        due_date=due_date,
    )


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    repo = TaskRepository(db)
    task = repo.get_owned_task(user_id=current_user.id, task_id=task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return repo.update_task(task=task, payload=payload)


@router.post("/{task_id}/complete", response_model=TaskRead)
def complete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    repo = TaskRepository(db)
    task = repo.get_owned_task(user_id=current_user.id, task_id=task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return repo.update_task(task=task, payload=TaskUpdate(is_completed=True))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    repo = TaskRepository(db)
    task = repo.get_owned_task(user_id=current_user.id, task_id=task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    repo.delete_task(task)
