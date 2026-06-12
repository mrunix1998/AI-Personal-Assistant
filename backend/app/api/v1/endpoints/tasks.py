import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.crud.tasks import TaskRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.tasks import TaskCreate, TaskRead, TaskUpdate
router=APIRouter(prefix="/tasks", tags=["tasks"])
@router.post("", response_model=TaskRead)
def create_task(payload:TaskCreate, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)): return TaskRepository(db).create_local_task(current_user.id,payload)
@router.get("", response_model=list[TaskRead])
def list_tasks(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)): return TaskRepository(db).list_for_user(current_user.id)
@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id:uuid.UUID,payload:TaskUpdate,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    obj=TaskRepository(db).update(current_user.id,task_id,payload)
    if not obj: raise HTTPException(404,"Task not found")
    return obj
@router.delete("/{task_id}")
def delete_task(task_id:uuid.UUID,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)): return {"deleted":TaskRepository(db).delete(current_user.id,task_id)}
