from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from databases import get_db
from service.email_service import send_email
from schemas import OTPRequest, VerifyOTPRequest
from service.otp_service import generate_otp, validate_otp

router = APIRouter(prefix="/api/email_service",tags=["emails"])
@router.post("/send-otp-email/")
async def send_otp_email(request: OTPRequest, db: Session = Depends(get_db)):
    try:
        otp = await generate_otp(db, request.user_id)  # Truyền user_id trước, db sau
        print(otp)
        await send_email(db, request.email, "OTP Code", f"Your OTP code is: {otp}")
        return {
            "status": "success",
            "message": "Email OTP được gửi thành công"
        }
    except Exception as e:
        return HTTPException(status_code=500, detail=f"Error sending OTP email: {str(e)}")
@router.post("/validate-otp/", status_code=status.HTTP_200_OK)
async def validate_otp_api(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    is_valid = await validate_otp(request.user_id, request.otp, db)
    if is_valid:
        return {
            "status": "success",
            "message": "OTP hợp lệ"
        }
    return {"message": "OTP không hợp lệ"}