from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.reminder import Reminder
from app.models.user import User
from app.schemas.reminders import ReminderRead
from app.services.reminder_engine import ReminderEngine

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("/generate")
def generate(
    agenda_date: date,
    lead_minutes: int = Query(default=15, ge=1, le=1440),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ReminderEngine(db).generate_for_day(
        user_id=current_user.id,
        agenda_date=agenda_date,
        lead_minutes=lead_minutes,
    )


@router.get("", response_model=list[ReminderRead])
def list_reminders(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Reminder).filter(Reminder.user_id == current_user.id)
    if status:
        query = query.filter(Reminder.status == status)
    return query.order_by(Reminder.remind_at.asc()).all()
