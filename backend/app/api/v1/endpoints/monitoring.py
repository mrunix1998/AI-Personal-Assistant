from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/readiness")
def readiness(db: Session = Depends(get_db)) -> dict[str, Any]:
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)) -> dict[str, Any]:
    tables = ["users", "calendar_events", "task_items", "reminders", "notifications", "notification_channels"]
    data: dict[str, int] = {}
    for table in tables:
        try:
            data[table] = int(db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)
        except Exception:
            data[table] = -1
    return {"status": "ok", "counts": data}
