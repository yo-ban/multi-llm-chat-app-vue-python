from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

# 新しい構造からのインポート
from app.infrastructure.database import get_db
from app.domain.settings.schemas import SettingsCreate, SettingsResponse
# from app.domain.settings.repository import SettingsRepository # リポジトリはサービス内で使用
from app.domain.messages.schemas import ChatRequest
# サービス層のインポート
from app.application.settings.service import SettingsService

# 他のハンドラやロガーのインポート
from app.handlers.chat_handler import ChatHandler
from app.handlers.file_handler import FileHandler
from app.logger.logging_utils import get_logger, log_request_info, log_error, log_info

# 定数 (仮ユーザーID)
TEMP_USER_ID = 1

# Set up logging
logger = get_logger()

app = FastAPI()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Settings Endpoints --- (Using temporary fixed user ID)

@app.get("/api/settings", response_model=SettingsResponse)
def read_settings(db: Session = Depends(get_db)):
    """指定されたユーザーIDの設定を取得する"""
    settings_service = SettingsService(db)
    return settings_service.get_settings_for_user(user_id=TEMP_USER_ID)

@app.put("/api/settings", response_model=SettingsResponse)
def update_settings_endpoint(
    settings_data: SettingsCreate,
    db: Session = Depends(get_db)
):
    """指定されたユーザーIDの設定を更新する"""
    settings_service = SettingsService(db)

    # サービス層が Dict[str, str] を受け取り、リポジトリで処理する
    updated_settings_response = settings_service.update_settings_for_user(
        user_id=TEMP_USER_ID,
        settings_data=settings_data
    )

    # サービス層が返した SettingsResponse (apiKeys: Dict[str, bool]) を返す
    return updated_settings_response

# --- /api/messages エンドポイント --- 

@app.post("/api/messages")
async def messages(
    request: Request,                 # リクエスト情報取得用
    chat_request: ChatRequest,        # リクエストボディ
    db: Session = Depends(get_db)      # DBセッションを依存関係として注入
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
        settings_service = SettingsService(db)
        user_settings = settings_service.get_settings_for_user(TEMP_USER_ID)

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
        chat_handler = ChatHandler(api_key)
        
        # 6. チャットリクエストを処理
        return await chat_handler.handle_chat_request(chat_request, vendor)
        
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
