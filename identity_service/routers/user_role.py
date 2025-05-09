from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from models import UserRole, Role
from auth_per import get_current_user
from databases import db_dependency
from schemas import UserRoleRequest, AssignRoleRequest
from connect_service import get_user, log_user_action
from verify_api_key import verify_api_key
from service.redis_client import redis_clients, get_user_role_from_cache, set_user_role_in_cache
router = APIRouter(prefix="/api/identity_service",tags=["user-role"])
# API: Lấy thong tin user 
@router.get("/user-roles/{user_id}", status_code=status.HTTP_200_OK)
async def read_user_roles(user_id: int, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể truy xuất vai trò của người dùng."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    # Kiểm tra cache
    user_roles = get_user_role_from_cache(user_id)
    if user_roles:
        return {"detail": "Vai trò người dùng đã được truy xuất thành công từ cache", "user_roles": user_roles}
    # Lấy danh sách user_roles của user_id từ Identity Service
    try:
        user_roles = get_user(user_id)
        user = user_roles.get('user')
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Không thể lấy thông tin người dùng từ User Service")
    if not user_roles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy vai trò người dùng cho người dùng này")
    # Lấy danh sách tất cả các role
    existing_role = db.query(UserRole).filter(UserRole.user_id == user['id'], UserRole.role_id == Role.id).first()
    set_user_role_in_cache(user['id'], user_roles)
    log_user_action(current_user["user_id"], f"{current_user["username"]}: Đã truy xuất vai trò của người dùng {user["id"]}")
    return {
        "detail": "Vai trò người dùng đã được truy xuất thành công",
        "user_roles": user_roles,
        "role": existing_role,
    }
# API: Thêm mới một role cho một user
@router.post("/user-roles/create-user-role", status_code=status.HTTP_201_CREATED)
async def create_user_role(user_role_request: UserRoleRequest, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể thêm mới role cho người dùng."""
    # Kiểm tra quyền Admin
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền thêm mới vai trò cho người dùng")
    # Kiểm tra dữ liệu đầu vào
    if not user_role_request.user_id or not user_role_request.role_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID người dùng hoặc tên vai trò không hợp lệ")
    # Lấy thông tin user từ User Service
    try:
        user_response = get_user(user_role_request.user_id)
        if not user_response or "user" not in user_response:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Người dùng với ID: {user_role_request.user_id} không tồn tại!")
        user_info = user_response["user"] 
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Không thể lấy dữ liệu người dùng từ User Service: {str(e)}")
    # Tìm role_id dựa trên role_name
    role = db.query(Role).filter(Role.name == user_role_request.role_name).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vai trò '{user_role_request.role_name}' không tồn tại!")
    # Kiểm tra nếu user đã có role này
    existing_role = db.query(UserRole).filter(UserRole.user_id == user_info["id"], UserRole.role_id == role.id).first()
    if existing_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Người dùng ID {user_info['id']} đã có vai trò '{user_role_request.role_name}'")
    # Tạo bản ghi UserRole
    user_role = UserRole(user_id=user_info["id"], role_id=role.id)
    db.add(user_role)
    db.commit()
    db.refresh(user_role)
    # Xóa cache cũ để cập nhật lại
    cache_key = f"user_roles_{user_info['id']}"
    redis_clients.delete(cache_key)
    #Lưu lại cache mới
    set_user_role_in_cache(user_info["id"], user_role)
    # Ghi log hành động
    log_user_action(current_user["user_id"], f"{current_user['username']} đã thêm vai trò '{user_role_request.role_name}' cho người dùng ID {user_info['id']}")
    return {
        "detail": "Người dùng đã được gán vai trò thành công!",
        "user_role": {
            "id": user_role.id,
            "user_id": user_role.user_id,
            "role_id": user_role.role_id,
            "role_name": role.name
        }
    }
# API: Cập nhật role của một user
@router.put("/user-roles/{user_id}/{role_name}", status_code=status.HTTP_200_OK)
async def update_user_role(user_role_request: UserRoleRequest, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể cập nhật role cho người dùng."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền thêm mới vai trò cho người dùng")
    current_role = db.query(Role).filter(Role.name == user_role_request.role_name).first()
    if not current_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vai trò hiện tại: '{user_role_request.role_name}' không tồn tại!")
    new_role = db.query(Role).filter(Role.name == user_role_request.role_name).first()
    if not new_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vai trò mới: '{user_role_request.role_name}' không tồn tại!")
    user_role = db.query(UserRole).filter(UserRole.user_id == user_role_request.user_id, UserRole.role_id == current_role.id).first()
    if not user_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Người dùng với ID: {user_role_request.user_id} không có vai trò '{user_role_request.role_name}'")
    #Cập nhật role mới
    user_role.role_id = new_role.id
    db.commit()
    db.refresh(user_role)
    # Xóa cache cũ và lưu lại cache mới
    cache_key = f"user_roles_{user_role.user_id}"
    redis_clients.delete(cache_key)
    set_user_role_in_cache(user_role.user_id, user_role)
    updated_role = db.query(Role).filter(Role.id == user_role.role_id).first()
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã cập nhật vai trò '{user_role_request.role_name}' của người dùng {user_role_request.user_id} thành '{updated_role.name}'")
    return {
        "detail": "Vai trò của người dùng đã cập nhật thành công",
        "user_role": {
            "user_id": user_role.user_id,
            "role_id": user_role.role_id,
            "role_name": updated_role.name  
        }
    }
# API: Xóa role của một user
@router.delete("/user-roles/{user_id}/{role_name}", status_code=status.HTTP_200_OK)
async def delete_user_role(user_role_request: UserRoleRequest, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể xóa role cho người dùng."""
    if current_user["role"]!= "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền xóa vai trò cho người dùng")
    # Tìm role_id từ role_name
    role = db.query(Role).filter(Role.name == user_role_request.role_name).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vai trò không tồn tại!")
    # Tìm và xóa bản ghi UserRole
    user_role = db.query(UserRole).filter(UserRole.user_id == user_role_request.user_id, UserRole.role_id == role.id).first()
    if not user_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vai trò của người không tồn tại!")
    db.delete(user_role)
    db.commit()
    # Xóa cache
    cache_key = f"user_roles_{user_role_request.user_id}"
    redis_clients.delete(cache_key)
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã xóa vai trò '{user_role_request.role_name}' của người dùng {user_role_request.user_id}")
    return {
        "detail": "Vai trò của người dùng đã được xóa thành công.",
        "user_id": user_role_request.user_id,
        "role_name": user_role_request.role_name
    }
# Gán role Admin mặc cho account admin
@router.post("/user-roles/assign-admin-role", status_code=status.HTTP_200_OK)
async def assign_admin_role(request: AssignRoleRequest, db: db_dependency,server_connection_key: str = Depends(verify_api_key)):
    """Dành cho hệ thống gọi nội bộ khi tạo user (vd: gán quyền admin ban đầu)."""
    role = db.query(Role).filter(Role.name == request.role_name).first()
    if not role:
        role = Role(
            name=request.role_name,
            description="Vai trò quản trị viên hệ thống",
            created_at=datetime.utcnow(),
        )
        db.add(role)
        db.commit()
        db.refresh(role)
        print(f"Vai trò 'Admin' đã được tạo với ID: {role.id}")
    # Kiểm tra xem người dùng đã có vai trò này chưa
    user_role = db.query(UserRole).filter(UserRole.user_id == request.user_id, UserRole.role_id == role.id).first()
    if user_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Người dùng đã có vai trò này!")
    # Tạo bản ghi UserRole
    user_role = UserRole(user_id=request.user_id, role_id=role.id)
    db.add(user_role)
    db.commit()
    db.refresh(user_role)
    # Xóa cache cũ và lưu lại cache mới
    cache_key = f"user_roles_{request.user_id}"
    redis_clients.delete(cache_key)
    set_user_role_in_cache(request.user_id, user_role)
    return {
        "detail": "Gán Role thành công!",
        "user_role": {
            "user_id": user_role.user_id,
            "role_name": role.name
        }
    }