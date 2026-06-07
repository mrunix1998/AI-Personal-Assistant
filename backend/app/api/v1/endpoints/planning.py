from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_access_token, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.planning import (
    DailyPlanRead,
    PlanningContextRead,
    PlanningResultRead,
    PlanningResultSaveRequest,
    PlanningWorkflowResponse,
)
from app.services.n8n_service import N8nWorkflowService
from app.services.planning_service import PlanningService

router = APIRouter(prefix="/planning", tags=["planning"])


@router.get("/daily", response_model=DailyPlanRead)
def get_daily_plan(
    agenda_date: date,
    day_start: time = time(hour=8),
    day_end: time = time(hour=20),
    min_break_minutes: int = Query(default=15, ge=0, le=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyPlanRead:
    return PlanningService(db).build_daily_plan(
        user_id=current_user.id,
        agenda_date=agenda_date,
        day_start=day_start,
        day_end=day_end,
        min_break_minutes=min_break_minutes,
    )


@router.get("/context", response_model=PlanningContextRead)
def get_planning_context(
    agenda_date: date,
    day_start: time = time(hour=8),
    day_end: time = time(hour=20),
    min_break_minutes: int = Query(default=15, ge=0, le=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return PlanningService(db).build_context(
        user_id=current_user.id,
        user_email=current_user.email,
        agenda_date=agenda_date,
        day_start=day_start,
        day_end=day_end,
        min_break_minutes=min_break_minutes,
    )


@router.post("/workflow", response_model=PlanningWorkflowResponse)
async def trigger_ai_planning_workflow(
    agenda_date: date,
    day_start: time = time(hour=8),
    day_end: time = time(hour=20),
    min_break_minutes: int = Query(default=15, ge=0, le=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    access_token: str = Depends(get_current_access_token),
) -> PlanningWorkflowResponse:
    planning_service = PlanningService(db)
    context = planning_service.build_context(
        user_id=current_user.id,
        user_email=current_user.email,
        agenda_date=agenda_date,
        day_start=day_start,
        day_end=day_end,
        min_break_minutes=min_break_minutes,
    )

    try:
        n8n_response = await N8nWorkflowService().trigger_ai_planning_workflow(
            user_id=current_user.id,
            user_email=current_user.email,
            agenda_date=agenda_date,
            access_token=access_token,
            planning_context=context,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not trigger n8n AI planning workflow: {exc}",
        ) from exc

    saved_plan_id = None
    if isinstance(n8n_response, dict):
        plan_payload = n8n_response.get("plan") or n8n_response
        saved = planning_service.save_plan(
            user_id=current_user.id,
            plan_date=agenda_date,
            plan_payload=plan_payload,
            source=str(n8n_response.get("source", "n8n_rule_based")),
            status=str(n8n_response.get("status", "generated")),
        )
        saved_plan_id = saved.id

    return PlanningWorkflowResponse(
        status="triggered",
        user_id=current_user.id,
        agenda_date=agenda_date,
        n8n_response=n8n_response if isinstance(n8n_response, dict) else {"raw_response": str(n8n_response)},
        saved_plan_id=saved_plan_id,
    )


@router.post("/save", response_model=PlanningResultRead)
def save_planning_result(
    payload: PlanningResultSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlanningResultRead:
    return PlanningService(db).save_plan(
        user_id=current_user.id,
        plan_date=payload.plan_date,
        source=payload.source,
        status=payload.status,
        plan_payload=payload.plan_payload,
    )


@router.get("/latest", response_model=PlanningResultRead | None)
def get_latest_planning_result(
    agenda_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlanningResultRead | None:
    return PlanningService(db).get_latest_plan(user_id=current_user.id, plan_date=agenda_date)
