from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.integrations.calendars.google import GoogleCalendarProvider
from app.models.user import User

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/google/connect")
async def connect_google_calendar(
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    # Next step: persist OAuth state in DB/Redis and bind it to current_user.id.
    state = f"{current_user.id}:{uuid4()}"
    authorization_url = await GoogleCalendarProvider().build_authorization_url(state=state)
    return {"authorization_url": authorization_url, "state": state}


@router.get("/google/callback")
async def google_oauth_callback(code: str, state: str, db: Session = Depends(get_db)) -> dict:
    # Next step: validate state and save encrypted tokens in connected_accounts.
    tokens = await GoogleCalendarProvider().exchange_code_for_tokens(code=code)
    return {"state": state, "token_type": tokens.get("token_type"), "expires_in": tokens.get("expires_in")}
