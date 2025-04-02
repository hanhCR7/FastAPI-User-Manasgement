import uuid
import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from databases import get_db
from schemas import EmailRequest, ActivationEmailRequest, PasswordResetEmail, UserLockNotification
from service.email_service import send_email

load_dotenv()
router = APIRouter(prefix="/api/email_service",tags=["emails"])
ACTIVATE_ACCOUNT_URL = os.getenv("ACTIVATE_ACCOUNT_URL")
SEND_EMAIL = os.getenv("EMAIL_URL")
@router.post("/send-email/", status_code=status.HTTP_200_OK)
async def send_email_api(email_request: EmailRequest, db: Session = Depends(get_db)):
    await send_email(db, email_request.recipient, email_request.subject, email_request.body)
    return {"message": "Email gửi thành công"}
# Gửi email xác thực tài khoản người dùng đã đăng ký
@router.post("/send-activation-email/", status_code=status.HTTP_200_OK)
async def send_activation_email_api(request: ActivationEmailRequest, db: Session = Depends(get_db)):
   """API gui email xac thuc tai khoan."""
   activation_link = f"{ACTIVATE_ACCOUNT_URL}?token={request.activation_token }"
   email_body = f"""
    <h2>Xác thực tài khoản</h2>
    <p>Nhấn vào link dưới đây để kích hoạt tài khoản của bạn:</p>
    <a href="{activation_link}">{activation_link}</a>
    """
   await send_email(db, request.recipient, "Xác thực tài khoản", email_body)
   return {
       "status": "success",
       "message": "Email gửi thành công"
    }
# Gửi email đặt lại mật khẩu
@router.post("/send-password-reset-email/", status_code=status.HTTP_200_OK)
async def send_password_reset_email_api(request: PasswordResetEmail, db: Session = Depends(get_db)):
    """API gui email dat lai mat khau."""
    email_body = f"""
    <h2>Đặt lại mật khẩu</h2>
    <p>Nhấn vào link dưới đây để đặt lại mật khẩu của bạn:</p>
    <a href="{request.reset_link}">{request.reset_link}</a>
    """
    await send_email(db, request.email, "Đặt lại mật khẩu", email_body)
    return {
        "status": "success",
        "message": "Email gửi thành công"
    }
# Gửi mail khi thấy user không đăng nhập lại quá lâu
@router.post("/send-user-lock-notification/", status_code=status.HTTP_200_OK)
async def send_user_lock_notification_api(request: UserLockNotification, db: Session = Depends(get_db)):
    """"API gửi mail khi thấy user không đăng nhập lại quá lâu"""
    email_body = f"""
    <h2>Thông báo tài khoản bị khóa</h2>
    <p>Chào {request.username}! Tài khoản của bạn đã khóa do đã quá lâu bạn không Login.</p>
    <p>Vui lòng liên hệ Admin đễ được xác nhận thông qua đưowng link dưới đây:</p>
    <a href="{SEND_EMAIL}">{SEND_EMAIL}</a>
    """
    await send_email(db, request.recipient, "Thông báo tài khoản bị khóa", email_body)
    return {
        "status": "success",
        "message": "Email gửi thành công"
    }