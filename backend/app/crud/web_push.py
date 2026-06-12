from sqlalchemy.orm import Session
from app.models.web_push_subscription import WebPushSubscription
from app.schemas.notifications import WebPushSubscriptionCreate

class WebPushRepository:
    def __init__(self, db: Session): self.db = db
    def upsert(self, user_id, payload: WebPushSubscriptionCreate) -> WebPushSubscription:
        obj = self.db.query(WebPushSubscription).filter(WebPushSubscription.user_id==user_id, WebPushSubscription.endpoint==payload.endpoint).first()
        if obj:
            obj.p256dh=payload.p256dh; obj.auth=payload.auth; obj.user_agent=payload.user_agent; obj.is_enabled=True
        else:
            obj = WebPushSubscription(user_id=user_id, **payload.model_dump())
            self.db.add(obj)
        self.db.commit(); self.db.refresh(obj); return obj
    def list_for_user(self, user_id) -> list[WebPushSubscription]:
        return self.db.query(WebPushSubscription).filter(WebPushSubscription.user_id==user_id, WebPushSubscription.is_enabled==True).all()
    def delete(self, user_id, subscription_id) -> bool:
        obj = self.db.query(WebPushSubscription).filter(WebPushSubscription.user_id==user_id, WebPushSubscription.id==subscription_id).first()
        if not obj: return False
        self.db.delete(obj); self.db.commit(); return True
