from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud.settings_crud import get_settings, update_settings, decrypt_settings, TEMP_USER_ID
from app.database import SessionLocal, engine, get_db, Base # Import Base and engine for database setup
from app.schemas import ChatRequest
from app.handlers.chat_handler import ChatHandler
from app.handlers.file_handler import FileHandler
from app.logger.logging_utils import get_logger, log_request_info, log_error, log_info

# テーブル自動作成コードを削除 - 代わりにAlembicマイグレーションに依存
# データベーススキーマの変更は以下のコマンドで実行します:
# 1. alembic revision --autogenerate -m "変更の説明"
# 2. alembic upgrade head
# 
# コンテナの起動時には、startup.shスクリプトによってマイグレーションが自動的に適用されます

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

@app.get("/api/settings", response_model=schemas.SettingsResponse)
def read_settings(db: Session = Depends(get_db)):
    """Retrieve settings for the hardcoded user."""
    db_settings = get_settings(db, user_id=TEMP_USER_ID)
    if db_settings is None:
        default_settings_data = schemas.SettingsCreate()
        db_settings = update_settings(db, user_id=TEMP_USER_ID, settings_data=default_settings_data)
    
    return decrypt_settings(db_settings)

@app.put("/api/settings", response_model=schemas.SettingsResponse)
def update_settings_endpoint(
    settings_data: schemas.SettingsCreate,
    db: Session = Depends(get_db)
):
    """Update settings for the hardcoded user."""
    db_settings = update_settings(db, user_id=TEMP_USER_ID, settings_data=settings_data)
    return decrypt_settings(db_settings)

# --- Existing Endpoints --- (Keep them as they are)

async def get_api_key(request: Request, db: Session = Depends(get_db)) -> str:
    """
    Dependency to extract and validate API key from request headers OR database.
    Currently, it still reads from the header for the /api/messages endpoint.
    TODO: Modify /api/messages to fetch the key from db_settings based on vendor.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        API key string (currently from header)
    """
    # --- Fetching from DB (Example - Needs integration into /api/messages) ---
    # db_settings = get_settings(db, user_id=TEMP_USER_ID)
    # if db_settings and db_settings.api_keys_encrypted:
    #     try:
    #         api_keys = json.loads(decrypt_data(db_settings.api_keys_encrypted))
    #         # Logic to determine which key to use based on chat_request.vendor
    #         # Example: return api_keys.get(chat_request.vendor)
    #     except Exception as e:
    #         print(f"Error getting API key from DB: {e}") # Log properly
    #         pass # Fallback to header or raise error
    # --- End Example ---
    
    # Current implementation: Still reads from header for /api/messages
    api_key = request.headers.get('x-api-key')
    if not api_key:
        # Instead of raising 401 immediately, we might allow access if DB keys exist
        # For now, keep original behavior for /api/messages
        raise HTTPException(status_code=401, detail="API key is required in header for this endpoint")
    return api_key

@app.post("/api/messages")
async def messages(
    request: Request,
    chat_request: ChatRequest,
    # Inject DB session here if needed to fetch API key from DB
    # db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key) # Keep Depends(get_api_key) for now
) -> StreamingResponse:
    """
    Handle chat messages endpoint
    TODO: Modify this to fetch API key from db_settings based on chat_request.vendor
    instead of relying solely on the x-api-key header.
    
    Args:
        request: FastAPI request object
        chat_request: Chat request parameters
        api_key: API key (currently from header via get_api_key)
        
    Returns:
        Streaming response with chat completion
    """
    try:
        await log_request_info(request)
        
        # --- Fetching API key from DB (Integration point) ---
        # 1. Get vendor from chat_request.vendor or determine from chat_request.model
        # 2. Call get_settings to get db_settings
        # 3. Decrypt api_keys_encrypted
        # 4. Get the specific key for the vendor: api_key = decrypted_keys.get(vendor)
        # 5. If key not found, raise HTTPException
        # 6. Pass the fetched api_key to ChatHandler
        # --- End Integration point ---
        
        # Current implementation still uses the key from the header via Depends(get_api_key)
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
    Handle file text extraction endpoint
    
    Args:
        request: FastAPI request object
        file: Uploaded file
        
    Returns:
        JSON response with extracted text
    """
    try:
        await log_request_info(request)
        
        file_handler = FileHandler()
        result = await file_handler.process_file(file)
        return JSONResponse(content=result)
        
    except Exception as e:
        log_error(e)
        raise HTTPException(status_code=400, detail=str(e))
