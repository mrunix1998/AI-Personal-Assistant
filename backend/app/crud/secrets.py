import uuid
from sqlalchemy.orm import Session
#from app.core.security import decrypt_secret, encrypt_secret
from app.core.token_crypto import decrypt_secret, encrypt_secret
from app.models.provider_secrets import ProviderSecret

class SecretRepository:
    def __init__(self, db: Session):
        self.db = db
    def set(self, user_id: uuid.UUID, provider: str, key: str, value: str) -> ProviderSecret:
        obj = self.db.query(ProviderSecret).filter_by(user_id=user_id, provider=provider, key=key).first()
        encrypted = encrypt_secret(value)
        if obj:
            obj.encrypted_value = encrypted
        else:
            obj = ProviderSecret(user_id=user_id, provider=provider, key=key, encrypted_value=encrypted)
            self.db.add(obj)
        self.db.commit(); self.db.refresh(obj); return obj
    def get(self, user_id: uuid.UUID, provider: str, key: str) -> str | None:
        obj = self.db.query(ProviderSecret).filter_by(user_id=user_id, provider=provider, key=key).first()
        return decrypt_secret(obj.encrypted_value) if obj else None
    def list_public(self, user_id: uuid.UUID):
        return self.db.query(ProviderSecret).filter_by(user_id=user_id).all()
    def get_many(self, user_id: uuid.UUID, provider: str, keys: list[str]) -> dict[str, str | None]:
        return {k: self.get(user_id, provider, k) for k in keys}
