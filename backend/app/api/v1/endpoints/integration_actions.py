from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import smtplib
from email.message import EmailMessage
from app.api.deps import get_current_user
from app.crud.notification_channels import NotificationChannelRepository
from app.crud.provider_secrets import ProviderSecretRepository
from app.db.session import get_db
from app.models.user import User
#
router = APIRouter(prefix="/integration-actions", tags=["integration-actions"])


@router.post("/telegram/save")
def save_telegram(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bot_token = payload.get("bot_token")
    chat_id = payload.get("chat_id")
    if not bot_token or not chat_id:
        raise HTTPException(status_code=400, detail="bot_token and chat_id are required")

    ProviderSecretRepository(db).upsert(current_user.id, "telegram", "bot_token", bot_token)
    channel = NotificationChannelRepository(db).upsert(current_user.id, "telegram", chat_id, payload.get("display_name"))
    return {"status": "saved", "channel": {"id": str(channel.id), "destination": channel.destination}}


@router.post("/telegram/test")
async def test_telegram(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = payload.get("message") or "✅ Telegram test from AI Personal Assistant"
    bot_token = ProviderSecretRepository(db).get_value(current_user.id, "telegram", "bot_token")
    channel = NotificationChannelRepository(db).get_enabled_channel(current_user.id, "telegram")
    if not bot_token or not channel:
        raise HTTPException(status_code=400, detail="Telegram bot token or chat_id is missing")

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": channel.destination, "text": message},
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=res.text)
    return {"status": "sent", "telegram_response": res.json()}


@router.post("/email/save")
def save_email(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProviderSecretRepository(db)

    allowed_keys = [
        "smtp_host",
        "smtp_port",
        "smtp_username",
        "smtp_password",
        "smtp_from_email",
        "to_email",
    ]

    for key in allowed_keys:
        value = payload.get(key)
        if value is not None and str(value).strip() != "":
            repo.upsert(current_user.id, "email", key, str(value).strip())

    to_email = payload.get("to_email")
    channel = None
    if to_email and str(to_email).strip():
        channel = NotificationChannelRepository(db).upsert(
            current_user.id,
            "email",
            str(to_email).strip(),
            "Email",
        )

    return {
        "status": "saved",
        "provider": "email",
        "saved_keys": allowed_keys,
        "channel": {"id": str(channel.id), "destination": channel.destination} if channel else None,
    }

@router.post("/email/test")
async def test_email(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProviderSecretRepository(db)

    required_keys = ["smtp_host", "smtp_port", "smtp_username", "smtp_password", "smtp_from_email", "to_email"]
    keys = {key: repo.get_value(current_user.id, "email", key) for key in required_keys}

    missing = [key for key, value in keys.items() if not value]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing email config: {', '.join(missing)}",
        )

    message_text = payload.get("message") or "✅ Email test from AI Personal Assistant"

    msg = EmailMessage()
    msg["Subject"] = "AI Personal Assistant - Email Test"
    msg["From"] = keys["smtp_from_email"]
    msg["To"] = keys["to_email"]
    msg.set_content(message_text)

    try:
        with smtplib.SMTP(keys["smtp_host"], int(keys["smtp_port"])) as server:
            server.starttls()
            server.login(keys["smtp_username"], keys["smtp_password"])
            server.send_message(msg)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not send test email: {exc}",
        ) from exc

    return {
        "status": "sent",
        "channel": "email",
        "to_email": keys["to_email"],
    }


@router.post("/notion/save")
def save_notion(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = payload.get("notion_token")
    if not token:
        raise HTTPException(status_code=400, detail="notion_token is required")

    repo = ProviderSecretRepository(db)
    repo.upsert(current_user.id, "notion", "notion_token", token)
    if payload.get("database_id"):
        repo.upsert(current_user.id, "notion", "database_id", payload["database_id"])

    return {"status": "saved", "provider": "notion"}


@router.post("/notion/test")
async def test_notion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = ProviderSecretRepository(db).get_value(current_user.id, "notion", "notion_token")
    if not token:
        raise HTTPException(status_code=400, detail="Notion token missing")

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            "https://api.notion.com/v1/users/me",
            headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"},
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=res.text)
    return {"status": "connected", "notion_response": res.json()}


@router.post("/jira/save")
def save_jira(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    required = ["jira_base_url", "jira_email", "jira_api_token"]
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing)}")

    repo = ProviderSecretRepository(db)
    for key in ["jira_base_url", "jira_email", "jira_api_token", "jira_project_key"]:
        if payload.get(key):
            repo.upsert(current_user.id, "jira", key, payload[key])

    return {"status": "saved", "provider": "jira"}


@router.post("/jira/test")
async def test_jira(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProviderSecretRepository(db)
    keys = {key: repo.get_value(current_user.id, "jira", key) for key in ["jira_base_url", "jira_email", "jira_api_token"]}
    if any(value is None for value in keys.values()):
        raise HTTPException(status_code=400, detail="Jira config missing")

    base_url = keys["jira_base_url"].rstrip("/")
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            f"{base_url}/rest/api/3/myself",
            auth=(keys["jira_email"], keys["jira_api_token"]),
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=res.text)
    return {"status": "connected", "jira_response": res.json()}


@router.post("/outlook/save")
def save_outlook(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProviderSecretRepository(db)
    for key, value in payload.items():
        if value:
            repo.upsert(current_user.id, "outlook", key, str(value))
    return {"status": "saved", "provider": "outlook"}


@router.post("/outlook/test")
async def test_outlook(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = ProviderSecretRepository(db).get_value(current_user.id, "outlook", "outlook_access_token")
    if not token:
        raise HTTPException(status_code=400, detail="Outlook Graph access token missing")

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(
            "https://graph.microsoft.com/v1.0/me/events?$top=1",
            headers={"Authorization": f"Bearer {token}"},
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=res.text)
    return {"status": "connected", "outlook_response": res.json()}


@router.post("/apple-ics/save")
def save_apple_ics(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ics_url = payload.get("ics_url")
    if not ics_url:
        raise HTTPException(status_code=400, detail="ics_url is required")

    repo = ProviderSecretRepository(db)
    repo.upsert(current_user.id, "apple_ics", "ics_url", ics_url)
    return {"status": "saved", "provider": "apple_ics"}


@router.post("/apple-ics/test")
async def test_apple_ics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ics_url = ProviderSecretRepository(db).get_value(current_user.id, "apple_ics", "ics_url")
    if not ics_url:
        raise HTTPException(status_code=400, detail="Apple/ICS URL missing")

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        res = await client.get(ics_url)
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=res.text[:500])
    text = res.text
    return {
        "status": "connected",
        "looks_like_ics": "BEGIN:VCALENDAR" in text,
        "size": len(text),
    }
