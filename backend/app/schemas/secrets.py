from pydantic import BaseModel

class SecretSave(BaseModel):
    provider: str
    key: str
    value: str

class SecretRead(BaseModel):
    provider: str
    key: str
