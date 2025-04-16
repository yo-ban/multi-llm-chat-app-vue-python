"""
設定ドメインのスキーマ定義

Pydanticを使用した設定関連のデータ検証とシリアライズモデル
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class SettingsBase(BaseModel):
    """
    設定の基本スキーマ
    
    API設定とユーザー設定の基本情報を含む
    """
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

    class Config:
        populate_by_name = True  # snake_caseとcamelCaseの両方を許可
        from_attributes = True   # SQLAlchemyモデルからの変換を許可


class SettingsCreate(SettingsBase):
    """
    設定作成用スキーマ
    
    設定の作成または更新に使用されるスキーマ
    """
    pass  # 現時点では基本クラスから追加フィールドなし


class SettingsResponse(SettingsBase):
    """
    設定レスポンス用スキーマ
    
    クライアントへのレスポンスとして使用されるスキーマ
    """
    class Config:
        from_attributes = True  # SQLAlchemyモデルからの変換を許可
        populate_by_name = True  # snake_caseとcamelCaseの両方を許可
        json_schema_extra = {"example": {}}
        alias_generator = lambda field_name: ''.join(word.capitalize() if i else word for i, word in enumerate(field_name.split('_'))) 