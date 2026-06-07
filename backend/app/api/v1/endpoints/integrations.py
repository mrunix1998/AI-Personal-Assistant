from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.crud.connected_accounts import ConnectedAccountRepository
from app.db.session import get_db
from app.integrations.calendars.google import GoogleCalendarProvider
from app.models.user import User
from app.services.google_calendar_sync_service import GoogleCalendarSyncService
from app.schemas.integrations import (
    ConnectedAccountRead,
    GoogleCallbackResponse,
    GoogleConnectResponse,
    GoogleSyncResponse,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _build_oauth_state(user_id: UUID) -> str:
    # MVP state format. In production, store a random nonce in Redis with TTL and validate it.
    from uuid import uuid4

    return f"{user_id}:{uuid4()}"


def _extract_user_id_from_state(state: str) -> UUID:
    try:
        raw_user_id, _nonce = state.split(":", 1)
        return UUID(raw_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state") from exc


@router.get("/accounts", response_model=list[ConnectedAccountRead])
def list_connected_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConnectedAccountRead]:
    return ConnectedAccountRepository(db).list_for_user(current_user.id)


@router.get("/google/connect", response_model=GoogleConnectResponse)
async def connect_google_calendar(
    current_user: User = Depends(get_current_user),
) -> GoogleConnectResponse:
    state = _build_oauth_state(current_user.id)
    authorization_url = await GoogleCalendarProvider().build_authorization_url(state=state)
    return GoogleConnectResponse(authorization_url=authorization_url, state=state)


@router.get("/google/callback", response_model=GoogleCallbackResponse)
async def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> GoogleCallbackResponse:
    user_id = _extract_user_id_from_state(state)
    provider = GoogleCalendarProvider()

    try:
        tokens = await provider.exchange_code_for_tokens(code=code)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not exchange Google authorization code for tokens",
        ) from exc

    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google did not return access token")

    user_info = await provider.fetch_user_info(access_token)
    external_account_id = user_info.get("email") or user_info.get("sub")

    account = ConnectedAccountRepository(db).upsert_google_calendar(
        user_id=user_id,
        access_token=access_token,
        refresh_token=tokens.get("refresh_token"),
        expires_in=tokens.get("expires_in"),
        external_account_id=external_account_id,
    )
    return GoogleCallbackResponse(message="Google Calendar connected successfully", account=account)


@router.post("/google/sync", response_model=GoogleSyncResponse)
async def sync_google_calendar_events(
    past_days: int = Query(default=30, ge=0, le=365),
    future_days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoogleSyncResponse:
    try:
        result = await GoogleCalendarSyncService(db).sync_calendars(
            user_id=current_user.id,
            past_days=past_days,
            future_days=future_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not sync Google Calendar events",
        ) from exc

    return GoogleSyncResponse(**result)
