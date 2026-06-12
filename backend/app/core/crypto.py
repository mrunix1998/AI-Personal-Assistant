from cryptography.fernet import Fernet
from app.core.config import get_settings

class TokenCipher:
    def __init__(self) -> None:
        self.fernet = Fernet(get_settings().token_encryption_key.encode())
    def encrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self.fernet.encrypt(value.encode()).decode()
    def decrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self.fernet.decrypt(value.encode()).decode()
