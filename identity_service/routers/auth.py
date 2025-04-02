import os
import asyncio
import uuid
from dotenv import load_dotenv
from jose import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from schemas import SignUp, ChangePassword, VerifyOTP, ResetPasswordRequest, ResetPasswordToken
from models import Role, UserRole, BackListTokens, PasswordResetToken
from databases import get_db
from auth_per import get_current_user
from connect_service import (
    get_user, get_user_with_password, log_user_action, sign_up_user, 
    update_last_login, update_password, active_account, generate_activation_token, 
    send_email_otp, validate_otp, send_reset_password_email, get_user_by_email,
    reset_update_password, send_user_lock_notification
)
router = APIRouter(prefix="/api/identity_service",tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/identity_service/login")
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
RESET_PASSWORD_URL = os.getenv("RESET_PASSWORD_URL")
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    to_encode["sub"] = str(to_encode.get("sub", ""))
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "role": data.get("role", "User")})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")
@router.post("/login", status_code=status.HTTP_200_OK)
async def login(login: OAuth2PasswordRequestForm = Depends()):
    """Trang đăng nhập
    Khi đăng nhập user sẽ được nhận một mã OTP qua email để xác minh
    """
    user_response = await get_user_with_password(login.username, login.password)
    if not user_response:
        raise HTTPException(status_code=404, detail="Tài khoản hoặc mật khẩu không đúng.")
    user_id = user_response.get('user_id')
    username = user_response.get('username')
    is_active = user_response.get("is_active")
    if not user_id:
        raise HTTPException(status_code=500, detail="Lỗi xác thực!!")
    if is_active != True:
        await send_user_lock_notification(user_response["email"], username)
        raise HTTPException(status_code=401, detail="Tài khoản của bạn bị vô hiệu hóa hoặc bạn chưa kích hoạt tài khoản thông email đã gửi. Vui lòng liên hệ Admin để mở lại tài khoản.")
    otp_response = await send_email_otp(user_response["user_id"], user_response["email"])
    if not otp_response or otp_response.get("status") != "success":
        raise HTTPException(status_code=500, detail="Không thể gửi mã OTP. Vui lòng thử lại sau.")
    return{
        "message": "Mã OTP đã được gửi đến email của bạn. Vui lòng kiểm tra và nhập OTP để đăng nhập.",
    }
@router.post("/validate-otp", status_code=status.HTTP_200_OK)
async def verify_otp(request: VerifyOTP, db: Session = Depends(get_db)):
    """Xác thực OTP"""
    if not request.user_id or not request.otp:
        raise HTTPException(status_code=400, detail="Thiếu thông tin xác thực.")
    otp_response = await validate_otp(request.user_id, request.otp)
    if not otp_response or otp_response.get("status") != "success":
        raise HTTPException(status_code=400, detail="Mã OTP không hợp lệ hoặc đã hết hạn.")
    user_id_response = request.user_id
    user_response = await get_user(user_id_response)
    # Kiểm tra user_response
    user_data = user_response.get("user") if user_response else None
    if not user_data:
        raise HTTPException(status_code=404, detail="Tài khoản không tồn tại.")
    user_id = user_data.get("id")
    username = user_data.get("username")
    if not user_id:
        raise HTTPException(status_code=500, detail="Lỗi hệ thống: user_id không hợp lệ.")
    # Kiểm tra role của user
    role = db.query(Role).join(UserRole, Role.id == UserRole.role_id).filter(UserRole.user_id == user_id).first()
    if role:
        role_user = role.name
    else:
        default_role = db.query(Role).filter(Role.name == "User").first()
        if not default_role:
            raise HTTPException(status_code=500, detail="Vai trò mặc định không tồn tại!") 
        new_user_role = UserRole(user_id=user_id, role_id=default_role.id)
        db.add(new_user_role)
        db.commit()
        role_user = default_role.name
    # Kiểm tra user_id trước khi cập nhật
    if not await update_last_login(user_id):
        raise HTTPException(status_code=500, detail="Không cập nhật được lần đăng nhập cuối cùng")
    # Tạo access token
    access_token = create_access_token(data={"sub": str(user_id), "role": role_user, "username": username})
    await log_user_action(user_id, f"{username} đã đăng nhập thành công!")
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "username": username
    }

@router.post("/sign_up", status_code=status.HTTP_201_CREATED)
async def sign_up(sign_up: SignUp, db: Session = Depends(get_db)):
    """Trang đăng ký"""
    user_response = await sign_up_user(
        sign_up.first_name, sign_up.last_name, sign_up.username, sign_up.email, sign_up.password
    )
    if not user_response or "user" not in user_response or "id" not in user_response["user"]:
        raise HTTPException(status_code=500, detail="Lỗi: Không lấy được user_id từ User Service")
    role = db.query(Role).filter(Role.name == "User").first()
    user_id = user_response["user"]["id"]
    db.add(UserRole(user_id=user_id, role_id=role.id))
    db.commit()
    activation_response = await generate_activation_token(user_id)
    if not activation_response or "activation_token" not in activation_response:
        raise HTTPException(status_code=500, detail="Lỗi tạo token kích hoạt")
    activation_token = activation_response["activation_token"]
    email_response = await active_account(user_id,sign_up.email, activation_token)
    if not email_response or email_response.get("status") != "success":
        print(email_response)
        raise HTTPException(status_code=500, detail="Lỗi kích hoạt tài khoản")
    await log_user_action(user_id, f"{sign_up.username} đã đăng ký thành công!")
   
    return {
        "message": "Người dùng đã đăng ký thành công! Email kích hoạt đã được gửi.", 
        "user_id": user_response["user"]["id"],
        "username": sign_up.username,
        "email": sign_up.email
    }
@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password(request: ChangePassword, current_user: dict = Depends(get_current_user)):
    """Trang đổi mật khẩu"""
    username = current_user["username"]
    user_response = await get_user_with_password(username, request.old_password)
    if not user_response:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại!")
    user_id = user_response["user_id"]
    token = current_user["token"]
    try:
        await update_password(user_id, request.old_password, request.new_password, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Lỗi cập nhật mật khẩu")
    await log_user_action(user_id, f"{username} đã đổi mật khẩu thành công!")
    return {
        "message": "Đổi mật khẩu thành công"
    }
@router.post('/logout', status_code=status.HTTP_200_OK)
async def logout(token: str = Depends(oauth2_scheme), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Trang đăng xuất"""
    db.add(BackListTokens(token=token))
    db.commit()
    await log_user_action(current_user["user_id"], f"{current_user['username']} đã đăng xuất thành công!")
    return {
        "detail": "Đăng xuất thành công!"
    }

@router.get("/validate-token", status_code=status.HTTP_200_OK)
async def validate_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Trang kiểm tra token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        role: str = payload.get("role")
        username: str = payload.get("username")
        if not user_id or not role or not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token payload không hợp lệ")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token đã hết hạn!")
    except jwt.JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không đúng")
    # Lấy user từ User Service
    user_response = await get_user(user_id)
    if not user_response or "user" not in user_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!")
    user_data = user_response['user']  # Lấy thông tin người dùng từ 'user'
    return {
        "user_id": user_data["id"],
        "username": user_data["username"],
        "role": role
    }  
# Quên mật khẩu
@router.post("/reset-password-request", status_code=status.HTTP_200_OK)
async def reset_password_request(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Trang yêu cầu quên mật khẩu"""
    user_response = await get_user_by_email(request.email)
    print(user_response)
    if not user_response or "id" not in user_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại")
    user_id = user_response["id"]
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    
    db_token = PasswordResetToken(
        user_id=user_id,
        token=token,
        created_at=datetime.utcnow(),
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()

    reset_link = f"{os.getenv('RESET_PASSWORD_URL')}?token={token}"
    email_response = await send_reset_password_email(request.email, reset_link)

    if not email_response or email_response.get("status") != "success":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể gửi email đặt lại mật khẩu")

    return {"message": "Email đặt lại mật khẩu đã được gửi đến địa chỉ email của bạn."}
# APi đặt lại password
@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(resquest: ResetPasswordToken, db: Session = Depends(get_db)):
    """Trang đặt lại mật khẩu"""
    if not resquest.token or not resquest.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu thông tin xác thực.")
    token_response = db.query(PasswordResetToken).filter(PasswordResetToken.token == resquest.token).first()
    if not token_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token không tồn tại hoặc đã hết hạn.")
    if datetime.utcnow() > token_response.expires_at:
        db.delete(token_response)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token đã hết hạn.")
    user_id = token_response.user_id
    new_password = resquest.new_password
    confirm_password = resquest.confirm_password
    if new_password != confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mật khẩu xác nhận không khớp.")
    try:
        await reset_update_password(user_id, new_password, confirm_password)
        db.delete(token_response)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lỗi cập nhật mật khẩu")
    await log_user_action(user_id, f"{user_id} đã đặt lại mật khẩu thành công!")
    return {
        "message": "Mật khẩu đã được đặt lại thành công."
    }