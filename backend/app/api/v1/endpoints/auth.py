from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token
from app.crud.users import UserRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserRead, LoginRequest, TokenRead
router=APIRouter(prefix="/auth", tags=["auth"])
@router.post("/register", response_model=UserRead, status_code=201)
def register(payload:UserCreate, db:Session=Depends(get_db)):
    repo=UserRepository(db)
    if repo.get_by_email(payload.email): raise HTTPException(409,"Email already registered")
    return repo.create(payload)
@router.post("/login", response_model=TokenRead)
def login(payload:LoginRequest, db:Session=Depends(get_db)):
    user=UserRepository(db).authenticate(payload.email,payload.password)
    if not user: raise HTTPException(401,"Invalid credentials")
    token=create_access_token(str(user.id), timedelta(minutes=get_settings().access_token_expire_minutes))
    return TokenRead(access_token=token)
@router.get("/me", response_model=UserRead)
def me(current_user:User=Depends(get_current_user)): return current_user
