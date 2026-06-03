import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import ProviderName


class TaskItem(Base):
    __tablename__ = "task_items"
    __table_args__ = (UniqueConstraint("provider_name", "external_task_id", name="uq_provider_task"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("connected_accounts.id"), index=True)
    provider_name: Mapped[ProviderName] = mapped_column(Enum(ProviderName), index=True)
    external_task_id: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
