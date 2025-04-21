import asyncio
import io
import os
import uuid
import pandas as pd
from pytz import UTC
from dotenv import load_dotenv
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from db_config import db_dependency
from models import Users, UserStatus, Log
from connect_service import validate_token_user, send_user_lock_notification
from routers.logs import create_log
from verify_api_key import verify_api_key
from security import hash_password, verify_password
from user_schemas import (
    CreateUserRequest, UpdateUserRequest, UserResponse, 
    UserStatus, UpdatePassword, AuthRequest, ListUserActive, 
    EditUserActive, ActivationTokenRequest, EmailResquest,
    UpdatePasswordResquest
)
router = APIRouter(prefix="/api/user_service",tags=["users"])
load_dotenv()
API_KEY = os.getenv("API_KEY")
@router.get("/user/all-user", status_code=status.HTTP_200_OK)
async def get_all_user(db: db_dependency, current_user: dict = Depends(validate_token_user)):
    """Chỉ có Admin mới có thể xem tất cả các User."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    user_id = current_user["user_id"]
    list_user = db.query(Users).order_by(Users.id).all()
    user_list_response = [UserResponse.from_orm(user) for user in list_user]
    await create_log(user_id, "Đã xem danh sách người dùng.",db)
    return {
        "details": "List user",
        "users": user_list_response
    }
@router.get("/user/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_by_id(user_id: int, db: db_dependency):
    """Lấy thông tin của user theo ID."""
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!!!")
    return {
        "details": "User by ID",
        "user": UserResponse.from_orm(user)
    }
@router.post('/authenticate', status_code=status.HTTP_200_OK)
async def authenticate_user(data: AuthRequest,db: db_dependency):
    """Xác thực tài khoản người dùng."""
    user = db.query(Users).filter(Users.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sai tài khoản hoặc mật khẩu. Vui lòng kiểm tra lại!!!")
    return {
        "user_id": user.id, 
        "username": user.username,
        "email": user.email,
        "status": user.status, 
        "is_active": user.is_active
    }
@router.post('/user/create-user', status_code=status.HTTP_201_CREATED)
async def create_user(create_user: CreateUserRequest, db: db_dependency,server_connection_key: str = Depends(verify_api_key)):   
    """Tạo mới User. Chỉ có Admin or User có quyền mới tạo được!"""
    if db.query(Users).filter(Users.username == create_user.username).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tên người dùng đã tồn tại!!!")
    if db.query(Users).filter(Users.email == create_user.email).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email của người dùng đã tồn tại!!!")
    create_user_model = Users(
        first_name=create_user.first_name,
        last_name=create_user.last_name,
        username=create_user.username,
        email=create_user.email,
        password_hash=hash_password(create_user.password_hash),
        is_active=False,
        status=UserStatus.Inactive,
    )
    db.add(create_user_model)
    db.commit()
    db.refresh(create_user_model)
    return {
        "details": "Tạo người dùng mới thành công!",
        "user": UserResponse.from_orm(create_user_model)
    }
@router.put("/user/{user_id}", status_code=status.HTTP_200_OK)
async def update_user(user_id: int, update_user: UpdateUserRequest, db: db_dependency, current_user: dict = Depends(validate_token_user)):
    """Cập nhật thông tin của User theo ID. Chỉ có Admin hoặc User đang đăng nhập mới có thể cập nhật."""
    if current_user["role"] != "Admin" and current_user["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này!!!")
    user_ids = current_user["user_id"]
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!!!")
    if db.query(Users).filter(Users.username == update_user.username, Users.id != user_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tên người dùng đã tồn tại!!!")
    if db.query(Users).filter(Users.email == update_user.email, Users.id != user_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email người dùng đã tồn tại!!!")
    user.first_name = update_user.first_name
    user.last_name = update_user.last_name
    user.username = update_user.username
    user.email = update_user.email
    if update_user.password_hash:
        user.password_hash = hash_password(update_user.password_hash)
    user.status = update_user.status
    db.commit()
    db.refresh(user)
    await create_log(user_ids, f"Đã cập nhật người dùng: {user_id} thành công.",db)
    return {
        "details": "Cập nhật người dùng thành công!",
        "user": UserResponse.from_orm(user)
    }
@router.put("/user/update-password/{user_id}")
async def update_password(user_id: int, request: UpdatePassword, db: db_dependency, current_user: dict = Depends(validate_token_user)):
    """Cập nhật mật khẩu của User theo ID. Chỉ có Admin hoặc User đang đăng nhập mới có thể cập nhật."""
    if current_user["role"] != "Admin" and current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập vào tài nguyên này!!!")
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại!!!")
    if not verify_password(request.old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Mật khẩu hiện tại không đúng!!!")
    if request.new_password != request.confirm_new_password:
        raise HTTPException(status_code=400, detail="Mật khẩu mới và xác nhận mật khẩu mới phải giống nhau!!!")
    user.password_hash = hash_password(request.new_password)
    db.commit() 
    return {
        "details": "Mật khẩu được cập nhật thành công!"
    }
@router.put("/user/update_last_login/{user_id}", status_code=status.HTTP_200_OK)
async def update_time_last_login(user_id: int, db: db_dependency, server_connection_key = Depends(verify_api_key)):
    """Cập nhật lần đăng nhập cuối cùng của User theo ID."""
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!!!")
    user.last_login = datetime.utcnow().replace(tzinfo=UTC)
    db.commit()
    db.refresh(user)
    return {
        "details": "Lần đăng nhập cuối cùng đã được cập nhật thành công!"
    } 
@router.delete("/user/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: int, db: db_dependency, current_user: dict = Depends(validate_token_user)):
    """Xóa User theo ID. Chỉ có Admin hoặc User được phân quyền mới có thể xóa."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này!!!")
    user_ids = current_user["user_id"]
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!!!")
    db.query(Log).filter(Log.user_id == user_id).delete()
    db.commit()
    db.delete(user)
    db.commit()
    await create_log(user_ids, f"Đã xóa User: {user_id}.",db)
    return {
        "details": "Xóa User thành công!"
    }
@router.get("/export-list-users", status_code=status.HTTP_200_OK, response_class=StreamingResponse)
async def export_users(db: db_dependency, current_user: dict = Depends(validate_token_user)):
    """Export danh sách người dùng ra file Excel. Chỉ có Admin hoặc User được phân quyền mới thực hiện được chứa năng này."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này!!!")
    list_user = db.query(Users).order_by(Users.id).all()
    data = []
    for user in list_user:
        data.append({
            "ID": user.id,
            "Username": user.username,
            "Email": user.email,
            "First Name": user.first_name,
            "Last Name": user.last_name,
            "Status": user.status.value,
            "Created At": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "",
            "Updated At": user.updated_at.strftime("%Y-%m-%d %H:%M:%S") if user.updated_at else "",
            "Last Login": user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else ""
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="List Users", index=False)
    output.seek(0)
    header = {
        "Content-Disposition": "attachment; filename=list_users.xlsx",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    await create_log(current_user["user_id"], f"{current_user['username']} Đã xuất file danh sách người dùng.",db)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=header)
@router.get("/check-invalid-user", status_code=status.HTTP_200_OK)
async def check_invalid_user(db: db_dependency, current_user: dict = Depends(validate_token_user)):
    """Kiểm tra và đánh dấu người dùng không hoạt độngng trong 15 ngày. Chỉ có Admin hoặc User đuộc phân quyền mới thực hiện được chức năng này"""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    time_last_login = datetime.now() - timedelta(days=2)
    inactive_user = db.query(Users).filter(Users.last_login < time_last_login, Users.status != UserStatus.Inactive).all()
    if not inactive_user:
        return {
            "message": "Không tìm thấy người dùng không hoạt động."
        }
    email_task = []
    for user in inactive_user:
        user.status = UserStatus.Inactive
        user.is_active = False
        email_task.append(send_user_lock_notification(user.email, user.username))
    db.commit()
    await asyncio.gather(*email_task)
    await create_log(current_user["user_id"], f"{current_user['username']} Đã kiểm tra người dùng không hoạt động trong 15 ngày.",db)
    return {
        "message": f"Có {len(inactive_user)} người dùng không hoạt động được tìm thấy và đánh dấu là không hoạt động"
    }

@router.get("/users/list-active", status_code=status.HTTP_200_OK)
async def get_list_active_user(db: db_dependency, current_user: dict = Depends(validate_token_user)):
    """Lấy danh sách trạng thái người dùng. Chỉ có Admin hoặc User được phân quyền mới thực hiện được chức năng này."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này!!!")
    list_user = db.query(Users).order_by(Users.id).all()
    user_list_response = [ListUserActive.from_orm(user) for user in list_user]
    await create_log(current_user["user_id"], f"{current_user['username']} Đã xem danh sách người dùng hoạt động.",db)
    return {
        "details": "List user active",
        "users": user_list_response
    }
@router.put("/user/edit-active/{user_id}", status_code=status.HTTP_200_OK)
async def edit_active_user(user_id: int, db: db_dependency, current_user: dict = Depends(validate_token_user)):
    """Chỉ có Admin mới có thể chỉnh sửa trạng thái của User."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này!!!")
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!!!")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    await create_log(current_user["user_id"], f"{current_user['username']} Đã cập nhật trạng thái User thành công!", db)
    return {
        "details": "Cập nhật trạng thái người dùng thành công!",
        "user": EditUserActive.from_orm(user)
    }
@router.post("/generate-activation-token", status_code=status.HTTP_200_OK)
async def generate_activation_token(request: ActivationTokenRequest, db: db_dependency, server_connection_key: str = Depends(verify_api_key)):
    """Tạo token kích hoạt tài khoản người dùng."""
    user = db.query(Users).filter(Users.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!!!")
    activation_token = str(uuid.uuid4())
    user.activation_token = activation_token
    db.commit()
    db.refresh(user)
    return {
        "details": "Tạo token kích hoạt thành công!"
    }
@router.get("/activate", status_code=status.HTTP_200_OK)
async def activate_user(token: str, db: db_dependency):
    """Kích hoạt tài khoản người dùng."""
    user = db.query(Users).filter(Users.activation_token == token).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token không hợp lệ!!!")
    if user.activation_token_expiration < datetime.utcnow() + timedelta(seconds=30):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token đã hết hạn!!!")
    user.status = UserStatus.Active
    user.is_active = True
    user.activation_token = None
    db.commit()
    db.refresh(user)
    await create_log(user.id, f"{user.username}: Đã kích hoạt tài khoản thành công!", db)
    return {
        "details": "Kích hoạt tài khoản thành công!"
    }
@router.get("/users/get-user-by-email/{email}", status_code=status.HTTP_200_OK)
async def get_user_by_email(email:str, db: db_dependency, server_connection_key: str = Depends(verify_api_key)):
    """Lấy thông tin người dùng theo email."""
    user = db.query(Users).filter(Users.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!!!")
    return {
        "details": "User by email",
        "id": user.id,
        "email": user.email,
    }
# APi ĐẶt lai mật khẩu
@router.put("/update-password/", status_code=status.HTTP_200_OK)
async def update_password(request: UpdatePasswordResquest, db: db_dependency, server_connection_key: str = Depends(verify_api_key)):
    """Cập nhật mật khẩu người dùng"""
    user = db.query(Users).filter(Users.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại!!!")
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mật khẩu mới và xác nhận mật khẩu mới phải giống nhau!!!")
    user.password_hash = hash_password(request.new_password)
    db.commit()
    db.refresh(user)
    await create_log(user.id, f"{user.username}: Đã cập nhật mật khẩu thành công!", db)
    return {
        "details": "Cập nhật mật khẩu thành công!"
    }