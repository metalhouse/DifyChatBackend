"""
聊天室系统数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, Enum, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()

class Chatroom(Base):
    """聊天室表"""
    __tablename__ = 'chatrooms'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, comment='聊天室名称')
    description = Column(Text, comment='聊天室描述')
    created_by = Column(String(36), nullable=False, comment='创建者用户ID')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, comment='是否启用')
    max_users = Column(Integer, default=100, comment='最大用户数')
    is_public = Column(Boolean, default=False, comment='是否公开')
    settings = Column(JSON, comment='聊天室设置')
    
    # 关系
    members = relationship("ChatroomMember", back_populates="chatroom", cascade="all, delete-orphan")
    messages = relationship("ChatroomMessage", back_populates="chatroom", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_created_by', 'created_by'),
        Index('idx_is_active', 'is_active'),
        Index('idx_created_at', 'created_at'),
    )


class ChatroomMember(Base):
    """聊天室成员表"""
    __tablename__ = 'chatroom_members'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chatroom_id = Column(String(36), ForeignKey('chatrooms.id'), nullable=False)
    user_id = Column(String(36), nullable=False)
    role = Column(Enum('admin', 'moderator', 'member', name='member_role'), default='member')
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime)
    is_muted = Column(Boolean, default=False)
    
    # 关系
    chatroom = relationship("Chatroom", back_populates="members")
    
    # 索引和约束
    __table_args__ = (
        Index('uk_chatroom_user', 'chatroom_id', 'user_id', unique=True),
        Index('idx_user_id', 'user_id'),
        Index('idx_joined_at', 'joined_at'),
    )


class ChatroomMessage(Base):
    """聊天消息表"""
    __tablename__ = 'chatroom_messages'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chatroom_id = Column(String(36), ForeignKey('chatrooms.id'), nullable=False)
    user_id = Column(String(36), nullable=False)
    user_name = Column(String(100), nullable=False, comment='发送时的用户名')
    content = Column(Text, nullable=False, comment='消息内容(如果加密则存储加密数据)')
    message_type = Column(Enum('text', 'image', 'file', 'system', name='message_type'), default='text')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    reply_to = Column(String(36), comment='回复的消息ID')
    
    # AES256加密相关字段
    encrypted = Column(Boolean, default=False, comment='是否加密')
    encryption_iv = Column(String(32), comment='AES加密初始化向量')
    encryption_tag = Column(String(32), comment='AES-GCM认证标签')
    message_hash = Column(String(64), comment='SHA256消息完整性校验码')
    
    # 关系
    chatroom = relationship("Chatroom", back_populates="messages")
    
    # 索引
    __table_args__ = (
        Index('idx_chatroom_created', 'chatroom_id', 'created_at'),
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_reply_to', 'reply_to'),
        Index('idx_encrypted', 'encrypted'),
    )


class ChatroomOnlineUser(Base):
    """在线用户表"""
    __tablename__ = 'chatroom_online_users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chatroom_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    user_name = Column(String(100), nullable=False)
    session_id = Column(String(100), nullable=False, comment='WebSocket会话ID')
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 索引和约束
    __table_args__ = (
        Index('uk_session', 'session_id', unique=True),
        Index('idx_chatroom_user', 'chatroom_id', 'user_id'),
        Index('idx_last_activity', 'last_activity'),
    )
