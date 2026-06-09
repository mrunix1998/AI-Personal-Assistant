from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_access_token, get_current_user
from app.crud.notification_channels import NotificationChannelRepository
from app.crud.provider_secrets import ProviderSecretRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.notifications import (
    EmailConnectManual,
    EmailDailyAgendaResponse,
    EmailSMTPConfigCreate,
    NotificationChannelCreate,
    NotificationChannelRead,
    TelegramConnectManual,
    TelegramDailyAgendaResponse,
)
from app.schemas.provider_secrets import ProviderSecretCreate, ProviderSecretRead, TelegramBotTokenCreate
from app.services.email_notification_service import EmailNotificationService, SMTPConfig
from app.services.n8n_service import N8nWorkflowService
from app.services.unified_agenda_service import UnifiedAgendaService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/telegram/bot-token", response_model=ProviderSecretRead, status_code=status.HTTP_201_CREATED)
def save_telegram_bot_token(
    payload: TelegramBotTokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderSecretRead:
    secret_payload = ProviderSecretCreate(
        provider="telegram",
        secret_key="bot_token",
        value=payload.bot_token,
        display_name=payload.display_name,
    )
    return ProviderSecretRepository(db).upsert(user_id=current_user.id, payload=secret_payload)


@router.post("/email/smtp-config", response_model=list[ProviderSecretRead], status_code=status.HTTP_201_CREATED)
def save_email_smtp_config(
    payload: EmailSMTPConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderSecretRead]:
    """Store SMTP credentials encrypted in DB.

    For Gmail, use an App Password, not the normal account password.
    Nothing is stored inside n8n workflow JSON.
    """
    repo = ProviderSecretRepository(db)
    items = {
        "smtp_host": payload.smtp_host,
        "smtp_port": str(payload.smtp_port),
        "smtp_username": payload.smtp_username,
        "smtp_password": payload.smtp_password,
        "smtp_from_email": payload.smtp_from_email,
        "smtp_use_tls": "true" if payload.smtp_use_tls else "false",
    }
    saved = []
    for key, value in items.items():
        saved.append(
            repo.upsert(
                user_id=current_user.id,
                payload=ProviderSecretCreate(
                    provider="email",
                    secret_key=key,
                    value=value,
                    display_name=payload.display_name,
                ),
            )
        )
    return saved


@router.get("/secrets", response_model=list[ProviderSecretRead])
def list_my_provider_secret_metadata(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderSecretRead]:
    return ProviderSecretRepository(db).list_metadata(user_id=current_user.id)


@router.post("/telegram/connect-manual", response_model=NotificationChannelRead, status_code=status.HTTP_201_CREATED)
def connect_telegram_manual(
    payload: TelegramConnectManual,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationChannelRead:
    channel_payload = NotificationChannelCreate(
        channel="telegram",
        destination=payload.chat_id,
        display_name=payload.display_name,
        is_enabled=True,
    )
    return NotificationChannelRepository(db).upsert(user_id=current_user.id, payload=channel_payload)


@router.post("/email/connect-manual", response_model=NotificationChannelRead, status_code=status.HTTP_201_CREATED)
def connect_email_manual(
    payload: EmailConnectManual,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationChannelRead:
    channel_payload = NotificationChannelCreate(
        channel="email",
        destination=payload.email,
        display_name=payload.display_name,
        is_enabled=True,
    )
    return NotificationChannelRepository(db).upsert(user_id=current_user.id, payload=channel_payload)


@router.get("/channels", response_model=list[NotificationChannelRead])
def list_notification_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationChannelRead]:
    return NotificationChannelRepository(db).list_for_user(user_id=current_user.id)


@router.post("/telegram/send-daily-agenda", response_model=TelegramDailyAgendaResponse)
async def send_daily_agenda_to_telegram(
    agenda_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    access_token: str = Depends(get_current_access_token),
) -> TelegramDailyAgendaResponse:
    telegram_channel = NotificationChannelRepository(db).get_enabled_channel(
        user_id=current_user.id,
        channel="telegram",
    )
    if telegram_channel is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram is not connected yet. Add a chat_id with /notifications/telegram/connect-manual.",
        )

    telegram_bot_token = ProviderSecretRepository(db).get_decrypted_value(
        user_id=current_user.id,
        provider="telegram",
        secret_key="bot_token",
    )
    if telegram_bot_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token is not configured. Save it with /notifications/telegram/bot-token.",
        )

    agenda = UnifiedAgendaService(db).build_daily_agenda(
        user_id=current_user.id,
        agenda_date=agenda_date,
    )

    try:
        n8n_response = await N8nWorkflowService().trigger_telegram_daily_agenda_workflow(
            user_id=current_user.id,
            user_email=current_user.email,
            agenda_date=agenda_date,
            access_token=access_token,
            telegram_chat_id=telegram_channel.destination,
            telegram_bot_token=telegram_bot_token,
            unified_agenda=agenda.model_dump(mode="json"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not send Telegram daily agenda via n8n: {exc}",
        ) from exc

    return TelegramDailyAgendaResponse(
        status="sent",
        channel_id=telegram_channel.id,
        agenda_date=agenda_date.isoformat(),
        n8n_response=n8n_response,
    )


@router.post("/email/send-daily-agenda", response_model=EmailDailyAgendaResponse)
async def send_daily_agenda_email_via_n8n(
    agenda_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    access_token: str = Depends(get_current_access_token),
) -> EmailDailyAgendaResponse:
    """Trigger n8n email workflow.

    n8n does not store or receive SMTP secrets. It calls the protected backend direct-send
    endpoint, and the backend reads encrypted SMTP credentials from the DB.
    """
    if NotificationChannelRepository(db).get_enabled_channel(user_id=current_user.id, channel="email") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is not connected yet. Add recipient with /notifications/email/connect-manual.",
        )
    _ensure_smtp_configured(db=db, user_id=current_user.id)

    try:
        n8n_response = await N8nWorkflowService().trigger_email_daily_agenda_workflow(
            user_id=current_user.id,
            user_email=current_user.email,
            agenda_date=agenda_date,
            access_token=access_token,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not send Email daily agenda via n8n: {exc}",
        ) from exc

    return EmailDailyAgendaResponse(
        status="sent",
        channel_id=None,
        agenda_date=agenda_date.isoformat(),
        n8n_response=n8n_response,
    )


@router.post("/email/send-direct", response_model=EmailDailyAgendaResponse)
def send_daily_agenda_email_direct(
    agenda_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailDailyAgendaResponse:
    """Protected endpoint used by n8n. Also useful for local debugging."""
    email_channel = NotificationChannelRepository(db).get_enabled_channel(
        user_id=current_user.id,
        channel="email",
    )
    if email_channel is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is not connected yet. Add recipient with /notifications/email/connect-manual.",
        )

    smtp_config = _load_smtp_config(db=db, user_id=current_user.id)
    agenda = UnifiedAgendaService(db).build_daily_agenda(user_id=current_user.id, agenda_date=agenda_date)
    email_message = next(
        (message for message in agenda.channel_messages if message.channel == "email"),
        None,
    )
    subject = email_message.subject if email_message and email_message.subject else f"Daily agenda for {agenda_date.isoformat()}"
    text_body = email_message.message if email_message else f"Your daily agenda for {agenda_date.isoformat()} is ready."

    try:
        email_response = EmailNotificationService().send_daily_agenda_email(
            smtp_config=smtp_config,
            to_email=email_channel.destination,
            subject=subject,
            text_body=text_body,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not send email via SMTP: {exc}",
        ) from exc

    return EmailDailyAgendaResponse(
        status="sent",
        channel_id=email_channel.id,
        agenda_date=agenda_date.isoformat(),
        email_response=email_response,
    )


def _ensure_smtp_configured(*, db: Session, user_id) -> None:
    _load_smtp_config(db=db, user_id=user_id)


def _load_smtp_config(*, db: Session, user_id) -> SMTPConfig:
    repo = ProviderSecretRepository(db)

    def get_required(key: str) -> str:
        value = repo.get_decrypted_value(user_id=user_id, provider="email", secret_key=key)
        if value is None or value == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email SMTP secret '{key}' is missing. Save SMTP config with /notifications/email/smtp-config.",
            )
        return value

    smtp_host = get_required("smtp_host")
    smtp_port = int(get_required("smtp_port"))
    smtp_username = get_required("smtp_username")
    smtp_password = get_required("smtp_password")
    smtp_from_email = get_required("smtp_from_email")
    smtp_use_tls = get_required("smtp_use_tls").lower() in {"1", "true", "yes", "on"}

    return SMTPConfig(
        host=smtp_host,
        port=smtp_port,
        username=smtp_username,
        password=smtp_password,
        from_email=smtp_from_email,
        use_tls=smtp_use_tls,
    )
