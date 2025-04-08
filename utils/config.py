import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# Determine the base directory for bundled resources
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    CONFIG_DIR = os.path.join(os.getenv('APPDATA'), "GuthPumpRegistry")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    LOG_DIR = os.path.join(CONFIG_DIR, "logs")
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(LOG_DIR, exist_ok=True)

# Singleton logger setup flag
_LOGGER_INITIALIZED = False

def setup_logging():
    """Set up logging with daily rotation and custom formatting."""
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    log_filename = os.path.join(LOG_DIR, "guth_pump_registry.log")
    handler = TimedRotatingFileHandler(
        filename=log_filename,
        when="midnight",  # Rotate at midnight
        interval=1,       # Every day
        backupCount=30,   # Keep 30 days of logs
        encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)  # Capture all levels, filter at logger level

    # Configure root logger
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)  # Default to DEBUG, can be adjusted
    root_logger.handlers = []  # Clear any existing handlers
    root_logger.addHandler(handler)

    # Add console handler for development (optional)
    if not getattr(sys, 'frozen', False):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)

    _LOGGER_INITIALIZED = True
    root_logger.info(f"Logging initialized to {log_filename}")

def get_logger(name):
    """Get a logger instance with the specified name."""
    if not _LOGGER_INITIALIZED:
        setup_logging()
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Default level, can be overridden
    return logger

if __name__ == "__main__":
    logger = get_logger("test_config")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    print(f"Log file: {os.path.join(LOG_DIR, 'guth_pump_registry.log')}")