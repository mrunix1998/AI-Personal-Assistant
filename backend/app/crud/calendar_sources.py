from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.calendar_sources import CalendarSource
from app.schemas.calendar_sources import IcsCalendarSourceCreate


class CalendarSourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_ics_source(self, *, user_id: UUID, payload: IcsCalendarSourceCreate) -> CalendarSource:
        external_id = str(payload.ics_url)
        existing = (
            self.db.query(CalendarSource)
            .filter(
                CalendarSource.user_id == user_id,
                CalendarSource.provider == payload.provider,
                CalendarSource.external_id == external_id,
            )
            .first()
        )
        if existing:
            existing.name = payload.name
            existing.ics_url = external_id
            existing.is_enabled = True
            self.db.commit()
            self.db.refresh(existing)
            return existing

        source = CalendarSource(
            user_id=user_id,
            provider=payload.provider,
            name=payload.name,
            external_id=external_id,
            ics_url=external_id,
            is_enabled=True,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def create_or_update_outlook_source(self, *, user_id: UUID, email: str, name: str = "Outlook Calendar") -> CalendarSource:
        existing = (
            self.db.query(CalendarSource)
            .filter(
                CalendarSource.user_id == user_id,
                CalendarSource.provider == "outlook_calendar",
                CalendarSource.external_id == email,
            )
            .first()
        )
        if existing:
            existing.name = name
            existing.is_enabled = True
            self.db.commit()
            self.db.refresh(existing)
            return existing

        source = CalendarSource(
            user_id=user_id,
            provider="outlook_calendar",
            name=name,
            external_id=email,
            is_enabled=True,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def list_for_user(self, *, user_id: UUID) -> list[CalendarSource]:
        return (
            self.db.query(CalendarSource)
            .filter(CalendarSource.user_id == user_id)
            .order_by(CalendarSource.created_at.desc())
            .all()
        )

    def get_for_user(self, *, user_id: UUID, source_id: UUID) -> CalendarSource | None:
        return (
            self.db.query(CalendarSource)
            .filter(CalendarSource.user_id == user_id, CalendarSource.id == source_id)
            .first()
        )

    def mark_synced(self, *, source: CalendarSource) -> CalendarSource:
        source.last_synced_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(source)
        return source
