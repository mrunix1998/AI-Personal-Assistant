from datetime import datetime, timezone
import httpx
from app.schemas.events import EventCreate

class OutlookCalendarService:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def fetch_events(self, start_at: datetime, end_at: datetime) -> list[EventCreate]:
        url = "https://graph.microsoft.com/v1.0/me/calendarView"
        params = {"startDateTime": start_at.isoformat(), "endDateTime": end_at.isoformat(), "$top": 100}
        headers = {"Authorization": f"Bearer {self.access_token}"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
        events: list[EventCreate] = []
        for item in data.get("value", []):
            start = self._parse_dt(item.get("start", {}))
            end = self._parse_dt(item.get("end", {}))
            if not start or not end:
                continue
            events.append(EventCreate(
                provider_name="outlook_calendar",
                external_event_id=f"outlook:{item.get('id')}",
                calendar_id="primary",
                calendar_name="Outlook Calendar",
                title=item.get("subject") or "Untitled Outlook event",
                description=item.get("bodyPreview"),
                location=(item.get("location") or {}).get("displayName"),
                starts_at=start,
                ends_at=end,
                timezone=(item.get("start") or {}).get("timeZone"),
            ))
        return events

    def _parse_dt(self, value: dict):
        raw = value.get("dateTime")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
