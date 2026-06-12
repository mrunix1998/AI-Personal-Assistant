from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.unified_agenda_service import UnifiedAgendaService
router=APIRouter(prefix="/planning", tags=["planning"])
@router.get("/context")
def context(agenda_date:date, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    return UnifiedAgendaService(db).build_daily_agenda(current_user.id,agenda_date)
@router.get("/daily")
def daily(agenda_date:date, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    agenda=UnifiedAgendaService(db).build_daily_agenda(current_user.id,agenda_date)
    return {"date":agenda_date,"note":"Planning disabled by product scope. This app aggregates tasks and meetings, it does not auto-schedule tasks.","agenda":agenda}
