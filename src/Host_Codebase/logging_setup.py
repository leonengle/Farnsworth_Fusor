"""
Logging configuration for the Fusor control system.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from config import config

def setup_logging():
    """Set up logging configuration."""
    log_config = config.get_logging_config()
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_config.get("level", "INFO")))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = os.path.join(log_dir, log_config.get("file", "fusor.log"))
    max_bytes = log_config.get("max_size_mb", 10) * 1024 * 1024
    backup_count = log_config.get("backup_count", 5)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_log_file = os.path.join(log_dir, "fusor_errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # Create session log
    session_log_file = os.path.join(log_dir, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    session_handler = logging.FileHandler(session_log_file)
    session_handler.setLevel(logging.DEBUG)
    session_handler.setFormatter(formatter)
    root_logger.addHandler(session_handler)
    
    logger = logging.getLogger("LoggingSetup")
    logger.info("Logging system initialized")
    logger.info(f"Log files: {log_file}, {error_log_file}, {session_log_file}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
