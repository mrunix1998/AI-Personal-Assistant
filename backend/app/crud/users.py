from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate

class UserRepository:
    def __init__(self, db: Session): self.db = db
    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()
    def get(self, user_id) -> User | None:
        return self.db.get(User, user_id)
    def create(self, payload: UserCreate) -> User:
        user = User(email=payload.email, full_name=payload.full_name, hashed_password=get_password_hash(payload.password))
        self.db.add(user); self.db.commit(); self.db.refresh(user); return user
    def authenticate(self, email: str, password: str) -> User | None:
        user = self.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password): return None
        return user
