import sqlite3
import os

DB_PATH = os.path.join("data", "guth_pump_registry.db")

def initialize_database():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pumps (
            serial_number TEXT PRIMARY KEY,
            pump_model TEXT NOT NULL,
            configuration TEXT NOT NULL,
            customer TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Stores', 'Assembly', 'Testing', 'Completed')),
            created_at DATETIME NOT NULL,
            requested_by TEXT NOT NULL,
            invoice_number TEXT,
            job_number_1 TEXT,
            job_number_2 TEXT,
            test_result TEXT CHECK(test_result IN ('Pass', 'Fail')),
            test_comments TEXT,
            motor_voltage TEXT,
            motor_speed TEXT,
            mechanical_seal TEXT,
            test_date DATE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bom_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_number TEXT,
            part_name TEXT NOT NULL,
            part_code TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            pulled_at DATETIME,
            verified_at DATETIME,
            FOREIGN KEY (serial_number) REFERENCES pumps(serial_number)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Admin', 'Stores', 'Assembler', 'Testing', 'Pump Originator'))
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            username TEXT NOT NULL,
            action TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS serial_counter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_code TEXT NOT NULL,
            config_code TEXT NOT NULL,
            sequence INTEGER NOT NULL DEFAULT 1,
            year TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    initialize_database()