"""
データベース接続設定

SQLAlchemyを使用したデータベース接続の設定と依存関係の定義
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file if it exists

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:password@db:5432/appdb")
# Example for SQLite (if you switch later):
# DATABASE_URL = "sqlite:///./test.db" 
# engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) # Needed only for SQLite

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    """
    FastAPI依存関係として使用するためのセッション取得関数
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 