"""
ユーザードメインのモデル定義
"""
from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base

class User(Base):
    """
    ユーザーモデル
    
    ユーザー情報を表すデータベースモデル
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # 実際のアプリでは、email、password_hashなどを追加

    # リレーションシップ
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan") 