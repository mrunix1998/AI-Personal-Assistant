from datetime import datetime
from pydantic import BaseModel
import uuid

class ReminderRead(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    channel: str
    status: str
    remind_at: datetime
    model_config = {"from_attributes": True}
