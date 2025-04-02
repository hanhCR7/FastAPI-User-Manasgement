from datetime import datetime
from pydantic import BaseModel, Field, ValidationInfo, field_validator, EmailStr
import re
class RoleRequest(BaseModel):
    name: str
    description: str = Field(max_length=255)
class RoleResponse(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    class Config:
        from_attributes  = True
class PermissionRequest(BaseModel):
    name: str
    description: str = Field(max_length=255)
class PermissionResponse(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    class Config:
        from_attributes  = True
class RolePermissionRequest(BaseModel):
    role_name: str
    permission_name: str
class RolePermissionResponse(BaseModel):
    role_id: int
    permission_id: int
    class Config:
        from_attributes  = True
class UserRoleRequest(BaseModel):
    user_id: int
    role_name: str
class UserRoleResponse(BaseModel):
    user_id: int
    role_id: int
    role_name: str
    class Config:
        from_attributes  = True
class Token(BaseModel):
    access_token: str
    token_type: str
class ChangePassword(BaseModel):
    old_password: str
    new_password: str 
    confirm_password: str 
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Mật khẩu phải có độ dài ít nhất 8 ký tự")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValueError("Mật khẩu phải chứa it nhất 1 ký tự đặc biệt")
        if not re.search(r'[0-9]', value):
            raise ValueError("Mật khẩu phải chứa ít nhất một số")
        if not re.search(r'[A-Z]', value):
            raise ValueError("Mật khẩu phải chứa ít nhất một chữ cái viết hoa")
        return value
    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value: str, info: ValidationInfo) -> str:
        new_password = info.data.get("new_password")
        if new_password and value != new_password:
            raise ValueError("Mật khẩu xác nhận không khớp với mật khẩu mới!")
        return value
class Login(BaseModel):
    username: str
    password: str
class SignUp(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    password: str
    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Mật khẩu phải có độ dài ít nhất 8 ký tự")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValueError("Mật khẩu phải chứa it nhất 1 ký tự đặc biệt")
        if not re.search(r'[0-9]', value):
            raise ValueError("Mật khẩu phải chứa ít nhất một số")
        if not re.search(r'[A-Z]', value):
            raise ValueError("Mật khẩu phải chứa ít nhất một chữ cái viết hoa")
        return value
class VerifyOTP(BaseModel):
    user_id: int
    otp: str
class ResetPasswordRequest(BaseModel):
    email: EmailStr
class ResetPasswordToken(BaseModel):
    token: str
    new_password: str
    confirm_password: str
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Mật khẩu phải có độ dài ít nhất 8 ký tự")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValueError("Mật khẩu phải chứa it nhất 1 ký tự đặc biệt")
        if not re.search(r'[0-9]', value):
            raise ValueError("Mật khẩu phải chứa ít nhất một số")
        if not re.search(r'[A-Z]', value):
            raise ValueError("Mật khẩu phải chứa ít nhất một chữ cái viết hoa")
        return value