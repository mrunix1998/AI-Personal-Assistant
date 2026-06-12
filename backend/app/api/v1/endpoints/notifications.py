import uuid
from datetime import date, datetime, timezone
import smtplib
from email.message import EmailMessage
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_access_token, get_current_user
from app.crud.notification_channels import NotificationChannelRepository
from app.crud.notifications import NotificationRepository
from app.crud.provider_secrets import ProviderSecretRepository
from app.crud.web_push import WebPushRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.notifications import *
from app.services.n8n_service import N8nWorkflowService
from app.services.unified_agenda_service import UnifiedAgendaService
router=APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/channels", response_model=list[NotificationChannelRead])
def channels(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)): return NotificationChannelRepository(db).list_for_user(current_user.id)

@router.get("/secrets", response_model=list[ProviderSecretRead])
def secrets(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    return [ProviderSecretRead(provider_name=s.provider, secret_name=s.key) for s in ProviderSecretRepository(db).list_for_user(current_user.id)]

@router.post("/telegram/connect-manual", response_model=NotificationChannelRead, status_code=201)
def telegram_connect(payload:TelegramConnectManual, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    return NotificationChannelRepository(db).upsert(current_user.id,"telegram",payload.chat_id,payload.display_name)
@router.post("/telegram/bot-token")
def telegram_token(payload:TelegramBotTokenConfig, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    ProviderSecretRepository(db).upsert(current_user.id,"telegram","bot_token",payload.bot_token); return {"status":"saved","provider":"telegram","secret":"bot_token"}
@router.post("/telegram/send-daily-agenda")
async def telegram_send(agenda_date:date, db:Session=Depends(get_db), current_user:User=Depends(get_current_user), access_token:str=Depends(get_current_access_token)):
    chan=NotificationChannelRepository(db).get_enabled_channel(current_user.id,"telegram")
    if not chan: raise HTTPException(400,"Telegram is not connected yet")
    token=ProviderSecretRepository(db).get_value(current_user.id,"telegram","bot_token")
    if not token: raise HTTPException(400,"Telegram bot_token is missing")
    agenda=UnifiedAgendaService(db).build_daily_agenda(current_user.id,agenda_date)
    msg=next(x.message for x in agenda.channel_messages if x.channel=="telegram")
    res=await N8nWorkflowService().telegram_daily({"telegram_bot_token":token,"telegram_chat_id":chan.destination,"telegram_message":msg,"agenda_date":agenda_date.isoformat(),"user_id":str(current_user.id),"user_email":current_user.email,"access_token":access_token})
    return {"status":"sent","channel_id":str(chan.id),"agenda_date":agenda_date.isoformat(),"n8n_response":res}

@router.post("/email/connect-manual", response_model=NotificationChannelRead, status_code=201)
def email_connect(payload:EmailConnectManual, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    return NotificationChannelRepository(db).upsert(current_user.id,"email",payload.email,payload.display_name)
@router.post("/email/smtp-config")
def email_smtp(payload:SmtpConfig, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    repo=ProviderSecretRepository(db)
    for k,v in payload.model_dump().items(): repo.upsert(current_user.id,"email",k,str(v))
    return {"status":"saved","provider":"email","secrets":["smtp_host","smtp_port","smtp_username","smtp_password","smtp_from_email"]}
@router.post("/email/send-daily-agenda")
async def email_send(agenda_date:date, db:Session=Depends(get_db), current_user:User=Depends(get_current_user), access_token:str=Depends(get_current_access_token)):
    chan=NotificationChannelRepository(db).get_enabled_channel(current_user.id,"email")
    if not chan: raise HTTPException(400,"Email channel is not connected yet")
    repo=ProviderSecretRepository(db); required=["smtp_host","smtp_port","smtp_username","smtp_password","smtp_from_email"]; secrets={k:repo.get_value(current_user.id,"email",k) for k in required}
    missing=[k for k,v in secrets.items() if not v]
    if missing: raise HTTPException(400,f"Email SMTP secret '{missing[0]}' is missing. Save SMTP config with /notifications/email/smtp-config.")
    agenda=UnifiedAgendaService(db).build_daily_agenda(current_user.id,agenda_date)
    email_msg=next(x for x in agenda.channel_messages if x.channel=="email")
    msg=EmailMessage()
    msg["From"]=secrets["smtp_from_email"]
    msg["To"]=chan.destination
    msg["Subject"]=email_msg.subject or f"Daily agenda for {agenda_date}"
    msg.set_content(email_msg.message)
    with smtplib.SMTP(secrets["smtp_host"], int(secrets["smtp_port"])) as smtp:
        smtp.starttls()
        smtp.login(secrets["smtp_username"], secrets["smtp_password"])
        smtp.send_message(msg)
    return {"status":"sent","channel_id":str(chan.id),"agenda_date":agenda_date.isoformat(),"email_response":{"ok":True,"source":"backend_smtp"}}
@router.post("/email/send-direct")
async def email_direct(to_email:str, subject:str, message:str, db:Session=Depends(get_db), current_user:User=Depends(get_current_user), access_token:str=Depends(get_current_access_token)):
    repo=ProviderSecretRepository(db); secrets={k:repo.get_value(current_user.id,"email",k) for k in ["smtp_host","smtp_port","smtp_username","smtp_password","smtp_from_email"]}
    msg=EmailMessage(); msg["From"]=secrets["smtp_from_email"]; msg["To"]=to_email; msg["Subject"]=subject; msg.set_content(message)
    with smtplib.SMTP(secrets["smtp_host"], int(secrets["smtp_port"])) as smtp:
        smtp.starttls(); smtp.login(secrets["smtp_username"], secrets["smtp_password"]); smtp.send_message(msg)
    return {"status":"sent","email_response":{"ok":True,"source":"backend_smtp"}}

@router.post("/center", response_model=NotificationRead)
def create_notification(payload:NotificationCreate, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    return NotificationRepository(db).create(current_user.id,payload.title,payload.message,payload.source,payload.channel)
@router.get("/center", response_model=list[NotificationRead])
def list_notifications(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)): return NotificationRepository(db).list_for_user(current_user.id)
@router.post("/center/daily-agenda")
def daily_notification(agenda_date:date, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    agenda=UnifiedAgendaService(db).build_daily_agenda(current_user.id,agenda_date); web_msg=next(x for x in agenda.channel_messages if x.channel=="web")
    dt=datetime.combine(agenda_date, datetime.min.time(), tzinfo=timezone.utc)
    notif=NotificationRepository(db).create(current_user.id,web_msg.subject or "Daily Agenda",web_msg.message,"unified_agenda","web",dt)
    subs=WebPushRepository(db).list_for_user(current_user.id)
    return {"status":"created","notification":NotificationRead.model_validate(notif),"web_push":{"status":"simulated","subscription_count":len(subs),"title":notif.title,"message":notif.message}}
@router.post("/center/{notification_id}/read", response_model=NotificationRead)
def read_notification(notification_id:uuid.UUID, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    obj=NotificationRepository(db).mark_read(current_user.id,notification_id)
    if not obj: raise HTTPException(404,"Notification not found")
    return obj
@router.post("/center/read-all")
def read_all(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)): return {"updated_count":NotificationRepository(db).mark_all_read(current_user.id)}
@router.delete("/center/{notification_id}")
def delete_notification(notification_id:uuid.UUID): return {"deleted":False,"detail":"Delete not implemented in MVP"}

@router.post("/web-push/subscriptions", response_model=WebPushSubscriptionRead)
def web_push_subscribe(payload:WebPushSubscriptionCreate, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)): return WebPushRepository(db).upsert(current_user.id,payload)
@router.get("/web-push/subscriptions", response_model=list[WebPushSubscriptionRead])
def web_push_list(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)): return WebPushRepository(db).list_for_user(current_user.id)
@router.delete("/web-push/subscriptions/{subscription_id}")
def web_push_delete(subscription_id:uuid.UUID, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)): return {"deleted":WebPushRepository(db).delete(current_user.id,subscription_id)}
