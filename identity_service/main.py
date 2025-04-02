from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from databases import engine
from fastapi.responses import HTMLResponse
from routers import role, permission, role_permission, user_role, auth
import models
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
@app.get("/")
async def root():
    return {"message": "Welcome to Identity Service"}