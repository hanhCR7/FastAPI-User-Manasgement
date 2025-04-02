from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session
from models import BackListTokens
from databases import get_db
from connect_service import get_user
import os
from dotenv import load_dotenv
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/identity_service/login")
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = 'HS256'
async def get_current_user(token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):
    backListed = db.query(BackListTokens).filter(BackListTokens.token == token).first()
    if backListed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token đã bị thu hồi. Vui lòng đăng nhập lại.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        role: str = payload.get("role")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token đã hết hạn!!!")
    except jwt.JWTError as e: 
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ!!!")
    # Lấy user từ User Service
    user_response = await get_user(user_id)
    if not user_response or "user" not in user_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!!!")
    user_data = user_response['user'] 
    return {
        "user_id": user_data["id"],
        "username": user_data["username"],
        "role": role,
        "token": token
    }  