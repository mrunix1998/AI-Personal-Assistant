from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.crud.calendar_sources import CalendarSourceRepository
from app.crud.secrets import SecretRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.calendar_sources import (
    CalendarEventRead,
    CalendarProviderRead,
    CalendarSourceRead,
    CalendarSourceTestResponse,
    CalendarSyncResponse,
    IcsCalendarSourceCreate,
)
from app.services.ics_calendar_service import IcsCalendarService
from app.services.multi_calendar_sync_service import MultiCalendarSyncService
from app.services.outlook_calendar_service import OutlookCalendarService

router = APIRouter(prefix="/calendars", tags=["calendars"])


@router.get("/providers", response_model=list[CalendarProviderRead])
def providers() -> list[CalendarProviderRead]:
    return [
        CalendarProviderRead(provider="google_calendar", label="Google Calendar", connection_type="oauth", status="existing_integration"),
        CalendarProviderRead(provider="outlook_calendar", label="Outlook / Microsoft 365", connection_type="oauth", status="ready"),
        CalendarProviderRead(provider="apple_ics", label="Apple Calendar", connection_type="ics", status="ready"),
        CalendarProviderRead(provider="generic_ics", label="Generic ICS Calendar", connection_type="ics", status="ready"),
    ]


@router.get("/outlook/connect")
def outlook_connect(current_user: User = Depends(get_current_user)):
    state = f"{current_user.id}:{uuid4()}"
    url = OutlookCalendarService().build_authorization_url(state=state)
    return {"authorization_url": url, "state": state}


@router.get("/outlook/callback")
async def outlook_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    user_id_raw = state.split(":", 1)[0]
    try:
        user_id = UUID(user_id_raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc

    outlook = OutlookCalendarService()
    tokens = await outlook.exchange_code(code=code)
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Microsoft did not return an access token")

    me = await outlook.me(access_token=access_token)
    email = me.get("mail") or me.get("userPrincipalName")
    if not email:
        raise HTTPException(status_code=400, detail="Could not read Microsoft account email")

    secrets = SecretRepository(db)
    secrets.set(user_id, "outlook", "access_token", access_token)
    if refresh_token:
        secrets.set(user_id, "outlook", "refresh_token", refresh_token)

    source = CalendarSourceRepository(db).create_or_update_outlook_source(
        user_id=user_id,
        email=email,
        name="Outlook Calendar",
    )
    return {
        "message": "Outlook Calendar connected successfully",
        "source": CalendarSourceRead.model_validate(source),
    }


@router.post("/ics-sources", response_model=CalendarSourceRead)
def create_ics_source(
    payload: IcsCalendarSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return CalendarSourceRepository(db).create_ics_source(user_id=current_user.id, payload=payload)


@router.get("/sources", response_model=list[CalendarSourceRead])
def list_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return CalendarSourceRepository(db).list_for_user(user_id=current_user.id)


@router.post("/sources/{source_id}/test", response_model=CalendarSourceTestResponse)
async def test_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = CalendarSourceRepository(db).get_for_user(user_id=current_user.id, source_id=source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Calendar source not found")

    if source.provider in {"generic_ics", "apple_ics"}:
        count = await IcsCalendarService().test_connection(source.ics_url or source.external_id)
        return CalendarSourceTestResponse(
            status="ok",
            provider=source.provider,
            name=source.name,
            event_count_preview=count,
            message=f"ICS feed is reachable and contains {count} events.",
        )

    if source.provider == "outlook_calendar":
        token = SecretRepository(db).get(current_user.id, "outlook", "access_token")
        if not token:
            raise HTTPException(status_code=400, detail="Outlook access token is missing. Connect Outlook first.")
        me = await OutlookCalendarService().me(access_token=token)
        return CalendarSourceTestResponse(
            status="ok",
            provider="outlook_calendar",
            name=source.name,
            event_count_preview=0,
            message=f"Connected to Microsoft account {me.get('mail') or me.get('userPrincipalName')}",
        )

    raise HTTPException(status_code=400, detail=f"Testing not supported for provider {source.provider}")


@router.post("/sources/{source_id}/sync", response_model=CalendarSyncResponse)
async def sync_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = CalendarSourceRepository(db).get_for_user(user_id=current_user.id, source_id=source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Calendar source not found")
    result = await MultiCalendarSyncService(db).sync_source(user_id=current_user.id, source=source)
    return CalendarSyncResponse(**result)


@router.post("/sync-all")
async def sync_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await MultiCalendarSyncService(db).sync_all(user_id=current_user.id)


@router.get("/events", response_model=list[CalendarEventRead])
def events(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc) if start_date else None
    end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc) if end_date else None

    sql = """
        SELECT id, provider_name::text AS provider_name, external_event_id, title, description, location, starts_at, ends_at, timezone
        FROM calendar_events
        WHERE user_id = :user_id
    """
    params = {"user_id": str(current_user.id)}
    if start_dt:
        sql += " AND starts_at >= :start_dt"
        params["start_dt"] = start_dt
    if end_dt:
        sql += " AND starts_at <= :end_dt"
        params["end_dt"] = end_dt
    sql += " ORDER BY starts_at ASC LIMIT 500"

    rows = db.execute(text(sql), params).mappings().all()
    return [CalendarEventRead(**dict(row)) for row in rows]
