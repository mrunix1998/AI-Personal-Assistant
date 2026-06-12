import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.connected_account import ConnectedAccount
from app.models.user import User
from app.schemas.integrations import ConnectedAccountRead
from app.services.google_calendar_service import GoogleCalendarService
router=APIRouter(prefix="/integrations", tags=["integrations"])
@router.get("/accounts", response_model=list[ConnectedAccountRead])
def accounts(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    return db.query(ConnectedAccount).filter(ConnectedAccount.user_id==current_user.id).all()
@router.get("/google/connect")
def google_connect(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    url=GoogleCalendarService(db).build_authorization_url(current_user.id, str(uuid.uuid4()))
    return {"authorization_url":url}
@router.get("/google/callback")
async def google_callback(code:str, state:str, db:Session=Depends(get_db)):
    acc=await GoogleCalendarService(db).exchange_code_and_store(code,state)
    return {"message":"Google Calendar connected successfully","account":ConnectedAccountRead.model_validate(acc)}
@router.post("/google/sync")
async def google_sync(past_days:int=Query(30,ge=0,le=365), future_days:int=Query(30,ge=0,le=365), db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    try: return await GoogleCalendarService(db).sync(current_user.id,past_days,future_days)
    except ValueError as e: raise HTTPException(400,str(e))
    except Exception as e: raise HTTPException(502,f"Could not sync Google Calendar events: {e}")
