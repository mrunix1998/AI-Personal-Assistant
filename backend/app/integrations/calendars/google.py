from datetime import datetime, time
from urllib.parse import quote, urlencode

import httpx

from app.core.config import get_settings
from app.integrations.calendars.base import CalendarProvider, ExternalCalendarEvent

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_LIST_URL = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
GOOGLE_CALENDAR_EVENTS_URL_TEMPLATE = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar.readonly",
]


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
            "include_granted_scopes": "true",
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

    async def fetch_user_info(self, access_token: str) -> dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
            response.raise_for_status()
            return response.json()

    async def fetch_calendar_list(self) -> list[dict]:
        if not self.access_token:
            raise ValueError("Google access token is required to fetch calendar list.")

        headers = {"Authorization": f"Bearer {self.access_token}"}
        calendars: list[dict] = []
        page_token: str | None = None

        async with httpx.AsyncClient(timeout=20) as client:
            while True:
                params = {"minAccessRole": "reader"}
                if page_token:
                    params["pageToken"] = page_token
                response = await client.get(GOOGLE_CALENDAR_LIST_URL, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                calendars.extend(data.get("items", []))
                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return calendars

    async def fetch_events(self, start: datetime, end: datetime) -> list[ExternalCalendarEvent]:
        return await self.fetch_events_from_all_calendars(start=start, end=end)

    async def fetch_events_from_all_calendars(self, start: datetime, end: datetime) -> list[ExternalCalendarEvent]:
        calendars = await self.fetch_calendar_list()
        all_events: list[ExternalCalendarEvent] = []
        errors: list[dict] = []

        for calendar in calendars:
            calendar_id = calendar.get("id")
            if not calendar_id:
                continue
            try:
                calendar_events = await self.fetch_events_for_calendar(
                    calendar_id=calendar_id,
                    calendar_name=calendar.get("summary") or calendar_id,
                    start=start,
                    end=end,
                )
                all_events.extend(calendar_events)
            except httpx.HTTPStatusError as exc:
                errors.append(
                    {
                        "calendar_id": calendar_id,
                        "status_code": exc.response.status_code,
                        "body": exc.response.text[:500],
                    }
                )

        if not all_events and errors and len(errors) == len(calendars):
            raise RuntimeError(f"Could not fetch events from any Google calendar: {errors}")

        return all_events

    async def fetch_events_for_calendar(
        self,
        *,
        calendar_id: str,
        calendar_name: str,
        start: datetime,
        end: datetime,
    ) -> list[ExternalCalendarEvent]:
        if not self.access_token:
            raise ValueError("Google access token is required to fetch calendar events.")

        params = {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "showDeleted": "false",
            "maxResults": 2500,
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = GOOGLE_CALENDAR_EVENTS_URL_TEMPLATE.format(calendar_id=quote(calendar_id, safe=""))

        items: list[dict] = []
        page_token: str | None = None
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                request_params = dict(params)
                if page_token:
                    request_params["pageToken"] = page_token
                response = await client.get(url, params=request_params, headers=headers)
                response.raise_for_status()
                data = response.json()
                items.extend(data.get("items", []))
                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        events: list[ExternalCalendarEvent] = []
        for item in items:
            start_data = item.get("start", {})
            end_data = item.get("end", {})
            start_value = start_data.get("dateTime") or start_data.get("date")
            end_value = end_data.get("dateTime") or end_data.get("date")
            if not start_value or not end_value:
                continue

            starts_at = self._parse_google_datetime(start_value, is_end=False)
            ends_at = self._parse_google_datetime(end_value, is_end=True)
            event_id = item["id"]

            events.append(
                ExternalCalendarEvent(
                    external_id=f"{calendar_id}:{event_id}",
                    external_calendar_id=calendar_id,
                    external_calendar_name=calendar_name,
                    title=item.get("summary", "Untitled event"),
                    starts_at=starts_at,
                    ends_at=ends_at,
                    description=item.get("description"),
                    location=item.get("location"),
                    timezone=start_data.get("timeZone") or end_data.get("timeZone"),
                )
            )
        return events

    @staticmethod
    def _parse_google_datetime(value: str, *, is_end: bool) -> datetime:
        # Google uses date-only strings for all-day events. Store them as midnight.
        if "T" not in value:
            return datetime.combine(datetime.fromisoformat(value).date(), time.min)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
