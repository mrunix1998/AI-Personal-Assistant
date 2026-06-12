from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.crud.secrets import SecretRepository
from app.db.session import get_db
from app.models.user import User
from app.schemas.secrets import SecretRead, SecretSave
router=APIRouter(prefix="/secrets",tags=["secrets"])
@router.post("",response_model=SecretRead)
def save_secret(payload:SecretSave, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    SecretRepository(db).set(current_user.id,payload.provider,payload.key,payload.value); return SecretRead(provider=payload.provider,key=payload.key)
@router.get("",response_model=list[SecretRead])
def list_secrets(db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    return [SecretRead(provider=s.provider,key=s.key) for s in SecretRepository(db).list_public(current_user.id)]
