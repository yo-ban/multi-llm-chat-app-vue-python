"""
設定ドメインのスキーマ定義

Pydanticを使用した設定関連のデータ検証とシリアライズモデル
"""
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from poly_mcp_client.models import ServerConfig, McpServersConfig, CanonicalToolDefinition

class PydanticCanonicalToolItemsSchema(BaseModel):
    """Pydantic版: 配列要素のスキーマ"""
    type: str

class PydanticCanonicalToolParameter(BaseModel):
    """Pydantic版: ツールパラメータ"""
    type: str
    description: Optional[str] = None
    items: Optional[PydanticCanonicalToolItemsSchema] = None

    # バリデータ: type が 'array' でない場合、items は None であるべき
    @field_validator('items', mode='before')
    @classmethod
    def check_items_based_on_type(cls, v, info):
        """'items' は type が 'array' の場合にのみ存在するように調整"""
        # 'values' は Pydantic v2 では 'info.data' を使う
        if 'type' in info.data and info.data['type'] != 'array':
            if v is not None:
                # logger.warning(f"Non-array type '{info.data['type']}' has 'items' defined. Ignoring items.")
                # typeがarrayでない場合はitemsをNoneにする
                return None
        # typeがarrayでitemsがない場合、デフォルト値（例: string）を設定することも可能
        # elif 'type' in info.data and info.data['type'] == 'array' and v is None:
        #    logger.warning("Array type missing 'items'. Assuming string items.")
        #    return PydanticCanonicalToolItemsSchema(type='string')
        return v # 元の値を返す (None or PydanticCanonicalToolItemsSchema)

class PydanticCanonicalToolDefinition(BaseModel):
    """Pydantic版: カノニカルツール定義"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, PydanticCanonicalToolParameter]
    required: List[str]

class SettingsBase(BaseModel):
    """
    設定の基本スキーマ
    
    API設定とユーザー設定の基本情報を含む
    """
    # api_keys: Dict[str, str] = Field(default_factory=dict, alias="apiKeys")
    api_keys_status: Dict[str, bool] = Field(default_factory=dict, alias="apiKeys") 
    default_temperature: Optional[float] = Field(0.7, ge=0, le=2, alias="defaultTemperature")
    default_max_tokens: Optional[int] = Field(4096, gt=0, alias="defaultMaxTokens")
    default_vendor: Optional[str] = Field('anthropic', alias="defaultVendor")
    default_model: Optional[str] = Field('claude-3-5-sonnet-20240620', alias="defaultModel")
    default_reasoning_effort: Optional[str] = Field('medium', alias="defaultReasoningEffort")
    default_web_search: Optional[bool] = Field(False, alias="defaultWebSearch")
    openrouter_models: List[Dict[str, Any]] = Field(default_factory=list, alias="openrouterModels")
    title_generation_vendor: Optional[str] = Field('openai', alias="titleGenerationVendor")
    title_generation_model: Optional[str] = Field('gpt-4o-mini', alias="titleGenerationModel")
    # MCPサーバー設定 (レスポンスではバリデーション済みのものを返す)
    mcp_servers_config: Dict[str, ServerConfig] = Field(default_factory=dict, alias="mcpServersConfig")
    # 無効なMCPサーバー名のリスト
    disabled_mcp_servers: List[str] = Field(default_factory=list, alias="disabledMcpServers")
    # 無効なMCPツール名のリスト
    disabled_mcp_tools: List[str] = Field(default_factory=list, alias="disabledMcpTools")

    class Config:
        populate_by_name = True  # snake_caseとcamelCaseの両方を許可
        from_attributes = True   # SQLAlchemyモデルからの変換を許可
        # ServerConfig のような外部ライブラリの型を許容する
        arbitrary_types_allowed = True

class SettingsCreate(BaseModel):
    """
    設定作成用スキーマ
    
    設定の作成または更新に使用されるスキーマ
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
    # フロントエンドからは Dict[str, Any] で受け取る可能性があるため、Anyで受け取りバリデーションする
    mcp_servers_config: Dict[str, Any] = Field(default_factory=dict, alias="mcpServersConfig")
    disabled_mcp_servers: List[str] = Field(default_factory=list, alias="disabledMcpServers")
    disabled_mcp_tools: List[str] = Field(default_factory=list, alias="disabledMcpTools")

    # バリデータ: mcp_servers_config を ServerConfig に変換・検証
    @field_validator('mcp_servers_config', mode='before')
    def validate_mcp_servers_config(cls, v):
        if not isinstance(v, dict):
            raise ValueError("mcpServersConfig must be a dictionary")
        try:
            # McpServersConfig は RootModel なので、辞書全体を渡す
            validated_config = McpServersConfig.model_validate(v)
            # バリデーション後のモデルの辞書を返す (後の処理で使いやすいように)
            return validated_config.root
        except ValidationError as e:
            # PydanticのValidationErrorをFastAPIが処理できるようにValueErrorに変換
            raise ValueError(f"Invalid MCP server configuration: {e}")
        except Exception as e:
            # 予期せぬエラー
            raise ValueError(f"An unexpected error occurred during MCP server config validation: {e}")

    class Config:
        populate_by_name = True


class SettingsResponse(SettingsBase):
    """
    設定レスポンス用スキーマ
    クライアントへのレスポンスとして使用されるスキーマ。
    利用可能なMCPツール定義も含む。
    """
    # 利用可能な (接続中のサーバーから取得した) MCP ツール定義のリスト
    available_mcp_tools: List[PydanticCanonicalToolDefinition] = Field(default_factory=list, alias="availableMcpTools")

    class Config:
        from_attributes = True  # SQLAlchemyモデルからの変換を許可
        populate_by_name = True  # snake_caseとcamelCaseの両方を許可
        arbitrary_types_allowed = True # ServerConfig を許容
        json_schema_extra = {"example": {}}
        alias_generator = lambda field_name: ''.join(word.capitalize() if i else word for i, word in enumerate(field_name.split('_'))) 