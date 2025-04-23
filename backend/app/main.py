from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager # lifespanのために追加
import os # 設定ファイルパスのために追加
import json

# 新しい構造からのインポート
from app.infrastructure.database import get_db, SessionLocal
from app.domain.settings.schemas import SettingsCreate, SettingsResponse
# from app.domain.settings.repository import SettingsRepository # リポジトリはサービス内で使用
from app.domain.messages.schemas import ChatRequest
# サービス層のインポート
from app.application.settings.service import SettingsService

# 他のハンドラやロガーのインポート
from app.handlers.chat_handler import ChatHandler
from app.handlers.file_handler import FileHandler
from app.logger.logging_utils import get_logger, log_request_info, log_error, log_info

# --- PolyMCPClientのインポート ---
from poly_mcp_client import PolyMCPClient
from poly_mcp_client.models import McpServersConfig

# 定数 (仮ユーザーID)
TEMP_USER_ID = 1

# Set up logging
logger = get_logger()

# --- PolyMCPClientのシングルトンインスタンスを作成 ---
mcp_client_manager = PolyMCPClient()

# --- FastAPI lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPIアプリケーションのライフサイクル管理"""
    logger.info("FastAPI起動: MCPクライアントマネージャーを初期化・接続開始")

    mcp_init_config = None
    # データベースからアクティブなMCPサーバー設定を取得
    db: Session = SessionLocal() # lifespan内では Depends(get_db) が使えないため、直接セッションを作成
    settings_service = SettingsService(db, mcp_client_manager)
    try:
        # TEMP_USER_ID のアクティブな設定を取得
        active_mcp_config = settings_service.get_active_mcp_servers_config(TEMP_USER_ID)

        if active_mcp_config:
            logger.info(f"データベースから {len(active_mcp_config)} 個のアクティブなMCPサーバー設定を読み込みました。")
            # PolyMCPClient が期待する形式 {"mcpServers": {...}} に整形
            # ServerConfig オブジェクトを辞書に変換する必要がある
            mcp_init_config_data = {
                name: config.model_dump() for name, config in active_mcp_config.items()
            }
            mcp_init_config = {"mcpServers": mcp_init_config_data}
        else:
            logger.info("データベースにアクティブなMCPサーバー設定が見つかりませんでした。MCPサーバーは起動しません。")
            mcp_init_config = {"mcpServers": {}} # 空の設定で初期化

    except Exception as e:
        logger.error(f"データベースからのMCP設定読み込み中にエラーが発生しました: {e}", exc_info=True)
        # エラーが発生した場合も、空の設定で初期化を試みる
        mcp_init_config = {"mcpServers": {}}
    finally:
        db.close() # セッションを閉じる

    # PolyMCPClient を初期化
    if mcp_init_config is not None:
        try:
            # config_data を渡して初期化
            await mcp_client_manager.initialize(config_data=mcp_init_config)
            # 初期接続を待機 (タイムアウトを設定)
            connection_results = await mcp_client_manager.wait_for_initial_connections(timeout=60.0)
            logger.info(f"MCP初期接続試行完了: {connection_results}")
        except Exception as e:
            logger.error(f"PolyMCPClient の初期化または接続待機中にエラーが発生しました: {e}", exc_info=True)
            # 初期化に失敗した場合でも、アプリケーションは起動させる（MCP機能は利用不可）
    else:
        logger.error("MCP初期化設定の準備に失敗しました。MCPクライアントは初期化されません。")

    logger.info("FastAPIの準備完了。")
    yield
    # アプリケーション終了時
    logger.info("FastAPI終了: MCP接続をクリーンアップ")
    await mcp_client_manager.shutdown()
    logger.info("MCPクリーンアップ完了。")


# --- FastAPI アプリケーションインスタンス (lifespanを設定) ---
app = FastAPI(lifespan=lifespan)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PolyMCPClient 依存性注入 ---
async def get_mcp_manager():
    """依存性注入用の関数"""
    if not mcp_client_manager._is_initialized:
        # アプリケーション起動時に初期化されているはずだが、念のためチェック
        logger.error("PolyMCPClientが初期化されていません。")
        # 本番環境ではここでエラーを発生させるべき
        raise RuntimeError("PolyMCPClient is not initialized.")
    return mcp_client_manager

# --- Settings Endpoints --- (Using temporary fixed user ID)
@app.get("/api/settings", response_model=SettingsResponse)
async def read_settings(
    db: Session = Depends(get_db),
    mcp_manager: PolyMCPClient = Depends(get_mcp_manager)
):
    """指定されたユーザーIDの設定を取得する"""

    settings_service = SettingsService(db, mcp_manager)

    return await settings_service.get_settings_for_user(user_id=TEMP_USER_ID)

@app.put("/api/settings", response_model=SettingsResponse)
async def update_settings_endpoint(
    settings_data: SettingsCreate,
    db: Session = Depends(get_db),
    mcp_manager: PolyMCPClient = Depends(get_mcp_manager)
):
    """指定されたユーザーIDの設定を更新する"""
    settings_service = SettingsService(db, mcp_manager)
    try:
        # サービス層が SettingsCreate を受け取り、内部で処理する
        updated_settings_response = await settings_service.update_settings_for_user(
            user_id=TEMP_USER_ID,
            settings_data=settings_data
        )
        # サービス層が返した SettingsResponse を返す
        return updated_settings_response

    except ValueError as ve:
        # SettingsCreate のバリデータからのエラーをハンドル
        log_error(f"設定更新時のバリデーションエラー: {ve}")
        # PydanticのValidationError起因の場合は詳細メッセージを含める
        detail = str(ve)
        if "Invalid MCP server configuration" in detail:
            # エラーメッセージから詳細部分を抽出（より親切なエラー表示のため）
            try:
                detail = detail.split("Invalid MCP server configuration: ", 1)[1]
            except IndexError:
                pass # 抽出失敗時は元のメッセージのまま
        raise HTTPException(status_code=422, detail=f"Invalid settings data: {detail}")
    except Exception as e:
        log_error(f"設定更新中に予期せぬエラーが発生: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during settings update.")

# --- /api/messages エンドポイント --- 

@app.post("/api/messages")
async def messages(
    request: Request,                 # リクエスト情報取得用
    chat_request: ChatRequest,        # リクエストボディ
    db: Session = Depends(get_db),      # DBセッションを依存関係として注入    
    mcp_manager: PolyMCPClient = Depends(get_mcp_manager) # PolyMCPClientを依存性注入で取得
) -> StreamingResponse:
    """
    チャットメッセージのエンドポイントを処理する。
    データベースからユーザー設定を取得し、リクエストされたベンダーに対応するAPIキーを使用する。
    
    Args:
        request: FastAPIリクエストオブジェクト
        chat_request: チャットリクエストパラメータ (ベンダー情報を含む)
        db: データベースセッション
        
    Returns:
        チャット補完を含むストリーミングレスポンス
        
    Raises:
        HTTPException(400): リクエストにベンダー情報がない場合、または設定に該当ベンダーのAPIキーがない場合
        HTTPException(500): その他のサーバーエラー
    """
    try:
        await log_request_info(request)

        # 1. 設定サービスを使ってユーザー設定を取得 (主にキー設定状況の確認用)
        settings_service = SettingsService(db, mcp_manager)
        user_settings = await settings_service.get_settings_for_user(TEMP_USER_ID) 

        # 2. リクエストからベンダー情報を取得
        vendor = chat_request.vendor
        if not vendor:
            # TODO: vendorがない場合、model名から推測するロジックを追加することも検討
            log_error(f"Vendor not specified in chat request for model {chat_request.model}")
            raise HTTPException(status_code=400, detail="Vendor is required in the chat request.")

        # 3. 取得した設定から該当ベンダーのAPIキーが *設定されているか* を確認
        # (user_settings.api_keys は存在しないため、api_keys_status を使用)
        if not user_settings.api_keys_status.get(vendor):
            log_error(f"API key for vendor '{vendor}' not configured for user {TEMP_USER_ID}.")
            raise HTTPException(
                status_code=400, 
                detail=f"API key for '{vendor}' is not configured. Please add it in the settings."
            )

        # 4. 設定されている場合、実際のAPIキーを取得
        api_key = settings_service.get_decrypted_api_key(TEMP_USER_ID, vendor)
        if not api_key:
            # このケースは通常発生しないはず (Status=Trueなのにキーが取得できない場合)
            log_error(f"Configured API key for vendor '{vendor}' could not be retrieved for user {TEMP_USER_ID}.")
            raise HTTPException(
                status_code=500, 
                detail=f"Could not retrieve configured API key for '{vendor}'."
            )
            
        # 5. 取得したAPIキーを使ってChatHandlerを初期化
        chat_handler = ChatHandler(api_key, settings_service)
        
        # 6. チャットリクエストを処理
        return await chat_handler.handle_chat_request(
            chat_request, 
            vendor, 
            mcp_manager
        )
        
    except HTTPException as http_exc:
        # FastAPIからのHTTPExceptionはそのまま再raiseする
        raise http_exc
    except Exception as e:
        # その他の予期せぬエラー (exc_info=True を削除)
        log_error(f"Error handling chat request: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

# --- ファイル抽出エンドポイント --- 

@app.post('/api/extract-text')
async def extract_text(
    request: Request,
    file: UploadFile = File(...)
) -> JSONResponse:
    """
    ファイルテキスト抽出エンドポイントを処理する。
    
    Args:
        request: FastAPIリクエストオブジェクト
        file: アップロードされたファイル
        
    Returns:
        抽出されたテキストを含むJSONレスポンス
    """
    try:
        await log_request_info(request)
        
        file_handler = FileHandler()
        result = await file_handler.process_file(file)
        return JSONResponse(content=result)
        
    except Exception as e:
        log_error(e)
        raise HTTPException(status_code=400, detail=str(e))
