from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.token_crypto import decrypt_secret, encrypt_secret
from app.models.provider_secret import ProviderSecret
from app.schemas.provider_secrets import ProviderSecretCreate


class ProviderSecretRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(self, *, payload: ProviderSecretCreate, user_id: UUID | None = None) -> ProviderSecret:
        stmt = select(ProviderSecret).where(
            ProviderSecret.user_id.is_(None) if user_id is None else ProviderSecret.user_id == user_id,
            ProviderSecret.provider == payload.provider,
            ProviderSecret.secret_key == payload.secret_key,
        )
        existing = self.db.scalar(stmt)
        encrypted_value = encrypt_secret(payload.value)

        if existing is not None:
            existing.encrypted_value = encrypted_value or ""
            existing.display_name = payload.display_name
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        secret = ProviderSecret(
            user_id=user_id,
            provider=payload.provider,
            secret_key=payload.secret_key,
            encrypted_value=encrypted_value or "",
            display_name=payload.display_name,
        )
        self.db.add(secret)
        self.db.commit()
        self.db.refresh(secret)
        return secret

    def get(self, *, provider: str, secret_key: str, user_id: UUID | None = None) -> ProviderSecret | None:
        stmt = select(ProviderSecret).where(
            ProviderSecret.user_id.is_(None) if user_id is None else ProviderSecret.user_id == user_id,
            ProviderSecret.provider == provider,
            ProviderSecret.secret_key == secret_key,
        )
        return self.db.scalar(stmt)

    def get_decrypted_value(self, *, provider: str, secret_key: str, user_id: UUID | None = None) -> str | None:
        secret = self.get(provider=provider, secret_key=secret_key, user_id=user_id)
        if secret is None:
            return None
        return decrypt_secret(secret.encrypted_value)

    def list_metadata(self, *, user_id: UUID | None = None) -> list[ProviderSecret]:
        stmt = select(ProviderSecret).where(
            ProviderSecret.user_id.is_(None) if user_id is None else ProviderSecret.user_id == user_id,
        ).order_by(ProviderSecret.provider, ProviderSecret.secret_key)
        return list(self.db.scalars(stmt).all())
