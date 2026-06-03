from app.db.session import Base, engine
from app import models  # noqa: F401 - imports model metadata


def init_db() -> None:
    # MVP only. In production we will switch this to Alembic migrations.
    Base.metadata.create_all(bind=engine)
