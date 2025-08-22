"""
Logging configuration for Jellynouncer.
Provides structured logging with rotation and multiple output levels.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs."""
    
    SENSITIVE_KEYS = [
        'api_key', 'token', 'password', 'secret', 'authorization',
        'webhook_url', 'jwt', 'key', 'auth'
    ]
    
    def filter(self, record):
        """Filter log record to mask sensitive data."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            message = record.msg
            for key in self.SENSITIVE_KEYS:
                if key in message.lower():
                    # Mask sensitive values
                    import re
                    pattern = rf'({key}["\']?\s*[:=]\s*["\']?)([^"\s,}}]+)'
                    message = re.sub(pattern, r'\1***MASKED***', message, flags=re.IGNORECASE)
            record.msg = message
        return True


def setup_logging(log_level: str = "INFO", log_dir: Optional[Path] = None):
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
    """
    if log_dir is None:
        log_dir = Path("logs")
    
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)
    
    # Main log file with rotation
    main_log_file = log_dir / "jellynouncer.log"
    file_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    file_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(file_handler)
    
    # Debug log file (only when debug level is enabled)
    if log_level.upper() == "DEBUG":
        debug_log_file = log_dir / "jellynouncer-debug.log"
        debug_handler = logging.handlers.RotatingFileHandler(
            debug_log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=3,
            encoding='utf-8'
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(debug_handler)
    
    # Error log file
    error_log_file = log_dir / "jellynouncer-error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Set library log levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, Directory: {log_dir}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)