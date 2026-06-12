import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (UniqueConstraint("user_id", "calendar_event_id", "remind_at", name="uq_event_reminder"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    calendar_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("calendar_events.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    message: Mapped[str] = mapped_column(String(1000))
    channel: Mapped[str] = mapped_column(String(50), default="web")
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
