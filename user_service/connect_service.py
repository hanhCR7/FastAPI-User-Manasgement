import httpx
import asyncio
import os
from dotenv import load_dotenv
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
load_dotenv()
token_url = os.getenv("LOGIN")
IDENTITY_URL = os.getenv("IDENTITY_SERVICE_URL")
EMAIL_URL = os.getenv("EMAIL_SERVICE_URL")
SERVICE_KEY = os.getenv("SERVICE_KEY")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{token_url}")
async def validate_token_user(token: str = Depends(oauth2_scheme)):
    headers = {
        "Authorization": f"Bearer {token}",
    }
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(
                f"{IDENTITY_URL}validate-token",
                headers=headers,
            ) 
            if response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không tồn tại!!!")
            try:
                data = response.json()
            except ValueError:
                raise HTTPException(status_code=500, detail="Phản hồi JSON không hợp lệ từ dịch vụ xác thực mã thông báo!!!")
            return {
                "user_id": data["user_id"],
                "username": data["username"],
                "role": data["role"],
            }
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi yêu cầu đến dịch vụ xác thực: {repr(e)}")
# gán role cho admin
async def assign_admin_role_to_user(user_id: int):
    """Gán quyền Admin cho người dùng"""
    headers = {
        "X-API-Key": SERVICE_KEY
    }
    data = {
        "user_id": user_id,
        "role_name": "Admin"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{IDENTITY_URL}user-roles/assign-admin-role", 
                json=data, 
                headers=headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Gán quyền Admin không thành công")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi yêu cầu đến dịch vụ xác thực: {repr(e)}")
#Gửi mail thông báo cho user bị khóa do không login quá 15 ngày
async def send_user_lock_notification(recipient: str, username: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{EMAIL_URL}send-user-lock-notification/",
                json={"recipient": recipient, "username": username}
            )
            if response.status_code == 200:
                return response.json()
        except httpx.ReadError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gửi mail thông báo: {repr(e)}")

    