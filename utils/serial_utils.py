import os
import sys
import threading
from datetime import datetime
from utils.config import get_logger

logger = get_logger("serial_utils")

# Determine the base directory for bundled resources
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERIAL_LOCK = threading.Lock()

# Updated serial number mappings per your request
PUMP_MODEL_CODES = {
    "PT 0.55KW": "0",
    "PS 0.75KW": "1",
    "PS 1.1KW": "2",
    "P1 1.1KW": "3",
    "P1 2.2KW": "4",
    "P1 3.0KW": "5",
    "P1 4.0KW": "6",
    "P1 5.5KW": "7",
    "P2 5.5KW": "8",
    "P2 7.5KW": "9"
}

CONFIG_CODES = {
    "Standard": "0",
    "Economical": "1",
}

def generate_serial_number(pump_model, configuration, cursor):
    """Generate a unique serial number in format ABCD EFG - HI where ABCD includes static 01."""
    if pump_model not in PUMP_MODEL_CODES:
        raise ValueError(f"Unknown pump model: {pump_model}")
    if configuration not in CONFIG_CODES:
        raise ValueError(f"Unknown configuration: {configuration}")

    model_code = PUMP_MODEL_CODES[pump_model]
    config_code = CONFIG_CODES[configuration]
    static_c = "0"
    static_d = "1"
    abcd = f"{model_code}{config_code}{static_c}{static_d}"
    year = datetime.now().strftime("%y")

    with SERIAL_LOCK:
        try:
            # Use a single transaction to ensure consistency
            cursor.execute("""
                BEGIN TRANSACTION;
                IF NOT EXISTS (
                    SELECT 1 FROM serial_counter 
                    WHERE model_code = ? AND config_code = ? AND year = ?
                )
                BEGIN
                    INSERT INTO serial_counter (model_code, config_code, sequence, year)
                    VALUES (?, ?, 0, ?)
                END
                
                UPDATE serial_counter 
                SET sequence = sequence + 1
                WHERE model_code = ? AND config_code = ? AND year = ?;
                
                SELECT sequence FROM serial_counter 
                WHERE model_code = ? AND config_code = ? AND year = ?;
                COMMIT TRANSACTION;
            """, (model_code, config_code, year, 
                  model_code, config_code, year, 
                  model_code, config_code, year, 
                  model_code, config_code, year))

            # Fetch the sequence (last query in the batch)
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"No sequence found for {model_code}{config_code} in {year}")
            sequence = row[0]  # Index 0 for 'sequence' column

            if sequence > 999:
                raise ValueError(f"Sequence exceeds 999 for {model_code}{config_code} in {year}")

            serial = f"{abcd} {sequence:03d} - {year}"
            logger.debug(f"Generated serial number: {serial} for {pump_model}/{configuration}")
            return serial
        except pyodbc.Error as e:
            logger.error(f"Database error generating serial number: {str(e)}")
            cursor.execute("ROLLBACK TRANSACTION")  # Rollback on error
            raise
        except Exception as e:
            logger.error(f"Failed to generate serial number: {str(e)}")
            cursor.execute("ROLLBACK TRANSACTION")  # Rollback on error
            raise

if __name__ == "__main__":
    from database import get_db_connection
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            serial = generate_serial_number("P1 3.0KW", "Standard", cursor)
            print(f"Generated serial: {serial}")
            conn.commit()
    except Exception as e:
        print(f"Error: {e}")