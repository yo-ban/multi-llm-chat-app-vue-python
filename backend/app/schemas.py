from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

# Base schema now includes all configurable fields
class SettingsBase(BaseModel):
    api_keys: Dict[str, str] = Field(default_factory=dict, alias="apiKeys")
    default_temperature: Optional[float] = Field(0.7, ge=0, le=2, alias="defaultTemperature")
    default_max_tokens: Optional[int] = Field(4096, gt=0, alias="defaultMaxTokens")
    default_vendor: Optional[str] = Field('anthropic', alias="defaultVendor")
    default_model: Optional[str] = Field('claude-3-5-sonnet-20240620', alias="defaultModel")
    default_reasoning_effort: Optional[str] = Field('medium', alias="defaultReasoningEffort")
    default_web_search: Optional[bool] = Field(False, alias="defaultWebSearch")
    openrouter_models: List[Dict[str, Any]] = Field(default_factory=list, alias="openrouterModels")
    title_generation_vendor: Optional[str] = Field('openai', alias="titleGenerationVendor")
    title_generation_model: Optional[str] = Field('gpt-4o-mini', alias="titleGenerationModel")
    # Removed comment about separate handling

    class Config:
        populate_by_name = True  # Allow both snake_case and camelCase
        # allow_population_by_field_name = True  # For Pydantic v1 compatibility

# Schema for creating/updating settings (inherits all fields from Base)
class SettingsCreate(SettingsBase):
    pass # No additional fields needed

# Schema for responding to client (inherits all fields from Base)
class SettingsResponse(SettingsBase):
    class Config:
        # orm_mode = True # Pydantic v1
        from_attributes = True # Pydantic v2
        populate_by_name = True  # Allow both snake_case and camelCase
        # allow_population_by_field_name = True  # For Pydantic v1 compatibility
        # Add json serialization configuration to use aliases in response
        json_schema_extra = {"example": {}}
        alias_generator = lambda field_name: ''.join(word.capitalize() if i else word for i, word in enumerate(field_name.split('_')))

class Message(BaseModel):
    """
    Represents a chat message with optional image attachments
    """
    role: str
    text: Optional[str]
    images: Optional[List[str]] = Field(default_factory=list)

class ChatRequest(BaseModel):
    """
    Represents a chat request with all necessary parameters
    """
    messages: List[Message]
    model: str
    temperature: float = 0.7 # Match default from original model or settings?
    maxTokens: int = 4096
    system: str = ""
    stream: bool = True
    reasoningEffort: Optional[str] = None  # 'low', 'medium', or 'high'
    isReasoningSupported: bool = False
    websearch: bool = False
    multimodal: bool = False
    imageGeneration: bool = False
    # Consider adding vendor and conversation_id if they are part of the request schema
    vendor: Optional[str] = None 
    conversation_id: Optional[str] = None

class ErrorResponse(BaseModel):
    """
    Represents a standardized error response
    """
    error: str
    detail: Optional[str] = None
    status_code: int 