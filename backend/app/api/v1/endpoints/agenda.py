from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_access_token, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.unified_agenda_service import UnifiedAgendaService
from app.services.n8n_service import N8nWorkflowService
router=APIRouter(prefix="/agenda", tags=["agenda"])
@router.get("/unified-daily")
def unified_daily(agenda_date:date, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    return UnifiedAgendaService(db).build_daily_agenda(current_user.id, agenda_date)
@router.post("/unified-daily/workflow")
async def unified_daily_workflow(agenda_date:date, db:Session=Depends(get_db), current_user:User=Depends(get_current_user), access_token:str=Depends(get_current_access_token)):
    agenda=UnifiedAgendaService(db).build_daily_agenda(current_user.id,agenda_date)
    res=await N8nWorkflowService().trigger("unified-agenda-notification", {"user_id":str(current_user.id),"user_email":current_user.email,"access_token":access_token,"agenda_date":agenda_date.isoformat(),"unified_agenda":agenda.model_dump(mode="json")})
    return {"status":"triggered","n8n_response":res}
@router.get("/daily-summary")
def daily_summary(agenda_date:date, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    agenda=UnifiedAgendaService(db).build_daily_agenda(current_user.id,agenda_date)
    return {"headline": f"Daily agenda for {agenda_date}", "summary": agenda.channel_messages[0].message, "stats": agenda.stats, "timeline": agenda.timeline}
