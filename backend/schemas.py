from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
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

    @field_validator('user_name')
    @classmethod
    def validate_user_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Username cannot be empty')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

    @field_validator('email')
    @classmethod
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

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        if v is not None and v not in [0, 10]:
            raise ValueError('Type must be 0 (regular user) or 10 (admin)')
        return v

    @field_validator('family_id')
    @classmethod
    def validate_family_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Family ID must be a positive integer')
        return v

    @field_validator('status')
    @classmethod
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

    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    user_name: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class LogoutResponse(BaseModel):
    message: str


class CategoryResponse(BaseModel):
    id: int
    family_id: int
    name: str
    description: Optional[str]
    status: int
    create_date: datetime
    update_date: datetime

    model_config = ConfigDict(from_attributes=True)


class PictureResponse(BaseModel):
    id: int
    family_id: int
    uploaded_by: int
    title: Optional[str]
    description: Optional[str]
    file_path: str
    thumbnail_path: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    width: Optional[int]
    height: Optional[int]
    taken_date: Optional[datetime]
    category_id: Optional[int]
    status: int
    create_date: datetime
    update_date: datetime

    model_config = ConfigDict(from_attributes=True)


class PictureCreateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        if v is not None and len(v) > 255:
            raise ValueError('Title must be 255 characters or less')
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v

    @field_validator('category_id')
    @classmethod
    def validate_category_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Category ID must be a positive integer')
        return v


class PictureListResponse(BaseModel):
    pictures: list[PictureResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class CommentResponse(BaseModel):
    id: int
    content: str
    user_id: int
    picture_id: int
    user_name: str
    create_date: datetime
    update_date: datetime

    model_config = ConfigDict(from_attributes=True)