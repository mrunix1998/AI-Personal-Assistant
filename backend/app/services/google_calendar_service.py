from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import TokenCipher
from app.models.calendar_event import CalendarEvent
from app.models.connected_account import ConnectedAccount
from app.models.enums import ProviderName, ProviderType


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_CAL_API = "https://www.googleapis.com/calendar/v3"

SCOPES = "openid email profile https://www.googleapis.com/auth/calendar.readonly"


class GoogleCalendarService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.cipher = TokenCipher()

    def build_authorization_url(self, user_id, state_nonce: str) -> str:
        state = f"{user_id}:{state_nonce}"

        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_and_store(self, code: str, state: str) -> ConnectedAccount:
        try:
            user_id = UUID(state.split(":", 1)[0])
        except Exception as exc:
            raise ValueError("Invalid Google OAuth state") from exc

        async with httpx.AsyncClient(timeout=20) as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            if token_resp.status_code >= 400:
                raise ValueError(f"Google token exchange failed: {token_resp.text}")

            token_data = token_resp.json()

            access_token = token_data["access_token"]
            refresh_token = token_data.get("refresh_token")
            expires_in = int(token_data.get("expires_in", 3600))

            user_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if user_resp.status_code >= 400:
                raise ValueError(f"Google userinfo failed: {user_resp.text}")

            external_email = user_resp.json().get("email") or "google_user"

        account = (
            self.db.query(ConnectedAccount)
            .filter(
                ConnectedAccount.user_id == user_id,
                ConnectedAccount.provider_name == ProviderName.GOOGLE_CALENDAR.value,
                ConnectedAccount.external_account_id == external_email,
            )
            .first()
        )

        if account is None:
            account = ConnectedAccount(
                user_id=user_id,
                provider_name=ProviderName.GOOGLE_CALENDAR.value,
                provider_type=ProviderType.CALENDAR.value,
                external_account_id=external_email,
            )
            self.db.add(account)

        account.access_token_encrypted = self.cipher.encrypt(access_token)

        if refresh_token:
            account.refresh_token_encrypted = self.cipher.encrypt(refresh_token)

        account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        self.db.commit()
        self.db.refresh(account)

        return account

    async def _valid_access_token(self, account: ConnectedAccount) -> str:
        access_token = self.cipher.decrypt(account.access_token_encrypted)

        expires_at = account.token_expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at and expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
            return access_token

        refresh_token = self.cipher.decrypt(account.refresh_token_encrypted)

        if not refresh_token:
            return access_token

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if resp.status_code >= 400:
                raise ValueError(f"Google refresh token failed: {resp.text}")

            data = resp.json()

        account.access_token_encrypted = self.cipher.encrypt(data["access_token"])
        account.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=int(data.get("expires_in", 3600))
        )

        self.db.commit()

        return data["access_token"]

    async def sync(self, user_id, past_days: int = 30, future_days: int = 30) -> dict:
        try:
            user_uuid = UUID(str(user_id))
        except Exception:
            user_uuid = user_id

        account = (
            self.db.query(ConnectedAccount)
            .filter(
                ConnectedAccount.user_id == user_uuid,
                ConnectedAccount.provider_name == ProviderName.GOOGLE_CALENDAR.value,
            )
            .first()
        )

        if account is None:
            raise ValueError("Google Calendar account is not connected yet.")

        token = await self._valid_access_token(account)

        start_at = (
            datetime.now(timezone.utc)
            - timedelta(days=past_days)
        ).replace(hour=0, minute=0, second=0, microsecond=0)

        end_at = (
            datetime.now(timezone.utc)
            + timedelta(days=future_days)
        ).replace(hour=0, minute=0, second=0, microsecond=0)

        headers = {"Authorization": f"Bearer {token}"}

        synced = 0
        calendars = []

        async with httpx.AsyncClient(timeout=30) as client:
            calendar_resp = await client.get(
                f"{GOOGLE_CAL_API}/users/me/calendarList",
                headers=headers,
            )

            if calendar_resp.status_code >= 400:
                raise ValueError(f"Google calendar list failed: {calendar_resp.text}")

            google_calendars = calendar_resp.json().get("items", [])

            for cal in google_calendars:
                if cal.get("accessRole") == "freeBusyReader":
                    continue

                calendar_id = cal.get("id")
                calendar_name = cal.get("summary")

                if not calendar_id:
                    continue

                calendars.append(
                    {
                        "id": calendar_id,
                        "summary": calendar_name,
                    }
                )

                params = {
                    "timeMin": start_at.isoformat().replace("+00:00", "Z"),
                    "timeMax": end_at.isoformat().replace("+00:00", "Z"),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                }

                events_resp = await client.get(
                    f"{GOOGLE_CAL_API}/calendars/{calendar_id}/events",
                    headers=headers,
                    params=params,
                )

                if events_resp.status_code == 404:
                    continue

                if events_resp.status_code == 403:
                    continue

                if events_resp.status_code >= 400:
                    continue
                
                for ev in events_resp.json().get("items", []):
                    if ev.get("status") == "cancelled":
                        continue

                    start_raw = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")
                    end_raw = ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date")

                    if not start_raw or not end_raw:
                        continue

                    starts_at = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                    ends_at = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))

                    external_event_id = f"{calendar_id}:{ev.get('id')}"

                    obj = (
                        self.db.query(CalendarEvent)
                        .filter(
                            CalendarEvent.user_id == user_uuid,
                            CalendarEvent.provider_name == ProviderName.GOOGLE_CALENDAR.value,
                            CalendarEvent.external_event_id == external_event_id,
                        )
                        .first()
                    )

                    if obj is None:
                        obj = CalendarEvent(
                            user_id=user_uuid,
                            connected_account_id=account.id,
                            provider_name=ProviderName.GOOGLE_CALENDAR.value,
                            external_event_id=external_event_id,
                        )
                        self.db.add(obj)

                    obj.connected_account_id = account.id
                    obj.calendar_id = calendar_id
                    obj.calendar_name = calendar_name
                    obj.title = ev.get("summary") or "Untitled event"
                    obj.description = ev.get("description")
                    obj.location = ev.get("location")
                    obj.starts_at = starts_at
                    obj.ends_at = ends_at
                    obj.timezone = ev.get("start", {}).get("timeZone")

                    synced += 1

        self.db.commit()

        return {
            "provider": ProviderName.GOOGLE_CALENDAR.value,
            "synced_count": synced,
            "calendars": calendars,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
        }