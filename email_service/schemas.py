from pydantic import BaseModel, EmailStr

class EmailRequest(BaseModel):
    recipient: EmailStr
    subject: str
    body: str

class EmailResponse(BaseModel):
    status: str
    message: str

class ActivationEmailRequest(BaseModel):
    user_id: int
    recipient: EmailStr
    activation_token: str
class OTPRequest(BaseModel):
    user_id: int
    email: EmailStr
class VerifyOTPRequest(BaseModel):
    user_id: int
    otp: str
class PasswordResetEmail(BaseModel):
    email: EmailStr
    reset_link: str

class UserLockNotification(BaseModel):
    recipient: EmailStr
    username: str