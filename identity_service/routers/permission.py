from fastapi import APIRouter, HTTPException, Depends, status
from models import Permission
from auth_per import get_current_user
from databases import db_dependency
from schemas import PermissionRequest, PermissionResponse
from connect_service import log_user_action
router = APIRouter( prefix="/api/identity_service",tags=["permission"],)
# API lấy danh sách permissions
@router.get("/permissions", status_code=status.HTTP_200_OK)
async def read_permissions(db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể xem danh sách tất cả các quyền."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    list_permission = db.query(Permission).all()
    permission_list_response = [PermissionResponse.from_orm(permission) for permission in list_permission]
    log_user_action( current_user["user_id"], f"{current_user["username"]}: Đã xem danh sách quyền.")
    return {
        "details": "Danh sách quyền: ",
        "permissions": permission_list_response  # Cải thiện tên key trả về
    }
# API thêm permission mới
@router.post('/permissions/create', status_code=status.HTTP_201_CREATED)
async def create_permission(permission_request: PermissionRequest, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể tạo quyền."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    new_permission = Permission(**permission_request.dict())
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)  # Đồng bộ lại permission mới vào db
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã tạo quyền {new_permission.name}.")
    return {
        "detail": "Quyền đã được tạo thành công",
        "permission": PermissionResponse.from_orm(new_permission)
    }
# API cập nhật permission
@router.put('/permission/update', status_code=status.HTTP_200_OK)
async def update_permission(permission_id: int, permission_request: PermissionRequest, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyền mới có thể cập nhật quyền."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    permission_to_update = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quyền không tồn tại!")
    permission_to_update.name = permission_request.name
    permission_to_update.description = permission_request.description
    db.commit()
    db.refresh(permission_to_update)  # Đồng bộ lại permission mới vào db
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã cập nhật quyền {permission_to_update.name}.")
    return {
        "detail": "Quyền đã cập nhật thành công!",
        "permission": PermissionResponse.from_orm(permission_to_update)
    }
# API xóa permission
@router.delete('/permission/{permission_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(permission_id: int, db: db_dependency, current_user: dict = Depends(get_current_user)):
    """Chỉ có Admin hoặc User được phân quyề mới có thể xóa quyền."""
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập vào tài nguyên này")
    permission_to_delete = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quyền không tồn tại")
    db.delete(permission_to_delete)
    db.commit()
    log_user_action(current_user["user_id"], f"{current_user['username']}: Đã xóa quyền {permission_to_delete}.")
    return {
        "detail": "Quyền đã được xóa thành công!",
        "permission_id": permission_id
    }
