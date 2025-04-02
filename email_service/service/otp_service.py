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
    # Generate a random OTP code
    otp_code = str(random.randint(100000, 999999))
    # Set the expiration time for the OTP code
    expiration_time = datetime.now() + timedelta(seconds=OTP_EXPIRATION_TIME)
    db.query(OTPcode).filter(OTPcode.user_id == user_id).delete()
    # Save the OTP code and expiration time to the database
    otp_entry = OTPcode(user_id=user_id, code=otp_code, expires_at=expiration_time)
    db.add(otp_entry)
    db.commit()
    return otp_code
async def validate_otp(user_id: int, otp_code: str, db: db_dependency):
    # Retrieve the OTP entry from the database
    otp_entry = db.query(OTPcode).filter(OTPcode.user_id == user_id, OTPcode.code == otp_code).first()
    # Check if the OTP code is valid
    if not otp_entry or otp_entry.expires_at < datetime.utcnow():
        return False
    # If the OTP code is invalid, delete the entry from the database
    db.delete(otp_entry)
    db.commit()
    return True
    