from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import re


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128, description="User's password")

    @validator('password')
    def validate_password(cls, v):
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]', v):
            raise ValueError(
                'Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character')
        return v

    @validator('full_name')
    def validate_full_name(cls, v):
        if not re.match(r'^[a-zA-Z\s]+$', v):
            raise ValueError('Full name must contain only letters and spaces')
        return v.strip()


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, description="User's email address")
    full_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's full name")
    is_active: Optional[bool] = Field(None, description="User's active status")

    @validator('full_name')
    def validate_full_name(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z\s]+$', v):
                raise ValueError('Full name must contain only letters and spaces')
            return v.strip()
        return v


class UserInDB(UserBase):
    #id: UUID = Field(..., description="User's unique identifier")
    is_active: bool = Field(default=True, description="User's active status")
    #created_at: datetime = Field(..., description="User creation timestamp")
    #updated_at: datetime = Field(..., description="User last update timestamp")

    class Config:
        from_attributes = True


class User(UserInDB):
    pass


class UserWithPermissions(User):
    permissions: List[str] = Field(default_factory=list, description="User's permissions")


class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenData(BaseModel):
    email: Optional[str] = Field(None, description="User's email from token")
    user_id: Optional[UUID] = Field(None, description="User's ID from token")