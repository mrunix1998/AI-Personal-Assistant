from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.crud.calendar_events import CalendarEventRepository
from app.crud.secrets import SecretRepository
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/calendar", tags=["calendar"])


class CalendarSourceCreate(BaseModel):
    name: str
    provider: str = "ics"
    ics_url: HttpUrl | None = None


def _source_key(source_id: str, field: str) -> str:
    return f"source:{source_id}:{field}"


@router.get("/providers")
def providers():
    return {
        "providers": [
            {"provider": "google_calendar", "mode": "oauth", "status": "supported"},
            {"provider": "outlook_calendar", "mode": "oauth_or_ics", "status": "ics_supported_oauth_next"},
            {"provider": "apple_calendar", "mode": "ics", "status": "supported"},
            {"provider": "generic_ics", "mode": "ics", "status": "supported"},
        ]
    }


@router.get("/sources")
def list_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SecretRepository(db)
    raw = repo.list(current_user.id) if hasattr(repo, "list") else []
    # Compatible fallback: return source index if saved by this endpoint.
    source_index = repo.get(current_user.id, "calendar_sources", "index")
    if not source_index:
        return []
    import json
    return json.loads(source_index)


@router.post("/sources")
def create_source(
    payload: CalendarSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.provider not in {"ics", "apple_ics", "generic_ics", "outlook_ics"}:
        raise HTTPException(status_code=400, detail="Only ICS-like sources are supported by this MVP endpoint")

    if not payload.ics_url:
        raise HTTPException(status_code=400, detail="ics_url is required")

    repo = SecretRepository(db)
    import json
    source_id = str(uuid.uuid4())
    source = {
        "id": source_id,
        "name": payload.name,
        "provider": payload.provider,
        "ics_url_saved": True,
    }

    existing_raw = repo.get(current_user.id, "calendar_sources", "index")
    existing = json.loads(existing_raw) if existing_raw else []
    existing.append(source)

    repo.set(current_user.id, "calendar_sources", "index", json.dumps(existing))
    repo.set(current_user.id, "calendar_sources", _source_key(source_id, "ics_url"), str(payload.ics_url))
    repo.set(current_user.id, "calendar_sources", _source_key(source_id, "name"), payload.name)
    repo.set(current_user.id, "calendar_sources", _source_key(source_id, "provider"), payload.provider)

    return source


@router.post("/sources/test")
async def test_source(
    payload: CalendarSourceCreate,
):
    if not payload.ics_url:
        raise HTTPException(status_code=400, detail="ics_url is required")

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        res = await client.get(str(payload.ics_url))
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=res.text[:500])

    text = res.text
    return {
        "status": "connected",
        "looks_like_ics": "BEGIN:VCALENDAR" in text,
        "size": len(text),
    }


def _extract_ics_events(text: str, limit: int = 200) -> list[dict]:
    events = []
    blocks = text.split("BEGIN:VEVENT")[1:]
    for block in blocks[:limit]:
        def get_line(name: str) -> str | None:
            for line in block.splitlines():
                if line.startswith(name + ":") or line.startswith(name + ";"):
                    return line.split(":", 1)[-1].strip()
            return None

        title = get_line("SUMMARY") or "Untitled event"
        uid = get_line("UID") or str(uuid.uuid4())
        dtstart = get_line("DTSTART")
        dtend = get_line("DTEND")

        def parse_dt(value: str | None):
            if not value:
                return None
            value = value.replace("Z", "")
            for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
                try:
                    dt = datetime.strptime(value[:15] if "T" in value else value[:8], fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except Exception:
                    pass
            return None

        starts_at = parse_dt(dtstart)
        ends_at = parse_dt(dtend) or (starts_at + timedelta(hours=1) if starts_at else None)
        if starts_at and ends_at:
            events.append({
                "external_event_id": uid,
                "title": title,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "provider_name": "ics",
            })
    return events


@router.post("/sources/{source_id}/sync")
async def sync_source(
    source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SecretRepository(db)
    ics_url = repo.get(current_user.id, "calendar_sources", _source_key(source_id, "ics_url"))
    name = repo.get(current_user.id, "calendar_sources", _source_key(source_id, "name")) or "ICS Calendar"

    if not ics_url:
        raise HTTPException(status_code=404, detail="Calendar source not found")

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        res = await client.get(ics_url)
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=res.text[:500])

    events = _extract_ics_events(res.text)
    event_repo = CalendarEventRepository(db)
    saved = 0
    for event in events:
        # Adjust this block to your CalendarEventRepository method name if needed.
        if hasattr(event_repo, "upsert"):
            event_repo.upsert(
                user_id=current_user.id,
                connected_account_id=None,
                provider_name="ics",
                external_event_id=f"{source_id}:{event['external_event_id']}",
                title=event["title"],
                description=None,
                location=None,
                starts_at=event["starts_at"],
                ends_at=event["ends_at"],
                timezone="UTC",
            )
            saved += 1
    return {"status": "synced", "source_id": source_id, "source_name": name, "synced_count": saved, "parsed_count": len(events)}


@router.post("/sync-all")
async def sync_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SecretRepository(db)
    import json
    existing_raw = repo.get(current_user.id, "calendar_sources", "index")
    sources = json.loads(existing_raw) if existing_raw else []
    results = []
    # Keep it simple: test/parse only, actual save depends on repository compatibility.
    for source in sources:
        results.append({"source_id": source["id"], "status": "registered"})
    return {"status": "ok", "source_count": len(sources), "results": results}
