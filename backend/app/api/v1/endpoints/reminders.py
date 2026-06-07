from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ReminderStatus
from app.models.user import User
from app.schemas.reminders import GenerateRemindersResponse, ReminderRead, ReminderSimulationResponse
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("/generate", response_model=GenerateRemindersResponse)
def generate_reminders_for_day(
    agenda_date: date = Query(...),
    lead_minutes: int = Query(30, ge=1, le=1440),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    created, skipped_count = ReminderService(db).generate_event_reminders(
        user_id=current_user.id,
        agenda_date=agenda_date,
        lead_minutes=lead_minutes,
    )
    return {
        "agenda_date": agenda_date.isoformat(),
        "lead_minutes": lead_minutes,
        "created_count": len(created),
        "skipped_count": skipped_count,
        "reminders": created,
    }


@router.get("", response_model=list[ReminderRead])
def list_reminders(
    status: ReminderStatus | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ReminderService(db).list_reminders(user_id=current_user.id, status=status)


@router.post("/simulate-send-due", response_model=ReminderSimulationResponse)
def simulate_send_due_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sent = ReminderService(db).simulate_due_reminders(user_id=current_user.id)
    return {"sent_count": len(sent), "reminders": sent}
