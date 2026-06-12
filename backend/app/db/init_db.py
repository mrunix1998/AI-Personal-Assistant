from app.db.session import Base, engine
from app.models import user, connected_account, calendar_event, task_item, reminder, notification_channel, provider_secret, notification, web_push_subscription  # noqa

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
