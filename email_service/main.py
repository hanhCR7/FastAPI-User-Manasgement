from fastapi import FastAPI
from routers import send_email, otp
from databases import Base, engine
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Email Service API")
# Gắn router
app.include_router(send_email.router)
app.include_router(otp.router)
@app.get("/api/email_service/")
async def root():
    return {"message": "Welcome to Email Service!"}