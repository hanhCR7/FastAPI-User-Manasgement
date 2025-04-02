from datetime import datetime
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException
from dotenv import load_dotenv
import os
import httpx
USER_SERVICE_URL = os.getenv('USER_SERVICE_URL')
EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_URL')
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/identity_service/login")
load_dotenv()
SERVICE_KEY = os.getenv('SERVICE_KEY')

def hash_password( password: str) -> str:
    return bcrypt_context.hash(password)
def verify_password( plain_password: str, hashed_password: str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)
# Lấy thông tin user từ User Service
async def get_user(user_id: int):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f'{USER_SERVICE_URL}user/{user_id}')
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi nạp user: {repr(e)}")
# Xác thực user
async def get_user_with_password(username: str, password: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f'{USER_SERVICE_URL}authenticate',
                json={'username': username, 'password': password}
            )
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi nạp user: {repr(e)}")
# Cập nhật password
async def update_password(user_id: int, old_password: str, new_password_hash: str, token: str = Depends(oauth2_scheme)):
    headers = {"Authentication": f"Bearer {token}"}
    payload = {
        "old_password": old_password,
        "new_password": new_password_hash,
        "confirm_password": new_password_hash
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f'{USER_SERVICE_URL}users/update-password/{user_id}', 
                headers=headers, 
                json=payload
            )
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi nạp user: {repr(e)}")
# Đăng ký user(lấy từ create_user của User Service)
async def sign_up_user(first_name: str, last_name: str, username: str, email: str, password_hash: str):
    headers = {"X-API-Key": SERVICE_KEY}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f'{USER_SERVICE_URL}user/create-user',
                headers=headers,
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "email": email,
                    "password_hash": password_hash
                }
            )
            if response.status_code == 201:
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi nạp user: {repr(e)}")
# Cập nhật last_login
async def update_last_login(user_id: int):
    headers = {"X-API-Key": SERVICE_KEY}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f'{USER_SERVICE_URL}user/update_last_login/{user_id}',
                headers=headers,
                json={"last_login": datetime.utcnow().isoformat()}
            )
            if response.status_code == 200:
                return response.json()
            raise Exception(f"Request error: {response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi nạp user: {repr(e)}")
# Tạo log
async def log_user_action(user_id: int, action: str):
    headers = {"X-API-Key": SERVICE_KEY}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f'{USER_SERVICE_URL}create-log',
                headers=headers,
                params={"user_id": user_id, "action": action}
            )
            if response.status_code == 201:
                return response.json()
            raise Exception(f"Request error: {response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi tạo log: {repr(e)}")
#Kích hoạt account
async def generate_activation_token(user_id: int):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f'{USER_SERVICE_URL}generate-activation-token', json={"user_id": user_id})
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi tạo activation token: {repr(e)}")
# COnnect to email service
async def active_account(user_id: int, email: str, activation_token: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f'{EMAIL_SERVICE_URL}send-activation-email/',
                json={"user_id": user_id, "recipient": email, "activation_token": activation_token}
            )
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            print(f"Loi connect: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi mail thông báo: {repr(e)}")
#Gửi mail khi user.is_active == False
async def send_user_lock_notification(recipient: str, username: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f'{EMAIL_SERVICE_URL}send-user-lock-notification/',
                json={"recipient": recipient, "username": username}
            )
            if response.status_code == 200:
                return response.json()
        except httpx.ReadError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi mail thông báo: {repr(e)}")
# Send Email OTP
async def send_email_otp(user_id: int, email: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f'{EMAIL_SERVICE_URL}send-otp-email/',
                json={"user_id": user_id, "email": email}
            )
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi mail thông báo: {repr(e)}")
# Validate OTP
async def validate_otp(user_id: int, otp: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f'{EMAIL_SERVICE_URL}validate-otp/',
                json={"user_id": user_id, "otp": otp}
            )
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi mail thông báo: {repr(e)}")
#Email đặt lại mật khẩu
async def send_reset_password_email(email: str, reset_link: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f'{EMAIL_SERVICE_URL}send-password-reset-email/',
                json={"email": email, "reset_link": reset_link}
            )
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi mail thông báo: {repr(e)}")
# Lấy thông tin user qua email
async def get_user_by_email(email: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f'{USER_SERVICE_URL}users/get-user-by-email/{email}')
            if response.status_code == 200:
                return response.json()
            raise Exception(f"Request error: {response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi mail thông báo: {repr(e)}")
# Cập nhật mật khẩu từ user service
async def reset_update_password(user_id: int, new_password: str, confirm_password: str):

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f'{USER_SERVICE_URL}update-password/',
                json={
                    "user_id": user_id,
                    "new_password": new_password,
                    "confirm_password": confirm_password
                }
            )
            if response.status_code == 200:
                return response.json()
            raise Exception(f"Request error: {response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi mail thông báo: {repr(e)}")