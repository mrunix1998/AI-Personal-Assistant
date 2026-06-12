from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.integrations.calendars.base import ExternalCalendarEvent
from app.models.calendar_events import CalendarEvent
from app.models.enums import ProviderName


class CalendarEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, *, user_id: UUID) -> list[CalendarEvent]:
        stmt = (
            select(CalendarEvent)
            .where(CalendarEvent.user_id == user_id)
            .order_by(CalendarEvent.starts_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def upsert_many(
        self,
        *,
        user_id: UUID,
        connected_account_id: UUID,
        provider_name: ProviderName,
        events: list[ExternalCalendarEvent],
    ) -> list[CalendarEvent]:
        saved_events: list[CalendarEvent] = []

        for external_event in events:
            existing = self.db.scalar(
                select(CalendarEvent).where(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.connected_account_id == connected_account_id,
                    CalendarEvent.provider_name == provider_name,
                    CalendarEvent.external_event_id == external_event.external_id,
                )
            )

            if existing is None:
                existing = CalendarEvent(
                    user_id=user_id,
                    connected_account_id=connected_account_id,
                    provider_name=provider_name,
                    external_event_id=external_event.external_id,
                    calendar_id=external_event.external_calendar_id,
                    calendar_name=external_event.external_calendar_name,
                    title=external_event.title,
                    description=external_event.description,
                    location=external_event.location,
                    starts_at=external_event.starts_at,
                    ends_at=external_event.ends_at,
                    timezone=external_event.timezone,
                )
                self.db.add(existing)
            else:
                existing.calendar_id = external_event.external_calendar_id
                existing.calendar_name = external_event.external_calendar_name
                existing.title = external_event.title
                existing.description = external_event.description
                existing.location = external_event.location
                existing.starts_at = external_event.starts_at
                existing.ends_at = external_event.ends_at
                existing.timezone = external_event.timezone

            saved_events.append(existing)

        self.db.commit()
        for event in saved_events:
            self.db.refresh(event)
        return saved_events

    def delete_missing_external_ids(
        self,
        *,
        user_id: UUID,
        connected_account_id: UUID,
        provider_name: ProviderName,
        keep_external_ids: set[str],
    ) -> int:
        stmt = delete(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.connected_account_id == connected_account_id,
            CalendarEvent.provider_name == provider_name,
        )
        if keep_external_ids:
            stmt = stmt.where(CalendarEvent.external_event_id.not_in(keep_external_ids))

        result = self.db.execute(stmt)
        self.db.commit()
        return int(result.rowcount or 0)
