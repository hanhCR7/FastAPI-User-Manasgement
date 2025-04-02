from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
from databases import Base
Base = declarative_base()
# Bảng roles
class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    permissions = relationship('Permission', secondary='role_permission', back_populates='roles')
    user_roles = relationship('UserRole', back_populates='role')  # Quan hệ với UserRole
# Bảng permissions
class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    roles = relationship('Role', secondary='role_permission', back_populates='permissions')
# Bảng role_permission (nhiều-nhiều giữa roles và permissions)
class RolePermission(Base):
    __tablename__ = 'role_permission'
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'))
    permission_id = Column(Integer, ForeignKey('permissions.id'))
# Bảng user_role (nhiều-nhiều giữa users và roles)
class UserRole(Base):
    __tablename__ = 'user_role'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)  
    role_id = Column(Integer, ForeignKey('roles.id'))
    role = relationship('Role', back_populates='user_roles')  # Quan hệ với Role
class BackListTokens(Base):
    __tablename__ = 'blacklisted_tokens'
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    token = Column(String(500), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(minutes=15))  # Thời gian hết hạn của token