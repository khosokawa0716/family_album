from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    user_name: str
    password: str
    email: Optional[str] = None
    type: int = 0
    family_id: int

class UserUpdate(BaseModel):
    user_name: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    type: Optional[int] = None
    family_id: Optional[int] = None
    status: Optional[int] = None

    @validator('user_name')
    def validate_user_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Username cannot be empty')
        return v

    @validator('password')
    def validate_password(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

    @validator('email')
    def validate_email(cls, v):
        if v is not None and v.strip() == "":
            return None  # 空文字はNoneに変換
        if v is not None:
            # 簡単なメール形式チェック
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Invalid email format')
        return v

    @validator('type')
    def validate_type(cls, v):
        if v is not None and v not in [0, 10]:
            raise ValueError('Type must be 0 (regular user) or 10 (admin)')
        return v

    @validator('family_id')
    def validate_family_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Family ID must be a positive integer')
        return v

    @validator('status')
    def validate_status(cls, v):
        if v is not None and v not in [0, 1]:
            raise ValueError('Status must be 0 (disabled) or 1 (enabled)')
        return v

class UserResponse(BaseModel):
    id: int
    user_name: str
    email: Optional[str]
    type: int
    family_id: int
    status: int
    create_date: datetime
    update_date: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    user_name: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class LogoutResponse(BaseModel):
    message: str