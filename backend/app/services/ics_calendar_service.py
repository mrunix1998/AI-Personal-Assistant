from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import httpx
from dateutil.parser import parse as parse_datetime
from icalendar import Calendar


def _to_datetime(value: Any) -> datetime:
    raw = getattr(value, "dt", value)
    if isinstance(raw, datetime):
        result = raw
    else:
        result = parse_datetime(str(raw))
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result


class IcsCalendarService:
    async def fetch_ics(self, ics_url: str) -> bytes:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(ics_url)
            response.raise_for_status()
            return response.content

    def parse_events(self, *, content: bytes, fallback_source_id: str) -> list[dict[str, Any]]:
        calendar = Calendar.from_ical(content)
        events: list[dict[str, Any]] = []

        for component in calendar.walk("VEVENT"):
            summary = str(component.get("summary", "Untitled event"))
            uid = str(component.get("uid", ""))
            starts_at = _to_datetime(component.get("dtstart"))
            ends_at = _to_datetime(component.get("dtend", component.get("dtstart")))
            description = str(component.get("description", "")) or None
            location = str(component.get("location", "")) or None

            if not uid:
                stable = f"{fallback_source_id}:{summary}:{starts_at.isoformat()}:{ends_at.isoformat()}"
                uid = hashlib.sha256(stable.encode()).hexdigest()

            events.append(
                {
                    "external_event_id": uid,
                    "title": summary,
                    "description": description,
                    "location": location,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "timezone": starts_at.tzname() or "UTC",
                }
            )

        return events

    async def test_connection(self, ics_url: str) -> int:
        content = await self.fetch_ics(ics_url)
        events = self.parse_events(content=content, fallback_source_id=ics_url)
        return len(events)
