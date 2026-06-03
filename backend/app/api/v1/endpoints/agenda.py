from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DailyAgendaRead
from app.services.agenda_service import AgendaService

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("/daily", response_model=DailyAgendaRead)
def get_daily_agenda(
    agenda_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyAgendaRead:
    events, tasks = AgendaService(db).get_daily_agenda(
        user_id=current_user.id,
        agenda_date=agenda_date,
    )
    return DailyAgendaRead(date=agenda_date.isoformat(), events=events, tasks=tasks)
