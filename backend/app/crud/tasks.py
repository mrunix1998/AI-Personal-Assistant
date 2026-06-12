import uuid
from datetime import date, datetime, time, timezone
from sqlalchemy.orm import Session
from app.models.task_item import TaskItem
from app.schemas.tasks import TaskCreate, TaskUpdate

class TaskRepository:
    def __init__(self, db: Session): self.db = db
    def create_local_task(self, user_id, payload: TaskCreate) -> TaskItem:
        task = TaskItem(user_id=user_id, connected_account_id=None, provider_name="local_tasks", external_task_id=f"local:{uuid.uuid4()}", title=payload.title, notes=payload.notes, due_at=payload.due_at, is_completed=False)
        self.db.add(task); self.db.commit(); self.db.refresh(task); return task
    def list_for_user(self, user_id, include_completed: bool = True) -> list[TaskItem]:
        q = self.db.query(TaskItem).filter(TaskItem.user_id == user_id)
        if not include_completed: q = q.filter(TaskItem.is_completed == False)  # noqa
        return q.order_by(TaskItem.due_at.asc().nullslast()).all()
    def list_for_date(self, user_id, agenda_date: date) -> list[TaskItem]:
        start = datetime.combine(agenda_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(agenda_date, time.max, tzinfo=timezone.utc)
        return self.db.query(TaskItem).filter(TaskItem.user_id == user_id, ((TaskItem.due_at >= start) & (TaskItem.due_at <= end)) | (TaskItem.due_at == None)).all()  # noqa
    def update(self, user_id, task_id, payload: TaskUpdate) -> TaskItem | None:
        task = self.db.query(TaskItem).filter(TaskItem.id == task_id, TaskItem.user_id == user_id).first()
        if not task: return None
        data = payload.model_dump(exclude_unset=True)
        for k,v in data.items(): setattr(task,k,v)
        self.db.commit(); self.db.refresh(task); return task
    def delete(self, user_id, task_id) -> bool:
        task = self.db.query(TaskItem).filter(TaskItem.id == task_id, TaskItem.user_id == user_id).first()
        if not task: return False
        self.db.delete(task); self.db.commit(); return True
