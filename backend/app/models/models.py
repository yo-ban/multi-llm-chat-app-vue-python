from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    """
    Represents a chat message with optional image attachments
    """
    role: str
    text: Optional[str]
    images: Optional[List[str]] = []

class ChatRequest(BaseModel):
    """
    Represents a chat request with all necessary parameters
    """
    messages: List[Message]
    model: str
    temperature: float = 0
    maxTokens: int = 4096
    system: str = ""
    stream: bool = True
    reasoningEffort: Optional[str] = None  # 'low', 'medium', or 'high'
    isReasoningSupported: bool = False
    websearch: bool = False  # Enable web search functionality using function calling
    multimodal: bool = False  # Whether the model supports multimodal inputs (e.g. images)
    imageGeneration: bool = False  # Whether the model supports image generation

class ErrorResponse(BaseModel):
    """
    Represents a standardized error response
    """
    error: str
    detail: Optional[str] = None
    status_code: int