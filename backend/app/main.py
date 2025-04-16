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
    return settings_service.update_settings_for_user(
        user_id=TEMP_USER_ID,
        settings_data=settings_data
    )

# --- Existing Endpoints --- (Keep them as they are)

async def get_api_key(request: Request, db: Session = Depends(get_db)) -> str:
    """
    APIキーをリクエストヘッダーまたはデータベースから抽出・検証する依存関係。
    現在、/api/messages エンドポイントではヘッダーからのみ読み取る。
    TODO: /api/messages を変更し、ベンダーに基づいてDBからキーを取得するようにする。
          (SettingsServiceを使用して実装する)
    
    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション
        
    Returns:
        APIキー文字列 (現在はヘッダーから)
    """
    # TODO: SettingsServiceを使用してデータベースからAPIキーを取得するロジックを実装
    # settings_service = SettingsService(db)
    # settings = settings_service.get_settings_for_user(user_id=TEMP_USER_ID)
    # api_keys = settings.apiKeys # レスポンスモデルはcamelCase
    # vendor = chat_request.vendor # リクエストからベンダーを取得する必要あり
    # vendor_key = api_keys.get(vendor)
    # if vendor_key: return vendor_key
    
    # 現在の実装: /api/messages ではまだヘッダーから読み取る
    api_key = request.headers.get('x-api-key')
    if not api_key:
        # DBにキーが存在する場合でも、現状は401エラーとする
        raise HTTPException(status_code=401, detail="API key is required in header for this endpoint")
    return api_key

@app.post("/api/messages")
async def messages(
    request: Request,
    chat_request: ChatRequest,
    api_key: str = Depends(get_api_key) # 現状はDepends(get_api_key)を維持
) -> StreamingResponse:
    """
    チャットメッセージのエンドポイントを処理する。
    TODO: x-api-keyヘッダーのみに依存するのではなく、
          chat_request.vendorに基づいてdb_settingsからAPIキーを取得するように変更する。
          (get_api_key関数を修正し、SettingsServiceを利用する)
    
    Args:
        request: FastAPIリクエストオブジェクト
        chat_request: チャットリクエストパラメータ
        api_key: APIキー (get_api_key経由で現在はヘッダーから)
        
    Returns:
        チャット補完を含むストリーミングレスポンス
    """
    try:
        await log_request_info(request)
        
        # TODO: DBからAPIキーを取得するロジック（get_api_key関数内で実装）
        
        # 現在の実装はヘッダーからのキーを使用
        chat_handler = ChatHandler(api_key)
        return await chat_handler.handle_chat_request(chat_request)
        
    except Exception as e:
        log_error(e)
        raise HTTPException(status_code=400, detail=str(e))

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
