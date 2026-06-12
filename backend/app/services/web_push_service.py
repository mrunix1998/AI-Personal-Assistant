import logging
from pywebpush import WebPushException, webpush
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class WebPushService:
    def __init__(self):
        self.settings = get_settings()

    def configured(self) -> bool:
        return bool(self.settings.vapid_private_key and self.settings.vapid_public_key)

    def send(self, subscription, title: str, message: str) -> dict:
        if not self.configured():
            return {"status": "skipped", "reason": "VAPID is not configured"}
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        }
        payload = {"title": title, "body": message}
        try:
            webpush(
                subscription_info=subscription_info,
                data=__import__("json").dumps(payload),
                vapid_private_key=self.settings.vapid_private_key,
                vapid_claims={"sub": self.settings.vapid_subject},
            )
            return {"status": "sent", "endpoint": subscription.endpoint}
        except WebPushException as exc:
            logger.warning("web_push_failed", extra={"endpoint": subscription.endpoint, "error": str(exc)})
            return {"status": "failed", "endpoint": subscription.endpoint, "error": str(exc)}
