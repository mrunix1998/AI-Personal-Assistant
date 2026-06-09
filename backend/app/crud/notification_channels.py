from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification_channel import NotificationChannel
from app.schemas.notifications import NotificationChannelCreate


class NotificationChannelRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(self, *, user_id: UUID, payload: NotificationChannelCreate) -> NotificationChannel:
        channel = (
            self.db.query(NotificationChannel)
            .filter(
                NotificationChannel.user_id == user_id,
                NotificationChannel.channel == payload.channel,
                NotificationChannel.destination == payload.destination,
            )
            .first()
        )
        if channel:
            channel.display_name = payload.display_name
            channel.is_enabled = payload.is_enabled
        else:
            channel = NotificationChannel(
                user_id=user_id,
                channel=payload.channel,
                destination=payload.destination,
                display_name=payload.display_name,
                is_enabled=payload.is_enabled,
            )
            self.db.add(channel)

        self.db.commit()
        self.db.refresh(channel)
        return channel

    def list_for_user(self, *, user_id: UUID) -> list[NotificationChannel]:
        return (
            self.db.query(NotificationChannel)
            .filter(NotificationChannel.user_id == user_id)
            .order_by(NotificationChannel.created_at.desc())
            .all()
        )

    def get_enabled_channel(self, *, user_id: UUID, channel: str) -> NotificationChannel | None:
        return (
            self.db.query(NotificationChannel)
            .filter(
                NotificationChannel.user_id == user_id,
                NotificationChannel.channel == channel,
                NotificationChannel.is_enabled.is_(True),
            )
            .order_by(NotificationChannel.created_at.desc())
            .first()
        )
