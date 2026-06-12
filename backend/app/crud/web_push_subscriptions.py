from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.web_push_subscriptions import WebPushSubscription
from app.schemas.notifications import WebPushSubscriptionCreate


class WebPushSubscriptionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(self, *, user_id: UUID, payload: WebPushSubscriptionCreate) -> WebPushSubscription:
        sub = (
            self.db.query(WebPushSubscription)
            .filter(
                WebPushSubscription.user_id == user_id,
                WebPushSubscription.endpoint == payload.endpoint,
            )
            .first()
        )
        if sub:
            sub.p256dh = payload.p256dh
            sub.auth = payload.auth
            sub.user_agent = payload.user_agent
            sub.is_enabled = True
        else:
            sub = WebPushSubscription(
                user_id=user_id,
                endpoint=payload.endpoint,
                p256dh=payload.p256dh,
                auth=payload.auth,
                user_agent=payload.user_agent,
                is_enabled=True,
            )
            self.db.add(sub)
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def list_enabled(self, *, user_id: UUID) -> list[WebPushSubscription]:
        return (
            self.db.query(WebPushSubscription)
            .filter(
                WebPushSubscription.user_id == user_id,
                WebPushSubscription.is_enabled.is_(True),
            )
            .order_by(WebPushSubscription.created_at.desc())
            .all()
        )

    def disable(self, *, user_id: UUID, subscription_id: UUID) -> bool:
        sub = (
            self.db.query(WebPushSubscription)
            .filter(WebPushSubscription.user_id == user_id, WebPushSubscription.id == subscription_id)
            .first()
        )
        if sub is None:
            return False
        sub.is_enabled = False
        self.db.commit()
        return True
