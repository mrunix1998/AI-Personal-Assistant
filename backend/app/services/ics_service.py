from datetime import datetime
from ics import Calendar
from app.schemas.events import EventCreate

def parse_ics_text(ics_text: str, provider_name="apple_calendar_ics") -> list[EventCreate]:
    cal=Calendar(ics_text); out=[]
    for ev in cal.events:
        if not ev.begin or not ev.end: continue
        out.append(EventCreate(provider_name=provider_name, external_event_id=ev.uid or f"ics:{ev.name}:{ev.begin}", title=ev.name or "Untitled", description=ev.description, location=ev.location, starts_at=ev.begin.datetime, ends_at=ev.end.datetime, timezone="Europe/Berlin", calendar_name="ICS Feed"))
    return out
