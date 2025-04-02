import httpx
import asyncio
import os
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
load_dotenv()
token_url = os.getenv("LOGIN")
IDENTITY_URL = os.getenv("IDENTITY_SERVICE_URL")
EMAIL_URL = os.getenv("EMAIL_SERVICE_URL")
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
            raise HTTPException(status_code=500, detail=f"Lỗi khi tìm nạp người dùng: {repr(e)}")
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

    