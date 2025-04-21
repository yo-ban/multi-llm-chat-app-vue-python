import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Dict, List, Any, Optional, Literal, Union, TypedDict
import logging
from pydantic import BaseModel, Field, ValidationError, RootModel

# MCP SDKのインポート
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import mcp.types as types

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MCPClientManager")

MCP_PREFIX = "mcp-"

# --- 設定データモデル---
class StdioServerConfig(BaseModel):
    """Stdioサーバー固有の設定"""
    type: str = Field("stdio", Literal=True) # typeフィールドを必須にし、値をstdioに固定
    command: str
    args: List[str] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = None

class HttpServerConfig(BaseModel):
    """HTTPサーバー固有の設定"""
    type: str = Field("http", Literal=True) # typeフィールドを必須にし、値をhttpに固定
    url: str
    # 必要に応じて認証情報などを追加

# Union型で Stdio または Http 設定を受け入れる
ServerConfig = Union[StdioServerConfig, HttpServerConfig]

# ルートモデルを使用して Dict[str, ServerConfig] を直接検証
class McpServersConfig(RootModel[Dict[str, ServerConfig]]):
    root: Dict[str, ServerConfig]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

# --- 内部で使用するサーバー定義  ---
class InternalServerDefinition(BaseModel):
    name: str
    type: str # "stdio" or "http"
    config: ServerConfig

# カノニカル形式のツールパラメータの型定義
class CanonicalToolItemsSchema(TypedDict):
    type: str # 配列要素の型 ('string', 'integer', 'number', 'boolean', 'object', 'array')

class CanonicalToolParameter(TypedDict):
    type: str # パラメータの型
    description: Optional[str]
    items: Optional[CanonicalToolItemsSchema] # typeが'array'の場合に使用

class CanonicalToolDefinition(TypedDict):
    name: str
    description: Optional[str]
    parameters: Dict[str, CanonicalToolParameter] # プロパティ名 -> パラメータ定義
    required: List[str]

# --- MCPClientManager クラス ---
class MCPClientManager:
    def __init__(self, prefix: str = MCP_PREFIX):
        self._sessions: Dict[str, ClientSession] = {}
        # サーバーのケイパビリティを保存する辞書
        self._server_capabilities: Dict[str, Optional[types.ServerCapabilities]] = {}
        self._server_definitions: Dict[str, InternalServerDefinition] = {}
        self._connection_tasks: Dict[str, asyncio.Task] = {}
        self._is_initialized = False
        self._lock = asyncio.Lock()
        self._prefix = prefix

    async def initialize_from_config(self, config_path: Optional[str] = None, config_data: Optional[Dict[str, Any]] = None):
        """
        指定された設定ファイルまたはデータからMCPサーバー接続を初期化する。
        config_path が指定された場合はファイルを読み込む。
        config_data が指定された場合は、{"mcpServers": {"server_key": {...}, ...}} の形式を期待する。
        enabledフラグは考慮せず、渡された設定すべてに接続を試みる。
        """
        async with self._lock:
            if self._is_initialized:
                logger.warning("MCPClientManagerは既に初期化されています。")
                return

            logger.info("MCPClientManagerの初期化を開始します...")
            servers_dict_data: Optional[Dict] = None # サーバー定義の辞書

            if config_path:
                logger.info(f"設定ファイル {config_path} を読み込みます。")
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        raw_config_data = json.load(f)
                    # ファイルから読み込んだ場合、mcpServers キーをチェック
                    if "mcpServers" not in raw_config_data or not isinstance(raw_config_data.get("mcpServers"), dict):
                        logger.error(f"設定ファイル {config_path} の形式が不正です。トップレベルに 'mcpServers' オブジェクトが必要です。")
                        return
                    servers_dict_data = raw_config_data["mcpServers"] # 辞書の中身を取得

                except FileNotFoundError:
                    logger.error(f"設定ファイルが見つかりません: {config_path}")
                    return
                except json.JSONDecodeError as e:
                    logger.error(f"設定ファイルのJSON解析エラー: {e}")
                    return
            elif config_data:
                logger.info("提供された設定データを使用します。")
                # config_data が mcpServers キーを持つことを期待
                if "mcpServers" not in config_data or not isinstance(config_data.get("mcpServers"), dict):
                      logger.error(f"提供された設定データの形式が不正です。トップレベルに 'mcpServers' オブジェクトが必要です。")
                      return
                servers_dict_data = config_data["mcpServers"] # 辞書の中身を取得
            else:
                logger.warning("設定ファイルパスも設定データも提供されませんでした。初期化をスキップします。")
                return

            # servers_dict_data が None または空でないかチェック
            if servers_dict_data is None:
                logger.error("初期化に使用するサーバー設定データがありません。")
                return
            if not servers_dict_data:
                logger.info("初期化に使用するサーバー設定が空です。接続するサーバーはありません。")
                self._is_initialized = True # 空でも初期化は完了したとみなす
                return

            # --- Pydantic 検証と接続開始処理 ---
            self._server_definitions.clear()
            validated_count = 0
            try:
                # ここでサーバー定義の辞書を検証 (servers_dict_data を渡す)
                parsed_servers = McpServersConfig.model_validate(servers_dict_data)

                for server_name, server_config in parsed_servers.root.items():
                    server_type = server_config.type
                    internal_def = InternalServerDefinition(
                        name=server_name,
                        type=server_type,
                        config=server_config
                    )
                    self._server_definitions[server_name] = internal_def
                    validated_count += 1

                logger.info(f"{validated_count} 個のMCPサーバー設定を正常に読み込みました。")

            except ValidationError as e:
                logger.error(f"MCPサーバー設定の検証エラー:\n{e}")
                return # エラーがあれば初期化失敗

            # 接続タスク開始
            connection_futures = []
            for name, definition in self._server_definitions.items():
                task = self._start_connection(name, definition)
                if task:
                    connection_futures.append(task)

            self._is_initialized = True
            logger.info("MCPClientManagerの初期化が完了しました。接続はバックグラウンドで試行されます。")

    def _start_connection(self, name: str, definition: InternalServerDefinition) -> Optional[asyncio.Task]:
        """個別のサーバーへの接続タスクを作成し、管理する"""
        # ... (内部ロジックはほぼ同じ) ...
        if name in self._connection_tasks and not self._connection_tasks[name].done():
            logger.info(f"サーバー '{name}' の接続タスクは既に実行中です。")
            return self._connection_tasks[name]

        logger.info(f"サーバー '{name}' ({definition.type}) の接続・監視タスクを開始します...")
        # ★ _connect_and_monitor に渡す型も InternalServerDefinition に
        task = asyncio.create_task(self._connect_and_monitor(name, definition))
        self._connection_tasks[name] = task
        task.add_done_callback(lambda t: self._connection_tasks.pop(name, None))
        return task

    async def _connect_and_monitor(self, name: str, definition: InternalServerDefinition):
        """サーバーへの接続、セッション確立、プロセス監視を行うコルーチン (stdio_client ヘルパー使用)"""
        # ... (処理の前半、型チェックとconfig取得部分を修正) ...
        retry_delay = 5
        max_retry_delay = 60

        while self._is_initialized:
            session = None
            exit_stack = AsyncExitStack()
            capabilities = None # ループ内でリセット

            try:
                if definition.type == "stdio":
                    # ★ definition.config が StdioServerConfig であることを確認
                    if not isinstance(definition.config, StdioServerConfig):
                        logger.error(f"サーバー '{name}' の内部設定タイプが不正です (Expected StdioServerConfig)。")
                        break
                    stdio_config = definition.config # 正しい型のはず
                    server_params = StdioServerParameters(
                        command=stdio_config.command,
                        args=stdio_config.args,
                        env=stdio_config.env
                    )
                    logger.info(f"サーバー '{name}' への接続を試行します: {stdio_config.command} {' '.join(stdio_config.args)}")

                    # --- 以降の接続・監視ロジックはほぼ変更なし ---
                    transport_streams = await exit_stack.enter_async_context(stdio_client(server_params))
                    reader, writer = transport_streams
                    logger.info(f"サーバー '{name}' へのトランスポート接続完了。")

                    session = await exit_stack.enter_async_context(ClientSession(reader, writer))
                    init_result = await session.initialize()
                    self._sessions[name] = session
                    capabilities = init_result.capabilities
                    self._server_capabilities[name] = capabilities

                    logger.info(f"サーバー '{name}' へのMCP接続が確立しました。")
                    if capabilities:
                        logger.info(f"サーバー '{name}' の機能: {capabilities}")

                    retry_delay = 5

                    while self._is_initialized and name in self._sessions:
                        await asyncio.sleep(10)

                    logger.warning(f"サーバー '{name}' との接続が失われました（または監視ループ終了）。")


                elif definition.type == "http":
                    # ★ definition.config が HttpServerConfig であることを確認
                    if not isinstance(definition.config, HttpServerConfig):
                        logger.error(f"サーバー '{name}' の内部設定タイプが不正です (Expected HttpServerConfig)。")
                        break
                    http_config = definition.config # 正しい型のはず
                    logger.warning(f"HTTPサーバー '{name}' ({http_config.url}) の接続は未実装です。")
                    await asyncio.sleep(3600) # 実装されるまで待機（仮）
                    break # HTTPは未実装なのでループ終了
                else:
                    # これは InternalServerDefinition 生成時に防がれるはずだが念のため
                    logger.error(f"不明なサーバータイプです: {definition.type} ({name})")
                    break

            # --- (エラーハンドリング、再接続ロジックは変更なし) ---
            except ConnectionRefusedError:
                logger.error(f"サーバー '{name}' への接続が拒否されました。")
            except FileNotFoundError:
                # stdioの場合のみコマンドが存在
                cmd = definition.config.command if isinstance(definition.config, StdioServerConfig) else 'N/A'
                logger.error(f"サーバー '{name}' の起動コマンド '{cmd}' が見つかりません。")
            except asyncio.CancelledError:
                logger.info(f"サーバー '{name}' の接続タスクがキャンセルされました。")
                break # キャンセルされたらループ終了
            except Exception as e:
                logger.error(f"サーバー '{name}' の接続または監視中にエラーが発生しました: {e}", exc_info=False) # スタックトレースは冗長なのでFalseに
            finally:
                # ケイパビリティ情報も削除
                if name in self._server_capabilities:
                    del self._server_capabilities[name]
                if name in self._sessions:
                    del self._sessions[name]
                try:
                    await exit_stack.aclose()
                    logger.debug(f"サーバー '{name}' のリソーススタックをクリーンアップしました。")
                except Exception as e_stack:
                    logger.error(f"サーバー '{name}' のリソーススタッククリーンアップ中にエラー: {e_stack}")

                if not self._is_initialized:
                    logger.info(f"シャットダウン中のため、サーバー '{name}' の再接続は行いません。")
                    break # シャットダウン中はループ終了

            # 再接続ロジック (キャンセルされていない場合)
            logger.info(f"サーバー '{name}' への再接続を {retry_delay} 秒後に試みます...")
            try:
                await asyncio.sleep(retry_delay)
            except asyncio.CancelledError:
                logger.info(f"再接続待機中にキャンセルされました ({name})。")
                break # キャンセルされたらループ終了
            retry_delay = min(retry_delay * 2, max_retry_delay)

        logger.info(f"サーバー '{name}' の接続・監視タスクを終了します。")

    async def _monitor_process(self, name: str, process: asyncio.subprocess.Process):
        """stdioサーバープロセスを監視し、終了したらログを出力する"""
        pid = process.pid # 終了後にアクセスできなくなる可能性があるため保持
        try:
            return_code = await process.wait()
            logger.warning(f"サーバー '{name}' のプロセス (PID: {pid}) が終了コード {return_code} で終了しました。")
        except asyncio.CancelledError:
            # タスクがキャンセルされた場合、ここには到達しないことが多いが念のため
            logger.info(f"サーバー '{name}' (PID: {pid}) のプロセス監視タスクがキャンセルされました。")
            raise # キャンセルを伝播させる
        except Exception as e:
            logger.error(f"サーバー '{name}' (PID: {pid}) のプロセス監視中にエラー: {e}")
        # この関数がreturnすると、_connect_and_monitor のループは finally に進む

    def _mcp_tool_to_canonical(self, server_name: str, mcp_tool: types.Tool) -> CanonicalToolDefinition:
        """MCP Toolオブジェクトをカノニカル形式の辞書に変換する"""
        parameters: Dict[str, CanonicalToolParameter] = {}
        required: List[str] = []

        # inputSchemaが存在し、辞書型であることを確認
        if mcp_tool.inputSchema and isinstance(mcp_tool.inputSchema, dict):
            input_schema_dict = mcp_tool.inputSchema
            # typeが指定されていない場合、デフォルトを 'object' とみなすことが多い
            schema_type = input_schema_dict.get("type", "object")
            properties = input_schema_dict.get("properties")

            # スキーマのトップレベルがオブジェクト型の場合のみpropertiesを処理
            if schema_type == "object" and properties and isinstance(properties, dict):
                # requiredリストも辞書から取得
                required = input_schema_dict.get("required", [])
                if not isinstance(required, list): # requiredがリストでない場合のフォールバック
                    logger.warning(f"ツール '{server_name}/{mcp_tool.name}' の required がリストではありません: {required}")
                    required = []

                for param_name, schema_prop in properties.items():
                    # schema_prop も辞書型であることを期待
                    if not isinstance(schema_prop, dict):
                        logger.warning(f"ツール '{server_name}/{mcp_tool.name}' のパラメータ '{param_name}' のスキーマ定義が辞書型ではありません: {type(schema_prop)}")
                        continue

                    # typeがない場合は 'any' として扱う
                    param_type = schema_prop.get("type", "any")
                    param_data: CanonicalToolParameter = {
                        "type": param_type,
                        "description": schema_prop.get("description"),
                        # "items": None # デフォルトはNone
                    }

                    # typeが'array'の場合、itemsスキーマを処理
                    if param_type == "array":
                        items_schema = schema_prop.get("items")
                        # items が辞書形式の場合のみ処理
                        if isinstance(items_schema, dict):
                            item_type = items_schema.get("type", "any")
                            param_data["items"] = {"type": item_type}
                        elif items_schema is not None: # dictではないがNoneでもない場合
                            logger.warning(f"ツール '{server_name}/{mcp_tool.name}' の配列パラメータ '{param_name}' の items スキーマが辞書型ではありません: {type(items_schema)}")
                            # items情報なしとして扱う

                    parameters[param_name] = param_data
            elif properties and isinstance(properties, dict) and not input_schema_dict.get("type"):
                # typeが未指定でもpropertiesがあればobject型とみなす (寛容な処理)
                logger.debug(f"ツール '{server_name}/{mcp_tool.name}' の inputSchema は type='object' が未指定ですが、properties を処理します。")
                required = input_schema_dict.get("required", [])
                if not isinstance(required, list):
                    logger.warning(f"ツール '{server_name}/{mcp_tool.name}' の required がリストではありません: {required}")
                    required = []
                for param_name, schema_prop in properties.items():
                    if not isinstance(schema_prop, dict):
                        logger.warning(f"ツール '{server_name}/{mcp_tool.name}' のパラメータ '{param_name}' のスキーマ定義が辞書型ではありません: {type(schema_prop)}")
                        continue
                    param_type = schema_prop.get("type", "any")
                    param_data: CanonicalToolParameter = {
                        "type": param_type,
                        "description": schema_prop.get("description"),
                        # "items": None
                    }
                    if param_type == "array":
                        items_schema = schema_prop.get("items")
                        if isinstance(items_schema, dict):
                            item_type = items_schema.get("type", "any")
                            param_data["items"] = {"type": item_type}
                        elif items_schema is not None:
                            logger.warning(f"ツール '{server_name}/{mcp_tool.name}' の配列パラメータ '{param_name}' の items スキーマが辞書型ではありません: {type(items_schema)}")
                    parameters[param_name] = param_data
            # elif schema_type != "object":
                # オブジェクト型以外(例: 文字列や数値のみを取るツール)の場合、parametersは空になる
                # logger.debug(f"ツール '{server_name}/{mcp_tool.name}' の inputSchema は type='{schema_type}' で、parametersは空です。")
            # else:
                # propertiesがない場合など
                # logger.warning(f"ツール '{server_name}/{mcp_tool.name}' の inputSchema に properties が見つかりません: type={schema_type}")
                pass # propertiesがない場合はparametersは空

        elif mcp_tool.inputSchema:
            # inputSchema が辞書型ではない場合
            logger.warning(f"ツール '{server_name}/{mcp_tool.name}' の inputSchema が辞書型ではありません: type={type(mcp_tool.inputSchema)}")
        # else: inputSchema が None の場合は何もしない

        canonical_def: CanonicalToolDefinition = {
            "name": f"mcp-{server_name}-{mcp_tool.name}",
            "description": mcp_tool.description,
            "parameters": parameters,
            "required": required
        }
        return canonical_def

    async def get_available_tools(self) -> List[CanonicalToolDefinition]:
        """
        現在接続中の全ての有効なMCPサーバーから利用可能なツールリストを取得する。
        ツール定義はカノニカル形式で返される。
        ツール名は "server_name/tool_name" 形式。
        """
        if not self._is_initialized:
            logger.warning("MCPClientManagerが初期化されていません。空のツールリストを返します。")
            return []

        all_canonical_tools: List[CanonicalToolDefinition] = []
        tasks = []
        active_sessions_data = list(self._sessions.items()) # イテレーション用コピー

        async def fetch_and_convert_tools(name: str, session: ClientSession):
            # 保存しておいたケイパビリティ情報を参照
            capabilities = self._server_capabilities.get(name)
            if capabilities and capabilities.tools:
                try:
                    tools_result = await session.list_tools()
                    for mcp_tool in tools_result.tools:
                        # ★ 変換処理を呼び出す
                        canonical_tool = self._mcp_tool_to_canonical(name, mcp_tool)
                        all_canonical_tools.append(canonical_tool)
                except Exception as e:
                    logger.error(f"サーバー '{name}' からのツールリスト取得または変換に失敗しました: {e}", exc_info=False)
            else:
                logger.info(f"サーバー '{name}' はツール機能をサポートしていません、またはケイパビリティ情報がありません。")

        for name, session in active_sessions_data:
            tasks.append(fetch_and_convert_tools(name, session))

        if tasks:
            await asyncio.gather(*tasks)

        logger.info(f"{len(all_canonical_tools)} 個の外部MCPツール定義を取得しました。")
        return all_canonical_tools

    async def execute_mcp_tool(self, full_tool_name: str, arguments: Dict[str, Any]) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """
        指定されたMCPサーバーのツールを実行する。
        full_tool_name は "server_name/tool_name" の形式。
        """
        if not self._is_initialized:
            raise RuntimeError("MCPClientManagerが初期化されていません。")

        if 'mcp-' not in full_tool_name:
            raise ValueError(f"ツール名 '{full_tool_name}' は 'mcp-server_name-tool_name' 形式である必要があります。")

        # 'mcp-' プレフィックスを除去
        name_suffix = full_tool_name[4:]

        server_name: Optional[str] = None
        original_tool_name: Optional[str] = None

        # 登録されているサーバー名で前方一致検索
        # 例: mcp-my-server-1-get-tool-data -> my-server-1 が server_name, get-tool-data が tool_name
        # 例: mcp-files-list-files -> files が server_name, list-files が tool_name
        found_server_key = None
        for server_key in self._server_definitions.keys():
            prefix_to_check = f"{server_key}-"
            if name_suffix.startswith(prefix_to_check):
                # 最も長く一致するサーバー名を見つける (例: 'server' と 'server-ext' があれば後者を優先)
                if found_server_key is None or len(server_key) > len(found_server_key):
                    found_server_key = server_key

        if found_server_key:
            server_name = self._server_definitions[found_server_key].name # 辞書に登録されている正式な名前
            original_tool_name = name_suffix[len(found_server_key) + 1:] # サーバー名 + ハイフンの後がツール名

        if not server_name or not original_tool_name:
            raise ValueError(f"ツール名 '{full_tool_name}' に対応するアクティブなMCPサーバーが見つかりません。利用可能なサーバー: {list(self._server_definitions.keys())}")

        session = self._sessions.get(server_name)
        if not session:
            logger.error(f"MCPサーバー '{server_name}' が現在接続されていません。ツール '{original_tool_name}' を実行できません。")
            raise ConnectionError(f"MCP Server '{server_name}' is not connected.")

        logger.info(f"MCPツール '{server_name}/{original_tool_name}' (Canonical: {full_tool_name}) を引数 {arguments} で実行します...")
        try:
            call_result = await session.call_tool(original_tool_name, arguments)

            if call_result is None:
                logger.error(f"ツール '{full_tool_name}' の実行結果が None でした。")
                raise RuntimeError(f"Tool execution failed for '{full_tool_name}': Received None result.")

            logger.info(f"ツール '{full_tool_name}' の実行が完了しました。")

            if call_result.isError:
                error_content = call_result.content if call_result.content else "Unknown tool error"
                error_text = " ".join([c.text for c in error_content if isinstance(c, types.TextContent)]) if error_content else "N/A"
                logger.error(f"ツール '{full_tool_name}' の実行中にサーバー側でエラーが発生しました: {error_text}")
                raise RuntimeError(f"Tool execution error in '{full_tool_name}': {error_text}")
            return call_result.content if call_result.content else []
        except asyncio.TimeoutError:
            logger.error(f"ツール '{full_tool_name}' の実行がタイムアウトしました。")
            raise TimeoutError(f"Tool execution timed out for '{full_tool_name}'.")
        except ConnectionError as ce:
            logger.error(f"ツール '{full_tool_name}' 実行中に接続エラー: {ce}")
            raise
        except Exception as e:
            logger.error(f"ツール '{full_tool_name}' の実行中に予期せぬエラー: {e}", exc_info=True)
            raise

    # --- リソース・プロンプト関連のメソッド（スタブ） ---
    async def get_available_resources(self) -> Dict[str, List[Dict[str, Any]]]:
        logger.warning("get_available_resources はまだ実装されていません。")
        return {}

    async def read_mcp_resource(self, full_resource_uri: str) -> Any:
        logger.warning("read_mcp_resource はまだ実装されていません。")
        raise NotImplementedError

    async def get_available_prompts(self) -> Dict[str, List[Dict[str, Any]]]:
        logger.warning("get_available_prompts はまだ実装されていません。")
        return {}

    async def get_mcp_prompt(self, full_prompt_name: str, arguments: Dict[str, Any]) -> Any:
        logger.warning("get_mcp_prompt はまだ実装されていません。")
        raise NotImplementedError

    # --- クリーンアップ ---
    async def close_all_connections(self):
        """
        全てのMCPサーバー接続と関連プロセスを安全に閉じる。
        アプリケーション終了時に呼び出す。
        """
        async with self._lock:
            if not self._is_initialized:
                logger.info("MCPClientManagerは既にシャットダウン済みか、初期化されていません。")
                return

            logger.info("全てのMCP接続とプロセスのシャットダウンを開始します...")
            self._is_initialized = False # 新規接続や再接続ループを停止させるフラグ

            tasks_to_cancel = list(self._connection_tasks.values())
            self._connection_tasks.clear() # 早めにクリア

            if tasks_to_cancel:
                for task in tasks_to_cancel:
                    if not task.done():
                        task.cancel()
                # キャンセルされたタスクの完了を待つ (エラーは無視)
                # これにより、各タスクの finally ブロック内の exit_stack.aclose() が実行されるはず
                await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
                logger.info(f"{len(tasks_to_cancel)}個の接続・監視タスクをキャンセルし、完了を待ちました。")
            else:
                logger.info("キャンセルする接続・監視タスクはありませんでした。")

            # セッションとケイパビリティ情報をクリア
            self._sessions.clear()
            self._server_capabilities.clear()

            logger.info("MCP接続とプロセスのシャットダウン処理を要求しました。")

            # 非同期クリーンアップのための短い待機
            # これにより、gatherで待った後、さらにイベントループが
            # 完全にクリーンアップする時間を与える
            await asyncio.sleep(0.5) # 0.1秒から少し余裕を持たせる
            logger.info("非同期クリーンアップのための待機完了。")


    async def _wait_for_process_termination(self, process: asyncio.subprocess.Process, name: str):
        """プロセスの終了を待ち、タイムアウトしたらkillするヘルパー"""
        pid = process.pid # kill後にpidにアクセスできなくなるため保持
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
            logger.info(f"プロセス (PID: {pid}, Name: {name}) は正常にterminateされました。")
        except asyncio.TimeoutError:
            logger.warning(f"プロセス (PID: {pid}, Name: {name}) の terminate タイムアウト。killします。")
            try:
                process.kill()
                await process.wait() # kill後の終了を待つ
                logger.info(f"プロセス (PID: {pid}, Name: {name}) はkillされました。")
            except ProcessLookupError:
                logger.warning(f"killしようとしたプロセス (PID: {pid}, Name: {name}) は既に存在しませんでした。")
            except Exception as e_kill:
                logger.error(f"プロセスkillエラー (PID: {pid}, Name: {name}): {e_kill}")
        except Exception as e_wait:
            logger.error(f"プロセスwaitエラー (PID: {pid}, Name: {name}): {e_wait}")
