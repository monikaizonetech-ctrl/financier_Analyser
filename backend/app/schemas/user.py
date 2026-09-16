from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.core import RoleEnum

class UserBase(BaseModel):
    email: EmailStr
    name: str
    phone_number: Optional[str] = None

class UserCreate(UserBase):
    password: str
    role: Optional[RoleEnum] = RoleEnum.FINANCIER

class UserResponse(UserBase):
    id: str
    role: RoleEnum
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
