from fastapi import APIRouter, Depends, HTTPException, status
from databases import db_dependency
from sqlalchemy import func
from models import Log, Users
from user_schemas import LogResponse
from connect_service import validate_token_user
from verify_api_key import verify_api_key
from dotenv import load_dotenv
import os
router = APIRouter(prefix="/api/user_service",tags=["logs"])
load_dotenv()
API_KEY = os.getenv("API_KEY")
@router.get("/logs", status_code=status.HTTP_200_OK)
async def get_logs(db: db_dependency, current_user: dict = Depends(validate_token_user)):
    """Lấy danh sách tất cả các bản ghi đã thêm vào hệ thống."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này!!!")
    list_logs = db.query(Log).order_by(Log.id).all()
    list_log_reponse = [LogResponse.from_orm(log) for log in list_logs]
    return {
        "detail": "Tất cả các bản ghi đã được truy xuất thành công",
        "logs": list_log_reponse
    }
@router.get("/user/{user_id}/logs", status_code=status.HTTP_200_OK)
async def get_user_logs(user_id: int, db: db_dependency, current_user: dict =Depends(validate_token_user)):
    """Lấy danh sách tất cả các bản ghi đã thêm vào hệ thống của người dùng với ID truyền vào."""
    if current_user["role"] != "Admin" and current_user["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này!!!")
    if not db.query(Log).filter(Log.user_id == user_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!!!")
    list_logs = db.query(Log).filter(Log.user_id == user_id).order_by(Log.id).all()
    list_log_reponse = [LogResponse.from_orm(log) for log in list_logs]
    return {
        "detail": "Nhật ký người dùng đã được lấy thành công",
        "logs": list_log_reponse
    }
@router.post('/create-log', status_code=status.HTTP_201_CREATED)
async def create_log(user_id: str, action: str, db: db_dependency, server_connection_key: str = Depends(verify_api_key)):
    """Thêm một bản ghi vào hệ thống với ID người dùng và hành động."""
    user_exists = db.query(Users).filter(Users.id == user_id).first()
    if not user_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Người dùng không hợp lệ!!!")
    new_log = Log(user_id=user_id, action=action, timestamp=func.now())
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return {
        "detail": "Hành động của người dùng đã được ghi lại thành công", 
    }
