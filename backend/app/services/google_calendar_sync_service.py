from datetime import datetime, time, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.token_crypto import decrypt_secret, encrypt_secret
from app.crud.calendar_events import CalendarEventRepository
from app.crud.connected_accounts import ConnectedAccountRepository
from app.integrations.calendars.google import GOOGLE_TOKEN_URL, GoogleCalendarProvider
from app.models.connected_account import ConnectedAccount
from app.models.enums import ProviderName


class GoogleCalendarSyncService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.accounts = ConnectedAccountRepository(db)
        self.events = CalendarEventRepository(db)

    async def sync_calendars(
        self,
        *,
        user_id: UUID,
        past_days: int = 30,
        future_days: int = 30,
    ) -> dict:
        account = self.accounts.get_by_provider(
            user_id=user_id,
            provider_name=ProviderName.GOOGLE_CALENDAR,
        )
        if account is None:
            raise ValueError("Google Calendar account is not connected yet.")

        access_token = await self._get_valid_access_token(account)

        now = datetime.now(timezone.utc)
        today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
        start_at = today_start - timedelta(days=past_days)
        end_at = today_start + timedelta(days=future_days)

        provider = GoogleCalendarProvider(access_token=access_token)
        calendars = await provider.fetch_calendar_list()
        external_events = await provider.fetch_events_from_all_calendars(start=start_at, end=end_at)

        saved_events = self.events.upsert_many(
            user_id=user_id,
            connected_account_id=account.id,
            provider_name=ProviderName.GOOGLE_CALENDAR,
            events=external_events,
        )
        deleted_count = self.events.delete_missing_external_ids(
            user_id=user_id,
            connected_account_id=account.id,
            provider_name=ProviderName.GOOGLE_CALENDAR,
            keep_external_ids={event.external_id for event in external_events},
        )

        events_by_calendar: dict[str, int] = {}
        for event in external_events:
            calendar_name = event.external_calendar_name or event.external_calendar_id or "unknown"
            events_by_calendar[calendar_name] = events_by_calendar.get(calendar_name, 0) + 1

        return {
            "provider": ProviderName.GOOGLE_CALENDAR,
            "synced_count": len(saved_events),
            "deleted_count": deleted_count,
            "calendar_count": len(calendars),
            "events_by_calendar": events_by_calendar,
            "start_at": start_at,
            "end_at": end_at,
        }

    # Backwards-compatible wrapper for older callers.
    async def sync_primary_calendar(
        self,
        *,
        user_id: UUID,
        start_date=None,
        days: int = 7,
    ) -> dict:
        return await self.sync_calendars(user_id=user_id, past_days=0, future_days=days)

    async def _get_valid_access_token(self, account: ConnectedAccount) -> str:
        now = datetime.now(timezone.utc)
        token_expires_at = account.token_expires_at
        if token_expires_at and token_expires_at.tzinfo is None:
            token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

        access_token = decrypt_secret(account.access_token)
        if token_expires_at is None or token_expires_at > now + timedelta(minutes=2):
            if not access_token:
                raise ValueError("Stored Google access token is empty.")
            return access_token

        refresh_token = decrypt_secret(account.refresh_token)
        if not refresh_token:
            raise ValueError("Google refresh token is missing. Reconnect Google Calendar.")

        payload = {
            "client_id": self.settings.google_client_id,
            "client_secret": self.settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()
            tokens = response.json()

        new_access_token = tokens["access_token"]
        expires_in = int(tokens.get("expires_in", 3600))
        account.access_token = encrypt_secret(new_access_token)
        account.token_expires_at = now + timedelta(seconds=expires_in)
        self.db.commit()
        self.db.refresh(account)
        return new_access_token
