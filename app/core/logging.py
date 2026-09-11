import logging
import sys
from pathlib import Path
from loguru import logger
from typing import Dict, List, Union
from pydantic import BaseModel

from app.core.config import get_config


class InterceptHandler(logging.Handler):
    """
    Default handler from examples in loguru documentation.
    See https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # For uvicorn access logs, extract just the message without the request details
        if record.name == "uvicorn.access":
            msg = record.getMessage()
            if '"' in msg and ' - "' in msg and '" ' in msg:
                # Extract just the request part: "GET /path HTTP/1.1" 
                parts = msg.split(' - "', 1)
                if len(parts) > 1:
                    request_part = parts[1]
                    msg = request_part
            logger.opt(depth=depth, exception=record.exc_info).log(level, msg)
        else:
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class LoggingSettings(BaseModel):
    """Settings for logging configuration."""
    LOGGER_NAME: str = "fastapi_app"
    LOG_FORMAT: str = "<level>{level: <8}</level> <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <cyan>{name}</cyan> | <level>{message}</level>"
    LOG_LEVEL: str = get_config().LOG_LEVEL
    
    # Logging config
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: Dict[str, Dict[str, str | None]] = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            "use_colors": None,
        },
    }
    handlers: Dict[str, Dict[str, Union[str, int, Dict[str, str]]]] = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    }
    loggers: Dict[str, Dict[str, Union[str, int, List[str], bool]]] = {
        "uvicorn": {"handlers": ["default"], "level": "INFO"},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    }


def setup_logging():
    """
    Configure logging for the application.
    
    Returns:
        None
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure Loguru
    config = {
        "handlers": [
            {
                "sink": sys.stdout,
                "format": LoggingSettings().LOG_FORMAT,
                "level": LoggingSettings().LOG_LEVEL,
                "enqueue": True,
                "diagnose": True,
            },
            {
                "sink": logs_dir / "app.log",
                "format": LoggingSettings().LOG_FORMAT,
                "level": LoggingSettings().LOG_LEVEL,
                "rotation": "20 MB",
                "compression": "zip",
                "enqueue": True,
                "diagnose": True,
            },
            {
                "sink": logs_dir / "error.log",
                "format": LoggingSettings().LOG_FORMAT,
                "level": "ERROR",
                "rotation": "10 MB",
                "compression": "zip",
                "enqueue": True,
                "diagnose": True,
                "filter": lambda record: record["level"].name == "ERROR"
            },
        ],
    }
    
    # Apply configuration
    logger.configure(**config) #type:ignore
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name in logging.root.manager.loggerDict.keys():
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
    
    # Other libraries that use standard logging
    for _log in [
        "uvicorn", "uvicorn.access", "uvicorn.error", "fastapi",
    ]:
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]
    
    # Return configured logger
    return logger.bind(request_id=None, method=None) 