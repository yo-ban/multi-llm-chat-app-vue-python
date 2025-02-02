from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from app.models.models import ChatRequest
from app.handlers.chat_handler import ChatHandler
from app.handlers.file_handler import FileHandler
from app.utils.logging_utils import get_logger, log_request_info, log_error, log_info

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

async def get_api_key(request: Request) -> str:
    """
    Dependency to extract and validate API key from request headers
    
    Args:
        request: FastAPI request object
        
    Returns:
        API key string
    """
    api_key = request.headers.get('x-api-key')
    if not api_key:
        raise HTTPException(status_code=401, detail="API key is required")
    return api_key

@app.post("/api/messages")
async def messages(
    request: Request,
    chat_request: ChatRequest,
    api_key: str = Depends(get_api_key)
) -> StreamingResponse:
    """
    Handle chat messages endpoint
    
    Args:
        request: FastAPI request object
        chat_request: Chat request parameters
        api_key: API key from request headers
        
    Returns:
        Streaming response with chat completion
    """
    try:
        await log_request_info(request)
        
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
