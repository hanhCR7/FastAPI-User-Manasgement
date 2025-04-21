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
