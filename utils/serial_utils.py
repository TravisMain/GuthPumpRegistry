import os
from datetime import datetime
import sqlite3

# Absolute path from project root (up one level from utils/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "guth_pump_registry.db")

# Serial number mappings (SOW Appendix A draft)
PUMP_MODEL_CODES = {
    "P1 3.0kW": "5",
    "PT 0.55kW": "1"
}

CONFIG_CODES = {
    "Standard": "1",
    "Economical": "2"
}

def connect_db(timeout=20):
    """Connect to the database."""
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    return conn

def generate_serial_number(pump_model, configuration, cursor):
    """Generate a unique serial number in format S/N: ABCD EFG - HI using an existing cursor."""
    if pump_model not in PUMP_MODEL_CODES:
        raise ValueError(f"Unknown pump model: {pump_model}")
    if configuration not in CONFIG_CODES:
        raise ValueError(f"Unknown configuration: {configuration}")

    model_code = PUMP_MODEL_CODES[pump_model]
    config_code = CONFIG_CODES[configuration]
    year = datetime.now().strftime("%y")  # e.g., "25" for 2025

    # Ensure a row exists for this model/config/year
    cursor.execute("""
        INSERT OR IGNORE INTO serial_counter (model_code, config_code, sequence, year)
        VALUES (?, ?, 0, ?)
    """, (model_code, config_code, year))
    # Increment sequence
    cursor.execute("""
        UPDATE serial_counter SET sequence = sequence + 1
        WHERE model_code = ? AND config_code = ? AND year = ?
    """, (model_code, config_code, year))
    # Get the new sequence
    cursor.execute("""
        SELECT sequence FROM serial_counter
        WHERE model_code = ? AND config_code = ? AND year = ?
    """, (model_code, config_code, year))
    sequence = cursor.fetchone()["sequence"]
    if sequence > 999:
        raise ValueError(f"Sequence exceeds 999 for {model_code}{config_code} in {year}")

    # Format: ABCD (model + config), EFG (sequence), HI (year)
    serial = f"{model_code}{config_code} {sequence:03d} - {year}"
    return serial

if __name__ == "__main__":
    with connect_db() as conn:
        cursor = conn.cursor()
        print(generate_serial_number("P1 3.0kW", "Standard", cursor))  # e.g., "51 001 - 25"
        conn.commit()