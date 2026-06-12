from datetime import datetime
from pydantic import BaseModel
import uuid

class ConnectedAccountRead(BaseModel):
    id: uuid.UUID
    provider_name: str
    provider_type: str
    external_account_id: str
    token_expires_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}
