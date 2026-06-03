from datetime import datetime
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings
from app.integrations.calendars.base import CalendarProvider, ExternalCalendarEvent

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class GoogleCalendarProvider(CalendarProvider):
    provider_name = "google_calendar"

    def __init__(self, access_token: str | None = None) -> None:
        self.settings = get_settings()
        self.access_token = access_token

    async def build_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> dict:
        payload = {
            "client_id": self.settings.google_client_id,
            "client_secret": self.settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.settings.google_redirect_uri,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()

    async def fetch_events(self, start: datetime, end: datetime) -> list[ExternalCalendarEvent]:
        if not self.access_token:
            raise ValueError("Google access token is required to fetch calendar events.")

        params = {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(GOOGLE_CALENDAR_EVENTS_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        events: list[ExternalCalendarEvent] = []
        for item in data.get("items", []):
            start_data = item.get("start", {})
            end_data = item.get("end", {})
            start_value = start_data.get("dateTime") or start_data.get("date")
            end_value = end_data.get("dateTime") or end_data.get("date")
            if not start_value or not end_value:
                continue
            events.append(
                ExternalCalendarEvent(
                    external_id=item["id"],
                    title=item.get("summary", "Untitled event"),
                    starts_at=datetime.fromisoformat(start_value.replace("Z", "+00:00")),
                    ends_at=datetime.fromisoformat(end_value.replace("Z", "+00:00")),
                    description=item.get("description"),
                    location=item.get("location"),
                    timezone=start_data.get("timeZone"),
                )
            )
        return events
