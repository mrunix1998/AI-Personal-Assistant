import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ProviderSecret(Base):
    """Encrypted API tokens/config used by backend-triggered n8n workflows.

    Examples:
    - provider='telegram', secret_key='bot_token'
    - provider='email', secret_key='smtp_password'
    - provider='whatsapp', secret_key='twilio_auth_token'
    - provider='notion', secret_key='integration_token'
    - provider='jira', secret_key='api_token'

    user_id is nullable so we can support both:
    - user-owned tokens (user_id set)
    - app-level/system tokens (user_id null), e.g. one Telegram bot for the app
    """

    __tablename__ = "provider_secrets"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", "secret_key", name="uq_provider_secret_user_provider_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    secret_key: Mapped[str] = mapped_column(String(120), index=True)
    encrypted_value: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
