from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.crud.notification_channels import NotificationChannelRepository
from app.crud.notifications import NotificationRepository
from app.crud.provider_secrets import ProviderSecretRepository


@dataclass(frozen=True)
class DeliveryResult:
    channel: str
    ok: bool
    detail: str
    response: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "ok": self.ok,
            "detail": self.detail,
            "response": self.response,
        }


class NotificationDeliveryService:
    """Direct production notification delivery, independent from n8n.

    Reads encrypted Telegram/SMTP credentials from provider_secrets and enabled
    destinations from notification_channels.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.channels = NotificationChannelRepository(db)
        self.secrets = ProviderSecretRepository(db)
        self.notifications = NotificationRepository(db)

    async def send_telegram(self, *, user_id: UUID, message: str) -> DeliveryResult:
        channel = self.channels.get_enabled_channel(user_id, "telegram")
        bot_token = self.secrets.get_value(user_id, "telegram", "bot_token")
        if channel is None or not bot_token:
            return DeliveryResult("telegram", False, "Telegram bot token or chat id is missing")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": channel.destination, "text": message},
            )
        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text}
        if response.status_code >= 400 or not payload.get("ok", False):
            return DeliveryResult("telegram", False, response.text, payload)
        return DeliveryResult("telegram", True, "sent", payload)

    def send_email(self, *, user_id: UUID, subject: str, message: str) -> DeliveryResult:
        channel = self.channels.get_enabled_channel(user_id, "email")
        required = ["smtp_host", "smtp_port", "smtp_username", "smtp_password", "smtp_from_email"]
        values = {key: self.secrets.get_value(user_id, "email", key) for key in required}
        missing = [key for key, value in values.items() if not value]
        if channel is None:
            return DeliveryResult("email", False, "Email channel is not connected")
        if missing:
            return DeliveryResult("email", False, f"Missing email config: {', '.join(missing)}")

        email = EmailMessage()
        email["Subject"] = subject
        email["From"] = values["smtp_from_email"]
        email["To"] = channel.destination
        email.set_content(message)

        try:
            with smtplib.SMTP(values["smtp_host"], int(values["smtp_port"]), timeout=30) as smtp:
                smtp.starttls()
                smtp.login(values["smtp_username"], values["smtp_password"])
                smtp.send_message(email)
        except Exception as exc:
            return DeliveryResult("email", False, str(exc))
        return DeliveryResult("email", True, "sent", {"to": channel.destination, "subject": subject})

    async def deliver_to_user(
        self,
        *,
        user_id: UUID,
        title: str,
        message: str,
        source: str = "automation",
        create_web_notification: bool = True,
        send_telegram: bool = True,
        send_email: bool = True,
    ) -> list[dict[str, Any]]:
        results: list[DeliveryResult] = []
        if create_web_notification:
            self.notifications.create(user_id, title, message, source=source, channel="web")
            results.append(DeliveryResult("web", True, "created"))
        if send_telegram:
            results.append(await self.send_telegram(user_id=user_id, message=f"{title}\n\n{message}"))
        if send_email:
            results.append(self.send_email(user_id=user_id, subject=title, message=message))
        return [result.as_dict() for result in results]
