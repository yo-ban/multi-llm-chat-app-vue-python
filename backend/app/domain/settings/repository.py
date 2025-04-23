"""
設定リポジトリ

ユーザー設定関連のデータアクセスロジックを提供
"""
from typing import Optional, Dict, Any, List
import json
from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.domain.settings.models import UserSettings
from app.domain.user.repository import UserRepository
from app.infrastructure.encryption import encrypt_data, decrypt_data

# MCP設定のバリデーションと型定義のためインポート
from poly_mcp_client.models import ServerConfig, McpServersConfig

class SettingsRepository:
    """
    設定リポジトリ
    
    ユーザー設定エンティティのCRUD操作を提供します
    """
    
    def __init__(self, db: Session):
        """
        引数:
            db: SQLAlchemyセッション
        """
        self.db = db
        self.user_repository = UserRepository(db)
    
    def get_by_user_id(self, user_id: int) -> Optional[UserSettings]:
        """
        ユーザーIDによって設定を取得
        
        引数:
            user_id: ユーザーID
            
        戻り値:
            設定が見つかればUserSettingsオブジェクト、なければNone
        """
        return self.db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    def create_or_update(
        self, 
        user_id: int, 
        api_keys: Dict[str, str] = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
        default_vendor: str = 'anthropic',
        default_model: str = 'claude-3-5-sonnet-20240620',
        default_reasoning_effort: str = 'medium',
        default_web_search: bool = False,
        openrouter_models: list = None,
        title_generation_vendor: str = 'openai',
        title_generation_model: str = 'gpt-4o-mini',
        mcp_servers_config: Optional[Dict[str, ServerConfig]] = None, # バリデーション済みの型を受け取る
        disabled_mcp_servers: Optional[List[str]] = None,
        disabled_mcp_tools: Optional[List[str]] = None,
    ) -> UserSettings:
        """
        ユーザー設定を作成または更新
        
        引数:
            user_id: ユーザーID
            api_keys: APIキーの辞書
            default_temperature: デフォルト温度
            default_max_tokens: デフォルト最大トークン数
            default_vendor: デフォルトベンダー
            default_model: デフォルトモデル
            default_reasoning_effort: デフォルト推論努力
            default_web_search: デフォルトWeb検索フラグ
            openrouter_models: OpenRouterモデルのリスト
            title_generation_vendor: タイトル生成ベンダー
            title_generation_model: タイトル生成モデル
            mcp_servers_config: バリデーション済みのMCPサーバー設定の辞書
            disabled_mcp_servers: 無効なサーバーリスト
            disabled_mcp_tools: 無効なツールリスト

        戻り値:
            作成または更新された設定オブジェクト
        """
        if api_keys is None:
            api_keys = {}
        if openrouter_models is None:
            openrouter_models = []
        if mcp_servers_config is None:
            mcp_servers_config = {}
        if disabled_mcp_servers is None:
            disabled_mcp_servers = []
        if disabled_mcp_tools is None:
            disabled_mcp_tools = []

        # 既存の設定を取得
        settings = self.get_by_user_id(user_id)

        # 現在の復号化されたキーを取得（部分更新のため）
        current_decrypted_keys = {}
        if settings and settings.api_keys_encrypted:
            try:
                current_decrypted_keys = json.loads(decrypt_data(settings.api_keys_encrypted))
            except Exception as e:
                print(f"Error decrypting existing keys: {e}")
                current_decrypted_keys = {}

        # 更新するキーと現在のキーをマージ
        updated_keys = current_decrypted_keys.copy()
        for vendor, key_value in api_keys.items():
            if key_value == "": # フロントエンドから空文字が送られてきたら削除
                if vendor in updated_keys:
                    del updated_keys[vendor]
            elif key_value is not None: # nullでない場合のみ更新 (キー入力がなかった場合は更新しない)
                # '*' がプレースホルダーとして送られてくる可能性を考慮 (フロント実装による)
                # ここでは '*' 以外の場合のみ更新
                if key_value != '********': 
                    updated_keys[vendor] = key_value

        # マージされたキーを暗号化
        encrypted_api_keys = encrypt_data(json.dumps(updated_keys))

        # --- MCPサーバー設定の暗号化 ---
        # ServerConfig オブジェクトを JSON シリアライズ可能な辞書に変換
        mcp_config_dict = {name: config.model_dump() for name, config in mcp_servers_config.items()}
        encrypted_mcp_config = encrypt_data(json.dumps(mcp_config_dict))

        if settings:
            # 既存の設定を更新
            settings.api_keys_encrypted = encrypted_api_keys
            settings.default_temperature = default_temperature
            settings.default_max_tokens = default_max_tokens
            settings.default_vendor = default_vendor
            settings.default_model = default_model
            settings.default_reasoning_effort = default_reasoning_effort
            settings.default_web_search = default_web_search
            settings.openrouter_models = openrouter_models
            settings.title_generation_vendor = title_generation_vendor
            settings.title_generation_model = title_generation_model
            settings.mcp_servers_config_encrypted = encrypted_mcp_config
            settings.disabled_mcp_servers = disabled_mcp_servers
            settings.disabled_mcp_tools = disabled_mcp_tools
        else:
            # ユーザーが存在することを確認
            user = self.user_repository.get_by_id(user_id)
            if not user:
                user = self.user_repository.create(user_id)
                
            # 新しい設定を作成
            settings = UserSettings(
                user_id=user_id,
                api_keys_encrypted=encrypted_api_keys,
                default_temperature=default_temperature,
                default_max_tokens=default_max_tokens,
                default_vendor=default_vendor,
                default_model=default_model,
                default_reasoning_effort=default_reasoning_effort,
                default_web_search=default_web_search,
                openrouter_models=openrouter_models,
                title_generation_vendor=title_generation_vendor,
                title_generation_model=title_generation_model,
                mcp_servers_config_encrypted=encrypted_mcp_config,
                disabled_mcp_servers=disabled_mcp_servers,
                disabled_mcp_tools=disabled_mcp_tools
            )
            self.db.add(settings)
            
        self.db.commit()
        self.db.refresh(settings)
        return settings
    
    def decrypt_api_keys(self, settings: UserSettings) -> Dict[str, str]:
        """
        暗号化されたAPIキーを復号化
        
        引数:
            settings: 設定オブジェクト
            
        戻り値:
            APIキーの辞書
        """
        if not settings.api_keys_encrypted:
            return {}
            
        try:
            return json.loads(decrypt_data(settings.api_keys_encrypted))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error decrypting or parsing API keys: {e}")
            return {} 
        
    def decrypt_mcp_servers_config(self, settings: UserSettings) -> Dict[str, ServerConfig]:
        """
        暗号化されたMCPサーバー設定を復号化し、バリデーションする

        引数:
            settings: UserSettingsオブジェクト

        戻り値:
            バリデーション済みのMCPサーバー設定の辞書 (サーバー名 -> ServerConfig)
            復号化またはバリデーションに失敗した場合は空の辞書
        """
        if not settings.mcp_servers_config_encrypted:
            return {}

        try:
            decrypted_json_str = decrypt_data(settings.mcp_servers_config_encrypted)
            config_dict = json.loads(decrypted_json_str)
            # McpServersConfig を使って復号化後のデータをバリデーション
            validated_config = McpServersConfig.model_validate(config_dict)
            return validated_config.root
        except (json.JSONDecodeError, ValueError, TypeError, ValidationError) as e: # TypeError, ValidationError を追加
            print(f"Error decrypting or validating MCP server config: {e}")
            # エラーが発生した場合は空の設定を返す
            return {}