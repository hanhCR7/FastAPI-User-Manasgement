from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, Enum
from sqlalchemy.orm import relationship
from databases import Base
import enum
# Enum cho trạng thái người dùng
class UserStatus(enum.Enum):
    Active = "Active"
    Inactive = "Inactive"
    Banned = "Banned"
# Model Users (User Service)
class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    password_hash = Column(String, nullable=False)
    activation_token = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    status = Column(Enum(UserStatus, name="userstatus"), default=UserStatus.Inactive) 
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    # Quan hệ với bảng logs
    logs = relationship("Log", back_populates="user", cascade="all, delete", passive_deletes=True)
# Model Log (Lưu trữ các log của user)
class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), index=True, nullable=False)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime,default=func.now(), server_default=func.now(), nullable=False)
    # Quan hệ ngược với User
    user = relationship("Users", back_populates="logs")
