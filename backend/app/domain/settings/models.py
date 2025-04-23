"""
設定ドメインのモデル定義
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base

class UserSettings(Base):
    """
    ユーザー設定モデル
    
    ユーザーのアプリケーション設定を表すデータベースモデル
    """
    __tablename__ = "user_settings"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    api_keys_encrypted = Column(LargeBinary, nullable=True)  # 暗号化されたJSONをバイトとして保存
    default_temperature = Column(Float, default=0.7)
    default_max_tokens = Column(Integer, default=4096)
    default_vendor = Column(String, default='anthropic')
    default_model = Column(String, default='claude-3-5-sonnet-20240620')
    default_reasoning_effort = Column(String, default='medium')
    default_web_search = Column(Boolean, default=False)
    openrouter_models = Column(JSON, nullable=True)
    title_generation_vendor = Column(String, default='openai')
    title_generation_model = Column(String, default='gpt-4o-mini')

    # MCPサーバー設定 (サーバー名 -> 設定 の辞書をJSON文字列化して暗号化)
    mcp_servers_config_encrypted = Column(LargeBinary, nullable=True)
    # 無効なMCPサーバー名のリスト
    disabled_mcp_servers = Column(JSON, nullable=True, default=list)
    # 無効なMCPツール名のリスト (例: ["mcp-server1-toolA", "mcp-server2-toolB"])
    disabled_mcp_tools = Column(JSON, nullable=True, default=list)
    # リレーションシップ
    user = relationship("User", back_populates="settings") 