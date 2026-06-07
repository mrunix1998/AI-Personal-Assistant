import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PlanningResult(Base):
    __tablename__ = "planning_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    plan_date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(100), default="n8n_rule_based")
    status: Mapped[str] = mapped_column(String(50), default="generated")
    plan_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
