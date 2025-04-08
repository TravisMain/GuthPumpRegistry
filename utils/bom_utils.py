import json
import os
import sys
from utils.config import get_logger

logger = get_logger("bom_utils")

# Determine the base directory for bundled resources
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    CONFIG_DIR = os.path.join(os.getenv('APPDATA'), "GuthPumpRegistry")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
    DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
    DEFAULT_CONFIG_PATH = CONFIG_PATH

def load_config():
    """Load configuration from config.json, falling back to defaults if missing."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
            logger.debug(f"Loaded config from {CONFIG_PATH}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {CONFIG_PATH}: {str(e)}")
    if os.path.exists(DEFAULT_CONFIG_PATH):
        try:
            with open(DEFAULT_CONFIG_PATH, "r") as f:
                config = json.load(f)
            logger.debug(f"Loaded default config from {DEFAULT_CONFIG_PATH}")
            return config
        except Exception as e:
            logger.error(f"Failed to load default config from {DEFAULT_CONFIG_PATH}: {str(e)}")
    logger.warning(f"No config found at {CONFIG_PATH} or {DEFAULT_CONFIG_PATH}, using defaults")
    return {"bom_path": os.path.join(BASE_DIR, "assets", "bom.json")}

def generate_bom(pump_model, configuration):
    """Generate BOM for a pump based on model and configuration from bom.json."""
    config = load_config()
    bom_path = config.get("bom_path", os.path.join(BASE_DIR, "assets", "bom.json"))
    
    if not os.path.exists(bom_path):
        logger.warning(f"BOM file not found at {bom_path}, returning default BOM")
        return [{"part_name": "Impeller", "part_code": "IMP-001", "quantity": 1},
                {"part_name": "Motor", "part_code": "MTR-3.0kW", "quantity": 1}]
    
    try:
        with open(bom_path, "r") as f:
            bom_data = json.load(f)
            items = bom_data.get(pump_model, {}).get(configuration, [])
            logger.debug(f"Generated BOM for {pump_model}/{configuration}: {items}")
            return items
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Failed to load BOM from {bom_path}: {str(e)}")
        return [{"part_name": "Impeller", "part_code": "IMP-001", "quantity": 1},
                {"part_name": "Motor", "part_code": "MTR-3.0kW", "quantity": 1}]

if __name__ == "__main__":
    print(generate_bom("P1 3.0KW", "Standard"))