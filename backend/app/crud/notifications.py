from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.notification import Notification

class NotificationRepository:
    def __init__(self, db: Session): self.db = db
    def create(self, user_id, title: str, message: str, source="system", channel="web", agenda_date=None) -> Notification:
        obj = Notification(user_id=user_id, title=title, message=message, source=source, channel=channel, agenda_date=agenda_date)
        self.db.add(obj); self.db.commit(); self.db.refresh(obj); return obj
    def list_for_user(self, user_id) -> list[Notification]:
        return self.db.query(Notification).filter(Notification.user_id==user_id).order_by(Notification.created_at.desc()).all()
    def mark_read(self, user_id, notification_id):
        obj = self.db.query(Notification).filter(Notification.user_id==user_id, Notification.id==notification_id).first()
        if not obj: return None
        obj.status="read"; obj.read_at=datetime.now(timezone.utc); self.db.commit(); self.db.refresh(obj); return obj
    def mark_all_read(self, user_id) -> int:
        objs = self.db.query(Notification).filter(Notification.user_id==user_id, Notification.status=="unread").all()
        now = datetime.now(timezone.utc)
        for o in objs: o.status="read"; o.read_at=now
        self.db.commit(); return len(objs)
