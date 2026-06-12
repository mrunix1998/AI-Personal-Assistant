import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TaskItem(Base):
    __tablename__ = "task_items"
    __table_args__ = (UniqueConstraint("provider_name", "external_task_id", name="uq_provider_task"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    connected_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("connected_accounts.id"), index=True, nullable=True)

    # Keep provider_name as string, not DB enum. This lets us add providers like todoist/notion later.
    provider_name: Mapped[str] = mapped_column(String(100), index=True)
    external_task_id: Mapped[str] = mapped_column(String(255), index=True)

    title: Mapped[str] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Planning Engine fields
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
