from sqlalchemy.orm import Session
from app.models.notification_channel import NotificationChannel

class NotificationChannelRepository:
    def __init__(self, db: Session): self.db = db
    def upsert(self, user_id, channel: str, destination: str, display_name: str | None = None) -> NotificationChannel:
        obj = self.db.query(NotificationChannel).filter(NotificationChannel.user_id==user_id, NotificationChannel.channel==channel).first()
        if obj:
            obj.destination = destination; obj.display_name = display_name; obj.is_enabled = True
        else:
            obj = NotificationChannel(user_id=user_id, channel=channel, destination=destination, display_name=display_name, is_enabled=True)
            self.db.add(obj)
        self.db.commit(); self.db.refresh(obj); return obj
    def list_for_user(self, user_id) -> list[NotificationChannel]:
        return self.db.query(NotificationChannel).filter(NotificationChannel.user_id==user_id).all()
    def get_enabled_channel(self, user_id, channel: str) -> NotificationChannel | None:
        return self.db.query(NotificationChannel).filter(NotificationChannel.user_id==user_id, NotificationChannel.channel==channel, NotificationChannel.is_enabled==True).first()  # noqa
