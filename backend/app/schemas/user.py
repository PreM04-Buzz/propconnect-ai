from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    role: UserRole = UserRole.agent


class UserCreate(UserBase):
    email: EmailStr  # strict validation on input only
    password: str = Field(min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str  # plain str on output so a stored address never breaks a response
    is_active: bool
    created_at: datetime
