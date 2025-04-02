from fastapi import APIRouter, HTTPException, Depends, status
from models import Role, Permission, RolePermission
from auth_per import get_current_user
from databases import db_dependency
from schemas import RolePermissionRequest,RolePermissionResponse
from connect_service import log_user_action
router = APIRouter( prefix="/api/identity_service",tags=["role-permission"])
@router.get("/role-permission", status_code=status.HTTP_200_OK)
async def read_role_permission(db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể xem danh sách Vai trò - quyền"""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này") 
    list_role_permission = db.query(RolePermission).all()
    role_permission_list_response = [RolePermissionResponse.from_orm(role_permission) for role_permission in list_role_permission]
    log_user_action(current_user["user_id"], f"{current_user["username"]}: Đã xem danh sách vai trò - quyền")
    return {
        "details": "Danh sách vai trò - quyền",
        "role_permission": role_permission_list_response
    }
@router.post("/role-permission/create", status_code=status.HTTP_201_CREATED)
async def create_role_permission(role_permission_request: RolePermissionRequest, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể gán quyền cho vai trò"""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    role = db.query(Role).filter(Role.name == role_permission_request.role_name).first()
    permission = db.query(Permission).filter(Permission.name == role_permission_request.permission_name).first()

    if not role or not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vai trò hoặc quyền không tồn tại!")
    if permission in role.permissions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Vai trò đã có quyền này")
    new_role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
    db.add(new_role_permission)
    db.commit()
    db.refresh(new_role_permission)
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã tạo vai trò - quyền {role_permission_request.role_name} - {role_permission_request.permission_name}")
    return {
        "detail": "Vai trò-quyền đã được tạo thành công",
        "role_permission": RolePermissionResponse.from_orm(new_role_permission)
    }
@router.put('/role-permission/update', status_code=status.HTTP_200_OK)
async def update_role_permission(role_permission_id: int, role_permission_request: RolePermissionRequest, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể cập nhật quyền cho vai trò."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    role_permission_to_update = db.query(RolePermission).filter(RolePermission.id == role_permission_id).first()
    if not role_permission_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vai trò - quyền không tồn tại!")
    role_permission_to_update.role_id = role_permission_request.role_id
    role_permission_to_update.permission_id = role_permission_request.permission_id
    db.commit()
    db.refresh(role_permission_to_update)
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã cập nhật vai trò - quyền {role_permission_request.role_name} - {role_permission_request.permission_name}")
    return {
        "detail": "Quyền vai trò đã được cập nhật thành công",
        "role_permission": RolePermissionResponse.from_orm(role_permission_to_update)
    }
@router.delete('/role-permission/{role_permission_id}', status_code=status.HTTP_200_OK)
async def delete_role_permission(role_permission_id: int, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể xóa quyền cho vai trò"""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    role_permission_to_delete = db.query(RolePermission).filter(RolePermission.id == role_permission_id).first()
    if not role_permission_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vai trò - quyền không tồn tại!")
    db.delete(role_permission_to_delete)
    db.commit()
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã xóa vai trò - quyền {role_permission_id}")
    return {
        "detail": "Đã xóa thành công quyền vai trò",
        "role_permission_id": role_permission_id
    }