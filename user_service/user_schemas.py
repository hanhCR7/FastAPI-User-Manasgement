from pydantic import BaseModel, EmailStr, field_validator
from enum import Enum
from typing import Optional
from datetime import datetime
import re
# Enum UserStatus
class UserStatus(str, Enum):
    Active = "Active"
    Inactive = "Inactive"
    Banned = "Banned"
# Schema cho việc tạo user (request)
class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password_hash: str  
    status: UserStatus = UserStatus.Active
    def validate_new_password(cls, value):
        if len(value) < 8:
            raise ValueError("Mật khẩu phải có độ dài ít nhất 8 ký tự")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValueError("Mật khẩu phải chứa it nhất 1 ký tự đặc biệt")
        if not re.search(r'[0-9]', value):
            raise ValueError("Mật khẩu phải chứa ít nhất một số")
        if not re.search(r'[A-Z]', value):
            raise ValueError("Mật khẩu phải chứa ít nhất một chữ cái viết hoa")
        return value
# Schema cho response user
class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    status: Optional[UserStatus] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    class Config:
        from_attributes  = True
class AuthRequest(BaseModel):
    username: str
    password: str 
class UpdatePassword(BaseModel):
    old_password: str
    new_password: str
    confirm_new_password: str
class LogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    timestamp: datetime
    class Config:
        from_attributes  = True
class LogRequest(BaseModel):
    user_id: int
    action: str
class ListUserActive(BaseModel):
    id: int
    username: str
    is_active: bool
    status: Optional[UserStatus]
    class Config:
        from_attributes  = True
class EditUserActive(BaseModel):
    status: Optional[UserStatus]
    is_active: bool
    class Config:
        from_attributes  = True
class ActivationTokenRequest(BaseModel):
    user_id: int

class EmailResquest(BaseModel):
    email: EmailStr

class UpdatePasswordResquest(BaseModel):
    user_id: int
    new_password: str
    confirm_password: str
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value):
        if len(value) < 8:
            raise ValueError("Mật khẩu phải có độ dài ít nhất 8 ký tự")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValueError("Mật khẩu phải chứa it nhất 1 ký tự đặc biệt")
        if not re.search(r'[0-9]', value):
            raise ValueError("Mật khẩu phải chứa ít nhất một số")
        if not re.search(r'[A-Z]', value):
            raise ValueError("Mật khẩu phải chứa ít nhất một chữ cái viết hoa")
        return value