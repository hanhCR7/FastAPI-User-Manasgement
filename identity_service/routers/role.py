from fastapi import APIRouter, HTTPException,  Depends, status
from models import Role
from auth_per import get_current_user
from databases import db_dependency
from schemas import RoleRequest, RoleResponse
from connect_service import log_user_action
router = APIRouter(prefix="/api/identity_service",tags=["role"])
@router.get("/roles", status_code=status.HTTP_200_OK)
async def read_roles(db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể xem danh sách vai trò."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    list_role = db.query(Role).all()
    role_list_response = [RoleResponse.from_orm(role) for role in list_role]
    log_user_action(current_user["user_id"], f"{current_user["username"]}: Đã xem danh sách vai trò!")
    return {
        "details": "Danh sách vai trò: ",
        "roles": role_list_response
    }
@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(role_request: RoleRequest, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể tạo vai trò."""
    if current_user["role"]!= "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    new_role = Role(**role_request.dict())
    db.add(new_role)
    db.commit()
    db.refresh(new_role) 
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã tạo vai trò: {new_role.name}!")
    return {
        "detail": "Vai trò đã được tạo thành công!",
        "role": RoleResponse.from_orm(new_role)
    }
@router.put('/role/update', status_code=status.HTTP_200_OK)
async def update_role(role_id: int, role_request: RoleRequest, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể cập nhật vai trò."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    role_to_update = db.query(Role).filter(Role.id == role_id).first()
    if not role_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vai trò không tồn tại!")
    role_to_update.name = role_request.name
    role_to_update.description = role_request.description
    db.commit()
    db.refresh(role_to_update) 
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã cập nhật vai trò: {role_to_update.name}!")
    return {
        "detail": "Vai trò đã được cập nhật thành công!",
        "role": RoleResponse.from_orm(role_to_update)
    }
@router.delete('/role/{role_id}', status_code=status.HTTP_200_OK)
async def delete_role(role_id: int, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể xóa vai trò."""
    if current_user["role"]!= "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    role_to_delete = db.query(Role).filter(Role.id == role_id).first()
    if not role_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vai trò không tồn tại!")
    db.delete(role_to_delete)
    db.commit()
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã xóa vai trò: {role_to_delete}!")
    return {
        "detail": "Vai trò đã được xóa thành công!",
        "role_id": role_id
    }

