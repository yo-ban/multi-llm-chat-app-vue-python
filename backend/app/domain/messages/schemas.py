"""
メッセージドメインのスキーマ定義

Pydanticを使用したメッセージ関連のデータ検証とシリアライズモデル
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class Message(BaseModel):
    """
    チャットメッセージモデル
    
    テキストと画像添付を持つメッセージを表現
    """
    role: str
    text: Optional[str]
    images: Optional[List[str]] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """
    チャットリクエストモデル
    
    LLMへのリクエストパラメータを表現
    """
    messages: List[Message]
    model: str
    temperature: float = 0.7 
    maxTokens: int = 4096
    system: str = ""
    stream: bool = True
    isReasoningSupported: bool = False
    reasoningParameterType: Optional[str] = None  # 'effort', 'budget'
    reasoningEffort: Optional[str] = None  # 'low', 'medium', 'high'
    budgetTokens: Optional[int] = None
    toolUse: bool = False
    multimodal: bool = False
    imageGeneration: bool = False
    vendor: Optional[str] = None
    conversation_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """
    標準エラーレスポンス
    
    統一されたエラーレスポンス形式
    """
    error: str
    detail: Optional[str] = None
    status_code: int 