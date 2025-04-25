"""
設定サービス

設定ドメインのビジネスロジックを実装する
"""
from sqlalchemy.orm import Session
from typing import Dict, Optional, List, Any
from pydantic import ValidationError
from poly_mcp_client import PolyMCPClient

from app.domain.settings.repository import SettingsRepository
from app.domain.settings.schemas import SettingsCreate, SettingsResponse, PydanticCanonicalToolDefinition
from app.domain.settings.models import UserSettings # Type hinting用
from app.domain.settings.constants import KNOWN_VENDORS # Import known vendors

from poly_mcp_client.models import ServerConfig, CanonicalToolDefinition

from app.logger.logging_utils import log_info, log_error, log_warning

class SettingsService:
    """
    設定関連のビジネスロジックを提供するサービスクラス
    """
    
    def __init__(self, db: Session, mcp_manager: PolyMCPClient):
        """
        引数:
            db: SQLAlchemyセッション
            mcp_manager: PolyMCPClient インスタンス
        """
        self.settings_repo = SettingsRepository(db)
        self.mcp_manager = mcp_manager # MCPクライアントを保持
    
    async def get_settings_for_user(self, user_id: int) -> SettingsResponse:
        """
        ユーザーの設定と、現在利用可能なMCPツールリストを取得する。
        設定が存在しない場合はデフォルト設定を作成して返す。
        
        引数:
            user_id: ユーザーID
            
        戻り値:
            設定のレスポンスモデル (SettingsResponse)
        """
        db_settings = self.settings_repo.get_by_user_id(user_id)
        
        if db_settings is None:
            # 設定が存在しない場合はデフォルト値で作成
            default_settings_data = SettingsCreate()
            # create_or_update に渡すためにバリデーション済みMCP設定を準備 (空辞書)
            validated_mcp_config = {}
            try:
                # SettingsCreate の mcp_servers_config はバリデータで ServerConfig に変換される想定
                validated_mcp_config = default_settings_data.mcp_servers_config
            except ValueError: # バリデーションエラーの場合 (デフォルトは空なので通常発生しないはず)
                pass

            db_settings = self.settings_repo.create_or_update(
                user_id=user_id,
                api_keys=default_settings_data.api_keys,
                default_temperature=default_settings_data.default_temperature,
                default_max_tokens=default_settings_data.default_max_tokens,
                default_vendor=default_settings_data.default_vendor,
                default_model=default_settings_data.default_model,
                default_reasoning_effort=default_settings_data.default_reasoning_effort,
                default_web_search=default_settings_data.default_web_search,
                openrouter_models=default_settings_data.openrouter_models,
                title_generation_vendor=default_settings_data.title_generation_vendor,
                title_generation_model=default_settings_data.title_generation_model,
                mcp_servers_config=validated_mcp_config, # バリデーション済み(空)
                disabled_mcp_servers=default_settings_data.disabled_mcp_servers,
                disabled_mcp_tools=default_settings_data.disabled_mcp_tools,
            )
        
        # APIキーを復号化
        decrypted_api_keys = self.settings_repo.decrypt_api_keys(db_settings)

        # MCPサーバー設定を復号化・バリデーション
        decrypted_mcp_config = self.settings_repo.decrypt_mcp_servers_config(db_settings)

        # 利用可能なMCPツールリストを取得 (辞書のリストとして受け取る)
        available_tools_raw: List[Dict[str, Any]] = []
        try:
            # poly-mcp-client は辞書のリストを返す
            available_tools_raw = await self.mcp_manager.get_available_tools(vendor="canonical")
            log_info(f"SettingsService (get): Fetched {len(available_tools_raw)} raw available MCP tools.")
        except Exception as e:
            log_error(f"SettingsService (get): Error fetching available MCP tools: {e}", exc_info=True)



        # --- 辞書のリストを Pydantic モデルのリストに変換 ---
        available_tools_pydantic: List[PydanticCanonicalToolDefinition] = []
        validation_errors = 0
        for tool_dict in available_tools_raw:
            try:
                # ここで Pydantic モデルに変換＆バリデーション
                validated_tool = PydanticCanonicalToolDefinition.model_validate(tool_dict)
                available_tools_pydantic.append(validated_tool)
            except ValidationError as e:
                validation_errors += 1
                # エラーの詳細をログに出力（ツール名も特定）
                tool_name = tool_dict.get('name', 'Unknown Tool')
                log_error(f"SettingsService (get): Validation error converting tool '{tool_name}' to Pydantic model: {e}", exc_info=False) # スタックトレースは不要かも
                # バリデーションエラーが起きても、エラーのあったツールを除外して続行
            except Exception as e:
                validation_errors += 1
                tool_name = tool_dict.get('name', 'Unknown Tool')
                log_error(f"SettingsService (get): Unexpected error converting tool '{tool_name}': {e}", exc_info=True)

        if validation_errors > 0:
            log_warning(f"SettingsService (get): Skipped {validation_errors} tool(s) due to validation/conversion errors.")

        # レスポンスデータを準備
        response_data = self._prepare_response_data(
            db_settings, decrypted_api_keys, decrypted_mcp_config, available_tools_pydantic
        )

        return SettingsResponse.model_validate(response_data)
        
    async def update_settings_for_user(self, user_id: int, settings_data: SettingsCreate) -> SettingsResponse:
        """
        ユーザーの設定を更新する。
        
        引数:
            user_id: ユーザーID
            settings_data: 更新する設定データ (SettingsCreate)
            
        戻り値:
            更新された設定のレスポンスモデル (SettingsResponse)
        """
        log_info(f"Starting settings update for user {user_id}")
        # SettingsCreate のバリデータで mcp_servers_config は検証済み
        validated_mcp_config = settings_data.mcp_servers_config

        db_settings = self.settings_repo.create_or_update(
            user_id=user_id,
            api_keys=settings_data.api_keys,
            default_temperature=settings_data.default_temperature,
            default_max_tokens=settings_data.default_max_tokens,
            default_vendor=settings_data.default_vendor,
            default_model=settings_data.default_model,
            default_reasoning_effort=settings_data.default_reasoning_effort,
            default_web_search=settings_data.default_web_search,
            openrouter_models=settings_data.openrouter_models,
            title_generation_vendor=settings_data.title_generation_vendor,
            title_generation_model=settings_data.title_generation_model,
            mcp_servers_config=validated_mcp_config, # バリデーション済み
            disabled_mcp_servers=settings_data.disabled_mcp_servers,
            disabled_mcp_tools=settings_data.disabled_mcp_tools,
        )
        log_info(f"Settings saved to DB for user {user_id}")

        # MCPクライアントの設定を更新
        try:
            log_info(f"Updating MCP client configuration for user {user_id}")
            # DBから最新の「有効な」設定を取得
            active_mcp_config = self.get_active_mcp_servers_config(user_id)

            # PolyMCPClient が期待する形式に変換
            mcp_client_config_data = {
                "mcpServers": {
                    name: config.model_dump() for name, config in active_mcp_config.items()
                }
            }

            # MCPクライアントに設定更新を指示
            await self.mcp_manager.update_configuration(config_data=mcp_client_config_data)
            log_info(f"MCP client configuration updated successfully for user {user_id}")

            # 更新後の接続状態を待機
            log_info("Waiting for connections after update...")
            connection_results = await self.mcp_manager.wait_for_connections(timeout=30.0)
            log_info(f"Connection status after update: {connection_results}")

        except Exception as e:
            # MCPクライアントの更新に失敗しても、DB設定は保存されている
            log_error(f"SettingsService (update): Error updating MCP client configuration: {e}")

        # APIキーを復号化
        decrypted_api_keys = self.settings_repo.decrypt_api_keys(db_settings)

        # MCPサーバー設定を復号化 (更新直後なのでバリデーションは不要かもしれないが念のため)
        decrypted_mcp_config = self.settings_repo.decrypt_mcp_servers_config(db_settings)

        # MCPクライアント更新後に再度ツールリストを取得
        available_tools_raw: List[Dict[str, Any]] = []
        try:
            available_tools_raw = await self.mcp_manager.get_available_tools(vendor="canonical")
            log_info(f"SettingsService (update): Fetched {len(available_tools_raw)} raw available MCP tools after update.")
        except Exception as e:
            log_error(f"SettingsService (update): Error fetching available MCP tools after update: {e}", exc_info=True)

        # --- 辞書のリストを Pydantic モデルのリストに変換 ---
        available_tools_pydantic: List[PydanticCanonicalToolDefinition] = []
        validation_errors = 0
        for tool_dict in available_tools_raw:
            try:
                validated_tool = PydanticCanonicalToolDefinition.model_validate(tool_dict)
                available_tools_pydantic.append(validated_tool)
            except ValidationError as e:
                validation_errors += 1
                tool_name = tool_dict.get('name', 'Unknown Tool')
                log_error(f"SettingsService (update): Validation error converting tool '{tool_name}' to Pydantic model: {e}", exc_info=False)
            except Exception as e:
                validation_errors += 1
                tool_name = tool_dict.get('name', 'Unknown Tool')
                log_error(f"SettingsService (update): Unexpected error converting tool '{tool_name}': {e}", exc_info=True)

        if validation_errors > 0:
            log_warning(f"SettingsService (update): Skipped {validation_errors} tool(s) due to validation/conversion errors.")


        # レスポンスデータを準備
        response_data = self._prepare_response_data(
            db_settings, decrypted_api_keys, decrypted_mcp_config, available_tools_pydantic
        )

        log_info(f"Settings update process completed for user {user_id}")
        return SettingsResponse.model_validate(response_data)

    def get_decrypted_api_key(self, user_id: int, vendor: str) -> Optional[str]:
        """
        指定されたユーザーとベンダーの復号化されたAPIキーを取得する。

        引数:
            user_id: ユーザーID
            vendor: APIキーを取得するベンダー名

        戻り値:
            復号化されたAPIキー文字列、または見つからない場合はNone
        """
        db_settings = self.settings_repo.get_by_user_id(user_id)
        if not db_settings:
            return None
        
        decrypted_api_keys = self.settings_repo.decrypt_api_keys(db_settings)
        return decrypted_api_keys.get(vendor)

    def get_active_mcp_servers_config(self, user_id: int) -> Dict[str, ServerConfig]:
        """
        指定されたユーザーの **有効な** MCPサーバー設定のみを取得する。
        PolyMCPClient の初期化に使用する。

        引数:
            user_id: ユーザーID

        戻り値:
            有効なMCPサーバー設定の辞書 (サーバー名 -> ServerConfig)
        """
        db_settings = self.settings_repo.get_by_user_id(user_id)
        if not db_settings:
            return {}

        all_mcp_config = self.settings_repo.decrypt_mcp_servers_config(db_settings)
        disabled_servers = set(db_settings.disabled_mcp_servers or [])

        active_config = {
            name: config
            for name, config in all_mcp_config.items()
            if name not in disabled_servers
        }
        return active_config

    def get_disabled_mcp_tools(self, user_id: int) -> List[str]:
        """
        指定されたユーザーの無効なMCPツール名のリストを取得する。

        引数:
            user_id: ユーザーID

        戻り値:
            無効なツール名のリスト
        """
        db_settings = self.settings_repo.get_by_user_id(user_id)
        if not db_settings or not db_settings.disabled_mcp_tools:
            return []
        # DBから取得したJSONリストを返す
        return db_settings.disabled_mcp_tools

    def _prepare_response_data(
            self, 
            db_settings: UserSettings, 
            decrypted_api_keys: Dict[str, str], 
            decrypted_mcp_config: Dict[str, ServerConfig],
            available_tools: List[PydanticCanonicalToolDefinition]
        ) -> Dict:
        """
        データベースモデルと復号化されたAPIキーからレスポンス用辞書を作成するヘルパー
        
        引数:
            db_settings: UserSettingsモデルインスタンス
            decrypted_api_keys: 復号化されたAPIキーの辞書
            decrypted_mcp_config: 復号化・バリデーション済みのMCPサーバー設定辞書
        
        戻り値:
            レスポンススキーマに渡すための辞書
        """
        # UserSettingsモデルから基本データを取得 (Pydanticモデルを経由して辞書化)
        # ここで model_validate を使うと、ネストしたMCP設定も正しく変換される
        base_data = SettingsResponse.model_validate(db_settings).model_dump(by_alias=False) # DBカラム名基準で取得

        # APIキーの状態 (boolean) を生成
        api_keys_status = {
            vendor: bool(decrypted_api_keys.get(vendor))
            for vendor in KNOWN_VENDORS
        }
        
        # レスポンスデータを作成
        response_data = {
            "apiKeys": api_keys_status, # エイリアス 'apiKeys'
            "defaultTemperature": base_data.get("default_temperature"),
            "defaultMaxTokens": base_data.get("default_max_tokens"),
            "defaultVendor": base_data.get("default_vendor"),
            "defaultModel": base_data.get("default_model"),
            "defaultReasoningEffort": base_data.get("default_reasoning_effort"),
            "defaultWebSearch": base_data.get("default_web_search"),
            "openrouterModels": base_data.get("openrouter_models") or [], # Noneなら空リスト
            "titleGenerationVendor": base_data.get("title_generation_vendor"),
            "titleGenerationModel": base_data.get("title_generation_model"),
            # 復号化・バリデーション済みのMCP設定と無効リストをセット
            "mcpServersConfig": decrypted_mcp_config, # エイリアス 'mcpServersConfig'
            "disabledMcpServers": base_data.get("disabled_mcp_servers") or [], # エイリアス 'disabledMcpServers'
            "disabledMcpTools": base_data.get("disabled_mcp_tools") or [],   # エイリアス 'disabledMcpTools'
            "availableMcpTools": available_tools # alias "availableMcpTools"
        }
        
        return response_data