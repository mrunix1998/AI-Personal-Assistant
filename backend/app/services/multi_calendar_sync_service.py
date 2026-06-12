from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.crud.calendar_sources import CalendarSourceRepository
from app.crud.secrets import SecretRepository
from app.models.calendar_sources import CalendarSource
from app.services.ics_calendar_service import IcsCalendarService
from app.services.outlook_calendar_service import OutlookCalendarService


class MultiCalendarSyncService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.sources = CalendarSourceRepository(db)
        self.secrets = SecretRepository(db)

    async def sync_source(self, *, user_id: UUID, source: CalendarSource) -> dict:
        if source.provider in {"generic_ics", "apple_ics"}:
            return await self._sync_ics(user_id=user_id, source=source)
        if source.provider == "outlook_calendar":
            return await self._sync_outlook(user_id=user_id, source=source)
        return {"status": "skipped", "provider": source.provider, "source_id": source.id, "synced_count": 0}

    async def sync_all(self, *, user_id: UUID) -> dict:
        results = []
        for source in self.sources.list_for_user(user_id=user_id):
            if source.is_enabled:
                results.append(await self.sync_source(user_id=user_id, source=source))
        return {"status": "completed", "results": results, "total_synced": sum(r.get("synced_count", 0) for r in results)}

    async def _sync_ics(self, *, user_id: UUID, source: CalendarSource) -> dict:
        service = IcsCalendarService()
        content = await service.fetch_ics(source.ics_url or source.external_id)
        events = service.parse_events(content=content, fallback_source_id=str(source.id))
        count = self._upsert_events(user_id=user_id, provider=source.provider, source_id=str(source.id), events=events)
        self.sources.mark_synced(source=source)
        return {"status": "synced", "provider": source.provider, "source_id": source.id, "synced_count": count, "deleted_count": 0}

    async def _sync_outlook(self, *, user_id: UUID, source: CalendarSource) -> dict:
        refresh_token = self.secrets.get(user_id, "outlook", "refresh_token")
        access_token = self.secrets.get(user_id, "outlook", "access_token")
        outlook = OutlookCalendarService()
        if refresh_token:
            refreshed = await outlook.refresh_access_token(refresh_token=refresh_token)
            access_token = refreshed.get("access_token")
            if refreshed.get("refresh_token"):
                self.secrets.set(user_id, "outlook", "refresh_token", refreshed["refresh_token"])
            if access_token:
                self.secrets.set(user_id, "outlook", "access_token", access_token)
        if not access_token:
            return {"status": "missing_token", "provider": "outlook_calendar", "source_id": source.id, "synced_count": 0}
        events = await outlook.calendar_events(access_token=access_token)
        count = self._upsert_events(user_id=user_id, provider="outlook_calendar", source_id=str(source.id), events=events)
        self.sources.mark_synced(source=source)
        return {"status": "synced", "provider": "outlook_calendar", "source_id": source.id, "synced_count": count, "deleted_count": 0}

    def _upsert_events(self, *, user_id: UUID, provider: str, source_id: str, events: list[dict]) -> int:
        synced = 0
        for event in events:
            external_id = f"{source_id}:{event['external_event_id']}"
            self.db.execute(
                text(
                    """
                    INSERT INTO calendar_events
                    (id, user_id, connected_account_id, provider_name, external_event_id, title, description, location, starts_at, ends_at, timezone)
                    VALUES (gen_random_uuid(), :user_id, NULL, :provider_name, :external_event_id, :title, :description, :location, :starts_at, :ends_at, :timezone)
                    ON CONFLICT (provider_name, external_event_id)
                    DO UPDATE SET
                      title = EXCLUDED.title,
                      description = EXCLUDED.description,
                      location = EXCLUDED.location,
                      starts_at = EXCLUDED.starts_at,
                      ends_at = EXCLUDED.ends_at,
                      timezone = EXCLUDED.timezone
                    """
                ),
                {
                    "user_id": str(user_id),
                    "provider_name": provider,
                    "external_event_id": external_id,
                    "title": event["title"],
                    "description": event.get("description"),
                    "location": event.get("location"),
                    "starts_at": event["starts_at"],
                    "ends_at": event["ends_at"],
                    "timezone": event.get("timezone"),
                },
            )
            synced += 1
        self.db.commit()
        return synced
