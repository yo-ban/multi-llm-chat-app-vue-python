from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from app.database import Base

# --- SQLAlchemy Models for Database Tables ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # In a real app, add email, password_hash, etc.

    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    api_keys_encrypted = Column(LargeBinary, nullable=True) # Store encrypted JSON as bytes
    default_temperature = Column(Float, default=0.7)
    default_max_tokens = Column(Integer, default=4096)
    default_vendor = Column(String, default='anthropic')
    default_model = Column(String, default='claude-3-5-sonnet-20240620') # Ensure this matches your constants
    default_reasoning_effort = Column(String, default='medium')
    default_web_search = Column(Boolean, default=False)
    openrouter_models = Column(JSON, nullable=True)
    title_generation_vendor = Column(String, default='openai')
    title_generation_model = Column(String, default='gpt-4o-mini') # Ensure this matches your constants

    user = relationship("User", back_populates="settings")

# --- Pydantic Models removed from this file ---
# They are now located in schemas.py