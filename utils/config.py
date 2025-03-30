import logging
import os
from datetime import datetime

# Define base directory as one level up from this file's location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging with rotation by date
def setup_logging():
    """Set up logging with daily rotation and custom formatting."""
    log_filename = os.path.join(LOG_DIR, f"guth_pump_registry_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Ensure the root logger doesn't propagate to console unless explicitly needed
    logging.getLogger('').handlers[0].propagate = False

# Initialize logging setup
setup_logging()

def get_logger(name):
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)