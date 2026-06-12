import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (UniqueConstraint("user_id", "provider_name", "external_event_id", name="uq_user_provider_event"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    connected_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("connected_accounts.id"),nullable=True,index=True,)
    provider_name: Mapped[str] = mapped_column(String(100), index=True)
    external_event_id: Mapped[str] = mapped_column(String(500), index=True)
    calendar_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    calendar_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)