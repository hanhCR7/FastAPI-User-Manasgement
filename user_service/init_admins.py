import os
from dotenv import load_dotenv
from security import hash_password
from db_config import db_dependency
from models import Users
from connect_service import assign_admin_role_to_user
from service.redis_client import redis_clients
load_dotenv()

DEAFULT_ADMIN_EMAIL = os.getenv("DEAFULT_ADMIN_EMAIL")
DEAFULT_ADMIN_PASSWORD = os.getenv("DEAFULT_ADMIN_PASSWORD")

async def init_admin(db: db_dependency):
    if redis_clients.exists("admin_initialized"):
        print("Người dùng quản trị viên đã được khởi tạo trước đó.")
        return
    admin = db.query(Users).filter_by(email=DEAFULT_ADMIN_EMAIL).first()
    if not admin:
        admin = Users(
            username="admin",
            email=DEAFULT_ADMIN_EMAIL,
            password_hash=hash_password(DEAFULT_ADMIN_PASSWORD),
            first_name="Admin",
            last_name="Admin",
            activation_token=None,
            is_active=True,
            status="Active"
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        # Gán quyền Admin cho người dùng
        await assign_admin_role_to_user(admin.id)
        print(f"Người dùng quản trị viên được tạo với ID: {admin.id}")
        print(f"Người dùng quản trị viên được tạo bằng email: {DEAFULT_ADMIN_EMAIL}")
    else:
        print(f"Người dùng quản trị đã tồn tại với email: {DEAFULT_ADMIN_EMAIL}")
    # Đánh dấu rằng người dùng quản trị đã được khởi tạo
    redis_clients.set("admin_initialized", "true")
