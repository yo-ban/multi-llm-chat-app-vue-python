import logging
import sys
from typing import Optional, Any, Dict
from fastapi import Request
import json

# Global logger instance
app_logger: Optional[logging.Logger] = None

def get_logger() -> logging.Logger:
    """
    Get the global logger instance. If it hasn't been set up, create it.
    
    Returns:
        Global logger instance
    """
    global app_logger
    if app_logger is None:
        app_logger = setup_logger("app")
    return app_logger

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with the specified name and level
    
    Args:
        name: Name of the logger
        level: Logging level (default: INFO)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Prevent propagation to root logger
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger

async def log_request_info(request: Request, logger: Optional[logging.Logger] = None) -> None:
    """
    Log information about an incoming request
    
    Args:
        request: FastAPI request object
        logger: Logger instance (optional, will use global logger if not provided)
    """
    logger = logger or get_logger()
    body = await request.body()
    try:
        body_json = json.loads(body)
    except:
        body_json = {"raw": str(body)}
        
    logger.info(
        f"Request: {request.method} {request.url}"
    )

def log_error(
    error: Exception,
    request_id: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Log an error with context information
    
    Args:
        error: Exception that occurred
        request_id: Optional request ID for tracking
        additional_info: Optional dictionary with additional context
        logger: Logger instance (optional, will use global logger if not provided)
    """
    logger = logger or get_logger()
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "request_id": request_id,
        **(additional_info or {})
    }
    
    logger.error(
        f"Error occurred: {json.dumps(error_info, indent=2)}",
        exc_info=True
    )

def log_info(
    message: str,
    additional_info: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Log an info message with optional context information
    
    Args:
        message: The main message to log
        additional_info: Optional dictionary with additional context
        logger: Logger instance (optional, will use global logger if not provided)
    """
    logger = logger or get_logger()
    if additional_info:
        logger.info(f"{message} - Additional Info: {json.dumps(additional_info, indent=2)}")
    else:
        logger.info(message)

def log_warning(
    message: str,
    additional_info: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Log a warning message with optional context information
    
    Args:
        message: The main warning message to log
        additional_info: Optional dictionary with additional context
        logger: Logger instance (optional, will use global logger if not provided)
    """
    logger = logger or get_logger()
    if additional_info:
        logger.warning(f"{message} - Additional Info: {json.dumps(additional_info, indent=2)}")
    else:
        logger.warning(message)

def log_debug(
    message: str,
    additional_info: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Log a debug message with optional context information
    
    Args:
        message: The main debug message to log
        additional_info: Optional dictionary with additional context
        logger: Logger instance (optional, will use global logger if not provided)
    """
    logger = logger or get_logger()
    if additional_info:
        logger.debug(f"{message} - Additional Info: {json.dumps(additional_info, indent=2)}")
    else:
        logger.debug(message) 