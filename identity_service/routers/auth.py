import os
import asyncio
import uuid
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from schemas import SignUp, Login, ChangePassword, VerifyOTP, ResetPasswordRequest, ResetPasswordToken
from models import Role, UserRole, PasswordResetToken, OTPAttempts
from databases import get_db
from auth_per import get_current_user
from connect_service import (
    get_user, get_user_with_password, log_user_action, sign_up_user, 
    update_last_login, update_password, active_account, generate_activation_token, 
    send_email_otp, validate_otp, send_reset_password_email, get_user_by_email,
    reset_update_password, send_user_lock_notification
)
from service.redis_client import redis_clients, cache_user, get_cached_user
from rate_limiter import rate_limiters
router = APIRouter(prefix="/api/identity_service",tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/identity_service/login")
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
RESET_PASSWORD_URL = os.getenv("RESET_PASSWORD_URL")
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_OTP_ATTEMPTS = 5 
BLOCK_TIME = timedelta(minutes=5) 

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
def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        if not user_id or not username or not role:
            print("Lỗi")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token không hợp lệ.")
        return {"sub": user_id, "username": username, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token đã hết hạn.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Refresh token không hợp lệ.")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {e}")

@router.post("/login", status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limiters(redis_clients, "login"))])
async def login(login: Login, request: Request):
    """Trang đăng nhập
    Khi đăng nhập user sẽ được nhận một mã OTP qua email để xác minh
    """  
    # Lấy địa chỉ IP của người dùng
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    print(f"Địa chỉ IP của người dùng: {client_ip}")
    user_response = await get_user_with_password(login.username, login.password)
    print(f"User response: {user_response}")
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
    user_data = get_cached_user(user_id)
    if not user_data:
        user_data = await get_user(user_id)
        cache_user(user_id, user_data)
    otp_response = await send_email_otp(user_response["user_id"], user_response["email"])
    if not otp_response or otp_response.get("status") != "success":
        raise HTTPException(status_code=500, detail="Không thể gửi mã OTP. Vui lòng thử lại sau.")
    return{
        "message": "Mã OTP đã được gửi đến email của bạn. Vui lòng kiểm tra và nhập OTP để đăng nhập.",
    }
@router.post("/validate-otp", status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limiters(redis_clients, "validate_otp"))])
async def verify_otp(request: VerifyOTP, db: Session = Depends(get_db)):
    """Xác thực OTP"""
    redis_key = f"otp_attempts:{request.user_id}"
    attempts = int(redis_clients.get(redis_key) or 0)
    if attempts >= MAX_OTP_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Bạn nhập sai OTP quá nhiều lần. Hãy thử lại sau 5 phút!")
    otp_response = await validate_otp(request.user_id, request.otp)
    if not otp_response or otp_response.get("status") != "success":
        redis_clients.setex(redis_key, int(BLOCK_TIME.total_seconds()), attempts + 1)
        raise HTTPException(status_code=400, detail="Mã OTP không hợp lệ hoặc hết hạn.")
    redis_clients.delete(redis_key)
    user_response = await get_user(request.user_id)
    user_data = user_response.get("user")
    role = db.query(UserRole).filter(UserRole.user_id == request.user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="Tài khoản không tồn tại.")
    cache_user(request.user_id, user_data)
    access_token = create_access_token(data={"sub": str(request.user_id), "role": role.role.name, "username": user_data.get("username")})
    refresh_token = create_access_token(data={"sub": str(request.user_id), "role": role.role.name, "username": user_data.get("username")}, expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    redis_clients.setex(f"refresh_token:{request.user_id}", timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), refresh_token)
    await log_user_action(request.user_id, f"{user_data.get('username')} đã đăng nhập thành công!")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer", 
        "username": user_data.get("username")
    }
@router.post("/sign_up", status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limiters(redis_clients, "sign_up"))])
async def sign_up(sign_up: SignUp, db: Session = Depends(get_db)):
    """Trang đăng ký"""
    user_response = await sign_up_user(
        sign_up.first_name, sign_up.last_name, sign_up.username, sign_up.email, sign_up.password
    )
    print("User response:", user_response)
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
        raise HTTPException(status_code=500, detail="Lỗi kích hoạt tài khoản")
    await log_user_action(user_id, f"{sign_up.username} đã đăng ký thành công!")
    return {
        "message": "Người dùng đã đăng ký thành công! Email kích hoạt đã được gửi.", 
        "user_id": user_response["user"]["id"],
        "username": sign_up.username,
        "email": sign_up.email
    }
@router.put("/change-password", status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limiters(redis_clients, "change_password"))])
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
async def logout(token: str = Depends(oauth2_scheme), current_user: dict = Depends(get_current_user)):
    """Trang đăng xuất"""
    decoded_token = decode_token(token)  
    if not decoded_token:
        raise HTTPException(status_code=400, detail="Token không hợp lệ hoặc đã hết hạn.")
    expire_time = decoded_token.get("exp") - datetime.utcnow().timestamp()
    if expire_time > 0:
        redis_clients.setex(f"blacklist:{token}", int(expire_time), "blacklisted")
    await log_user_action(current_user["user_id"], f"{current_user['username']} đã đăng xuất thành công!")
    return {
        "detail": "Đăng xuất thành công!"
    }

@router.get("/validate-token", status_code=status.HTTP_200_OK)
async def validate_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Trang kiểm tra token"""
    if redis_clients.exists(f"blacklist:{token}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token đã bị thu hồi")
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
# Refresh Token
@router.post("/refresh-token", status_code=status.HTTP_200_OK)
async def refresh_token(response: Response, refresh_token: str):
    """Tạo mới access token bằng refresh token"""
    user_response = verify_refresh_token(refresh_token)
    if not user_response:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token không hợp lệ hoặc đã hết hạn.")
    user_id = user_response.get("sub")
    username = user_response.get("username")
    role = user_response.get("role")
    stored_token = redis_clients.get(f"refresh_token:{user_id}")
    if stored_token != refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token đã bị thu hồi.")
    new_access_token = create_access_token({"sub": user_id, "username":username, "role":role}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    new_refresh_token = create_access_token({"sub": user_id, "username":username, "role":role}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    redis_clients.setex(f"refresh_token:{user_id}", timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), new_refresh_token)
    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, secure=True, samesite="Lax")
    return {"access_token": new_access_token, "token_type": "bearer"}
# Quên mật khẩu
@router.post("/reset-password-request", status_code=status.HTTP_200_OK,  dependencies=[Depends(rate_limiters(redis_clients, "reset_password_request"))])
async def reset_password_request(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Trang yêu cầu quên mật khẩu"""
    user_response = await get_user_by_email(request.email)
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
        "message": "Mật khẩu đã được đặt lại thành công. Hãy quay lại trong login tiếp tục!"
    }