import os
from datetime import datetime
from utils.config import get_logger

logger = get_logger("serial_utils")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

    try:
        cursor.execute("""
            IF NOT EXISTS (
                SELECT 1 FROM serial_counter 
                WHERE model_code = ? AND config_code = ? AND year = ?
            )
            BEGIN
                INSERT INTO serial_counter (model_code, config_code, sequence, year)
                VALUES (?, ?, 0, ?)
            END
        """, (model_code, config_code, year, model_code, config_code, year))

        cursor.execute("""
            UPDATE serial_counter 
            SET sequence = sequence + 1
            WHERE model_code = ? AND config_code = ? AND year = ?
            SELECT sequence FROM serial_counter 
            WHERE model_code = ? AND config_code = ? AND year = ?
        """, (model_code, config_code, year, model_code, config_code, year))

        # Fetch the sequence
        cursor.execute("""
            SELECT sequence FROM serial_counter 
            WHERE model_code = ? AND config_code = ? AND year = ?
        """, (model_code, config_code, year))
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"No sequence found for {model_code}{config_code} in {year}")
        sequence = row[0]  # Index 0 for 'sequence' column (tuple access)

        if sequence > 999:
            raise ValueError(f"Sequence exceeds 999 for {model_code}{config_code} in {year}")

        serial = f"{abcd} {sequence:03d} - {year}"
        logger.debug(f"Generated serial number: {serial} for {pump_model}/{configuration}")
        return serial
    except Exception as e:
        logger.error(f"Failed to generate serial number: {str(e)}")
        raise

if __name__ == "__main__":
    from database import get_db_connection
    with get_db_connection() as conn:
        cursor = conn.cursor()
        serial = generate_serial_number("P1 3.0KW", "Standard", cursor)
        print(serial)
        conn.commit()