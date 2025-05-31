"""
Logging configuration for IntelliStore API
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.stdlib import LoggerFactory


def setup_logging(log_level: str = "INFO") -> None:
    """Setup structured logging with structlog"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level and timestamp
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # JSON formatting for production
            structlog.processors.JSONRenderer() if log_level != "DEBUG" 
            else structlog.dev.ConsoleRenderer(colors=True)
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class StructlogHandler(logging.Handler):
    """Custom logging handler that forwards to structlog"""
    
    def __init__(self, logger_name: str = "uvicorn"):
        super().__init__()
        self.logger = structlog.get_logger(logger_name)
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record using structlog"""
        try:
            level = record.levelname.lower()
            message = record.getMessage()
            
            # Extract extra fields
            extra_fields = {
                key: value for key, value in record.__dict__.items()
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info'
                }
            }
            
            # Log with appropriate level
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(message, **extra_fields)
            
        except Exception:
            self.handleError(record)


def configure_uvicorn_logging() -> None:
    """Configure uvicorn to use structlog"""
    
    # Get uvicorn loggers
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    
    # Clear existing handlers
    uvicorn_logger.handlers.clear()
    uvicorn_access_logger.handlers.clear()
    
    # Add structlog handlers
    uvicorn_logger.addHandler(StructlogHandler("uvicorn"))
    uvicorn_access_logger.addHandler(StructlogHandler("uvicorn.access"))
    
    # Set levels
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_access_logger.setLevel(logging.INFO)


class RequestLoggingMiddleware:
    """Middleware for logging HTTP requests"""
    
    def __init__(self, app):
        self.app = app
        self.logger = structlog.get_logger("api.requests")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract request info
        method = scope["method"]
        path = scope["path"]
        query_string = scope.get("query_string", b"").decode()
        headers = dict(scope.get("headers", []))
        
        # Start timing
        import time
        start_time = time.time()
        
        # Process request
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Log response
                status_code = message["status"]
                duration = time.time() - start_time
                
                self.logger.info(
                    "HTTP request completed",
                    method=method,
                    path=path,
                    query_string=query_string,
                    status_code=status_code,
                    duration=duration,
                    user_agent=headers.get(b"user-agent", b"").decode(),
                )
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)