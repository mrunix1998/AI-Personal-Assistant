from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_access_token, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.unified_agenda import UnifiedAgendaWorkflowResponse, UnifiedDailyAgendaRead
from app.services.n8n_service import N8nWorkflowService
from app.services.unified_agenda_service import UnifiedAgendaService

router = APIRouter(prefix="/agenda", tags=["unified-agenda"])


@router.get("/unified-daily", response_model=UnifiedDailyAgendaRead)
def get_unified_daily_agenda(
    agenda_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnifiedDailyAgendaRead:
    return UnifiedAgendaService(db).build_daily_agenda(
        user_id=current_user.id,
        agenda_date=agenda_date,
    )


@router.post("/unified-daily/workflow", response_model=UnifiedAgendaWorkflowResponse)
async def trigger_unified_daily_agenda_workflow(
    agenda_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    access_token: str = Depends(get_current_access_token),
) -> UnifiedAgendaWorkflowResponse:
    agenda = UnifiedAgendaService(db).build_daily_agenda(
        user_id=current_user.id,
        agenda_date=agenda_date,
    )
    try:
        n8n_response = await N8nWorkflowService().trigger_unified_agenda_workflow(
            user_id=current_user.id,
            user_email=current_user.email,
            agenda_date=agenda_date,
            access_token=access_token,
            unified_agenda=agenda.model_dump(mode="json"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not trigger n8n unified agenda workflow: {exc}",
        ) from exc

    return UnifiedAgendaWorkflowResponse(
        status="triggered",
        user_id=current_user.id,
        agenda_date=agenda_date.isoformat(),
        n8n_response=n8n_response,
    )
