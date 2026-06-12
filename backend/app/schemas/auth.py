from pydantic import BaseModel, EmailStr, Field
import uuid

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = None

class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    model_config = {"from_attributes": True}

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
