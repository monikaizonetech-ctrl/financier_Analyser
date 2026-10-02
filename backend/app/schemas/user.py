from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.user import UserRole, UserStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    phone: str | None = None
    role: UserRole
    status: UserStatus
    created_at: datetime


class UserCreateByAdmin(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.MEMBER


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None


class PaginatedUsers(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int
