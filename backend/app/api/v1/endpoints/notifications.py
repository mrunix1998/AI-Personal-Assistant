from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_access_token, get_current_user
from app.crud.notification_channels import NotificationChannelRepository
from app.crud.provider_secrets import ProviderSecretRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.notifications import (
    NotificationChannelCreate,
    NotificationChannelRead,
    TelegramConnectManual,
    TelegramDailyAgendaResponse,
)
from app.schemas.provider_secrets import ProviderSecretCreate, ProviderSecretRead, TelegramBotTokenCreate
from app.services.n8n_service import N8nWorkflowService
from app.services.unified_agenda_service import UnifiedAgendaService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/telegram/bot-token", response_model=ProviderSecretRead, status_code=status.HTTP_201_CREATED)
def save_telegram_bot_token(
    payload: TelegramBotTokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderSecretRead:
    """Store Telegram bot token encrypted in DB.

    MVP behavior: the token is stored per user. In a production SaaS setup you may store
    one app-level Telegram bot token as a system secret instead.
    """
    secret_payload = ProviderSecretCreate(
        provider="telegram",
        secret_key="bot_token",
        value=payload.bot_token,
        display_name=payload.display_name,
    )
    return ProviderSecretRepository(db).upsert(user_id=current_user.id, payload=secret_payload)


@router.get("/secrets", response_model=list[ProviderSecretRead])
def list_my_provider_secret_metadata(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderSecretRead]:
    """Return only secret metadata, never decrypted values."""
    return ProviderSecretRepository(db).list_metadata(user_id=current_user.id)


@router.post("/telegram/connect-manual", response_model=NotificationChannelRead, status_code=status.HTTP_201_CREATED)
def connect_telegram_manual(
    payload: TelegramConnectManual,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationChannelRead:
    """MVP Telegram connection.

    For local development we store a Telegram chat_id manually. In a production version,
    this can be replaced with a Telegram webhook flow where the user sends /start to the bot.
    """
    channel_payload = NotificationChannelCreate(
        channel="telegram",
        destination=payload.chat_id,
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
