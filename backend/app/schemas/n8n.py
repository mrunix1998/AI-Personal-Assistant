from datetime import date
from uuid import UUID

from pydantic import BaseModel


class N8nDailySummaryTriggerResponse(BaseModel):
    status: str
    user_id: UUID
    agenda_date: date
    n8n_response: dict | list | str | None = None
