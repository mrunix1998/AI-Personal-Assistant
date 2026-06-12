from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.provider_secrets import ProviderSecret
from app.core.token_crypto import decrypt_secret, encrypt_secret


class ProviderSecretRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert(self, user_id, provider_name: str, secret_name: str, secret_value: str) -> ProviderSecret:
        obj = (
            self.db.query(ProviderSecret)
            .filter(ProviderSecret.user_id == user_id, ProviderSecret.provider == provider_name, ProviderSecret.key == secret_name)
            .first()
        )
        encrypted = encrypt_secret(secret_value)
        if obj:
            obj.encrypted_value = encrypted
            obj.updated_at = datetime.now(timezone.utc)
        else:
            obj = ProviderSecret(user_id=user_id, provider=provider_name, key=secret_name, encrypted_value=encrypted)
            self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_value(self, user_id, provider_name: str, secret_name: str) -> str | None:
        obj = (
            self.db.query(ProviderSecret)
            .filter(ProviderSecret.user_id == user_id, ProviderSecret.provider == provider_name, ProviderSecret.key == secret_name)
            .first()
        )
        return decrypt_secret(obj.encrypted_value) if obj else None

    def list_for_user(self, user_id):
        return self.db.query(ProviderSecret).filter(ProviderSecret.user_id == user_id).all()
