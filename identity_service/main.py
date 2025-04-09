from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from databases import engine
from fastapi.responses import HTMLResponse
from routers import role, permission, role_permission, user_role, auth
import models
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from limits.storage import RedisStorage
# Kiểm tra kết nối cơ sở dữ liệu
models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Identity Service API")
# Cấu hình CORS
origins = [
    "http://localhost:9000",
    "http://localhost:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"]
)
# Gắn router
app.include_router(role.router)
app.include_router(permission.router)
app.include_router(role_permission.router)
app.include_router(user_role.router)
app.include_router(auth.router)
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except RateLimitExceeded as e:
        return HTTPException(
            status_code=429,
            detail="Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau."
        )
@app.get("/")
async def root():
    return {"message": "Welcome to Identity Service"}