import random
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from databases import db_dependency
from models import OTPcode
from connect_service import get_user

load_dotenv()
OTP_EXPIRATION_TIME = int(os.getenv("OTP_EXPIRATION_TIME"))
async def generate_otp(db: db_dependency, user_id: int):
    """Tạo và lưu mã OTP vào database."""
    # Tạo mã OTP ngẫu nhiên
    otp_code = str(random.randint(100000, 999999))
    # Tạo thời gian hết hạn cho mã OTP
    expiration_time = datetime.now() + timedelta(seconds=OTP_EXPIRATION_TIME)
    db.query(OTPcode).filter(OTPcode.user_id == user_id).delete()
    # Lưu mã OTP vào database
    otp_entry = OTPcode(user_id=user_id, code=otp_code, expires_at=expiration_time)
    db.add(otp_entry)
    db.commit()
    return otp_code
async def validate_otp(user_id: int, otp_code: str, db: db_dependency):
    # Lấy otp_entry từ database theo user_id và otp_code
    otp_entry = db.query(OTPcode).filter(OTPcode.user_id == user_id, OTPcode.code == otp_code).first()
    # Kiểm tra xem mã OTP có tồn tại và chưa hết hạn hay không
    if not otp_entry or otp_entry.expires_at < datetime.utcnow():
        return False
    # Xóa mã OTP sau khi xác thực thành công
    db.delete(otp_entry)
    db.commit()
    return True
    