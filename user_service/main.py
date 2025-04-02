from fastapi import FastAPI
from routers import users, logs
from databases import Base, engine
Base.metadata.create_all(bind=engine)
app = FastAPI(title="User Service API")
# Gắn router
app.include_router(users.router)
app.include_router(logs.router)
@app.get("/api/user_service")
async def root():
    return {"message": "Welcome to User Service"}