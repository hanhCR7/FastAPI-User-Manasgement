from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from databases import Base

class EmailLogs(Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True)
    recipient = Column(String, index=True)
    subject = Column(String)
    body = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
class OTPcode(Base):
    __tablename__ = "otp_codes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
