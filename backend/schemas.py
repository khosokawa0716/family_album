from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    user_name: str
    password: str
    email: Optional[str] = None
    type: int = 0
    family_id: int

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