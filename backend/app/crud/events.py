import uuid
from sqlalchemy.orm import Session
from app.models.calendar_events import CalendarEvent
from app.schemas.events import EventCreate

class EventRepository:
    def __init__(self, db: Session): self.db = db
    def upsert(self, user_id: uuid.UUID, payload: EventCreate) -> CalendarEvent:
        obj = self.db.query(CalendarEvent).filter_by(user_id=user_id, provider_name=payload.provider_name, external_event_id=payload.external_event_id).first()
        if not obj:
            obj = CalendarEvent(user_id=user_id, provider_name=payload.provider_name, external_event_id=payload.external_event_id, title=payload.title, starts_at=payload.starts_at, ends_at=payload.ends_at)
            self.db.add(obj)
        obj.calendar_id=payload.calendar_id; obj.calendar_name=payload.calendar_name; obj.title=payload.title
        obj.description=payload.description; obj.location=payload.location; obj.starts_at=payload.starts_at; obj.ends_at=payload.ends_at; obj.timezone=payload.timezone
        self.db.commit(); self.db.refresh(obj); return obj
    def import_many(self, user_id: uuid.UUID, events: list[EventCreate]):
        return [self.upsert(user_id, e) for e in events]
    def daily(self, user_id: uuid.UUID, day_start, day_end):
        return self.db.query(CalendarEvent).filter(CalendarEvent.user_id==user_id, CalendarEvent.starts_at < day_end, CalendarEvent.ends_at > day_start).order_by(CalendarEvent.starts_at).all()
