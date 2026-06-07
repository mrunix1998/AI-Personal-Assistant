from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_access_token, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DailyAgendaRead
from app.schemas.daily_summary import DailySummaryRead
from app.schemas.n8n import N8nDailySummaryTriggerResponse
from app.services.agenda_service import AgendaService
from app.services.daily_summary_service import DailySummaryService
from app.services.n8n_service import N8nWorkflowService

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


@router.get("/daily-summary", response_model=DailySummaryRead)
def get_daily_summary(
    agenda_date: date,
    day_start: time = time(hour=8),
    day_end: time = time(hour=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailySummaryRead:
    return DailySummaryService(db).build_summary(
        user_id=current_user.id,
        agenda_date=agenda_date,
        day_start=day_start,
        day_end=day_end,
    )



@router.post("/daily-summary/workflow", response_model=N8nDailySummaryTriggerResponse)
async def trigger_daily_summary_workflow(
    agenda_date: date,
    current_user: User = Depends(get_current_user),
    access_token: str = Depends(get_current_access_token),
) -> N8nDailySummaryTriggerResponse:
    try:
        n8n_response = await N8nWorkflowService().trigger_daily_summary_workflow(
            user_id=current_user.id,
            user_email=current_user.email,
            agenda_date=agenda_date,
            access_token=access_token,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not trigger n8n daily summary workflow: {exc}",
        ) from exc

    return N8nDailySummaryTriggerResponse(
        status="triggered",
        user_id=current_user.id,
        agenda_date=agenda_date,
        n8n_response=n8n_response,
    )
