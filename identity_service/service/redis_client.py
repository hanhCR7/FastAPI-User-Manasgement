import redis
import os
import json
from dotenv import load_dotenv

load_dotenv()

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_db = os.getenv("REDIS_DB")


try:
    redis_clients = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
    # Kiểm tra kết nối với Redis
    redis_clients.ping()
    print(f"Kết nối Redis thành công tại {redis_host}:{redis_port} (db {redis_db})")
except redis.ConnectionError as e:
    redis_clients = None
    print(f"Không thể kết nối đến Redis: {e}")

def cache_user(user_id: int, user_data: dict, ttl: int = 600):
    """Lưu thông tin của user vào Redis với TTL 10 phút """
    redis_clients.setex(f"User: {user_id}", ttl, json.dumps(user_data))

def get_cached_user(user_id: int):
    """Lấy thông tin user từ Redis"""
    data = redis_clients.get(f"User: {user_id}")
    return json.dumps(data) if data else None

def delete_cached_user(user_id: int):
    """Xóa cached user khi có thay đổi"""
    redis_clients.delete(f"User: {user_id}")

# Hàm kiểm tra cache trước khi truy vấn cơ sở dữ liệu
def get_user_role_from_cache(user_id: int):
    cache_key = f"user_roles_{user_id}"
    cached_data = redis_clients.get(cache_key)
    if cached_data:
        return cached_data.decode('utf-8')
    return None

# Hàm lưu thông tin vào cache
def set_user_role_in_cache(user_id: int, user_roles):
    cache_key = f"user_roles_{user_id}"
    # Chuyển object thành dict
    role_dict = {
        "id": user_roles.role.id,
        "name": user_roles.role.name,
        "description": user_roles.role.description,
    }
    user_role_json = json.dumps(role_dict)
    # Lưu vào cache với TTL 1 giờ (3600 giây)
    redis_clients.setex(cache_key, 3600, user_role_json)