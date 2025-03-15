import sqlite3
import os
import threading
from datetime import datetime
import sys

DB_PATH = os.path.join("data", "guth_pump_registry.db")
DB_LOCK = threading.Lock()

def connect_db(timeout=20):
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    print("Initializing database...")
    os.makedirs("data", exist_ok=True)
    with DB_LOCK, connect_db() as conn:
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
    print("Tables created.")

def create_pump(serial_number, pump_model, configuration, customer, requested_by):
    with DB_LOCK, connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pumps (serial_number, pump_model, configuration, customer, status, created_at, requested_by)
            VALUES (?, ?, ?, ?, 'Stores', ?, ?)
        """, (serial_number, pump_model, configuration, customer, datetime.now(), requested_by))
        log_action(cursor, requested_by, f"Created pump S/N: {serial_number}")
        conn.commit()

def create_bom_item(cursor, serial_number, part_name, part_code, quantity):
    cursor.execute("""
        INSERT INTO bom_items (serial_number, part_name, part_code, quantity)
        VALUES (?, ?, ?, ?)
    """, (serial_number, part_name, part_code, quantity))

def log_action(cursor, username, action):
    cursor.execute("""
        INSERT INTO audit_log (timestamp, username, action)
        VALUES (?, ?, ?)
    """, (datetime.now(), username, action))

def update_serial_counter(model_code, config_code, year):
    with DB_LOCK, connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO serial_counter (model_code, config_code, sequence, year)
            VALUES (?, ?, 1, ?)
        """, (model_code, config_code, year))
        cursor.execute("""
            UPDATE serial_counter SET sequence = sequence + 1
            WHERE model_code = ? AND config_code = ? AND year = ?
        """, (model_code, config_code, year))
        cursor.execute("""
            SELECT sequence FROM serial_counter
            WHERE model_code = ? AND config_code = ? AND year = ?
        """, (model_code, config_code, year))
        sequence = cursor.fetchone()["sequence"]
        conn.commit()
        return sequence

def insert_test_data():
    print("Inserting test data...")
    test_pumps = [
        ("5101 001 - 25", "P1 3.0kW", "Standard", "Guth Pinetown", "user1"),
        ("5101 002 - 25", "P1 3.0kW", "Standard", "Guth Durban", "user1"),
        ("5101 003 - 25", "P1 3.0kW", "Standard", "Guth Cape Town", "user1"),
        ("5101 004 - 25", "P1 3.0kW", "Standard", "Guth Pretoria", "user1"),
        ("5101 005 - 25", "P1 3.0kW", "Standard", "Guth Johannesburg", "user1"),
    ]
    with connect_db() as conn:
        cursor = conn.cursor()
        for serial, model, config, customer, user in test_pumps:
            print(f"Inserting pump {serial}...")
            cursor.execute("""
                INSERT OR IGNORE INTO pumps (serial_number, pump_model, configuration, customer, status, created_at, requested_by)
                VALUES (?, ?, ?, ?, 'Stores', ?, ?)
            """, (serial, model, config, customer, datetime.now(), user))
            print(f"Pump {serial} inserted into pumps table.")
            log_action(cursor, user, f"Created pump S/N: {serial}")
            print(f"Logged action for {serial}.")
            print(f"Inserting BOM for {serial} - Impeller...")
            create_bom_item(cursor, serial, "Impeller", "IMP-001", 1)
            print(f"Inserting BOM for {serial} - Motor...")
            create_bom_item(cursor, serial, "Motor", "MTR-3.0kW", 1)
        print("Updating serial_counter...")
        cursor.execute("""
            INSERT OR REPLACE INTO serial_counter (id, model_code, config_code, sequence, year)
            VALUES (1, '5', '1', 5, '25')
        """)
        conn.commit()
    print("Test data inserted.")

if __name__ == "__main__":
    try:
        print("Starting database initialization...")
        initialize_database()
        print("Database initialized. Inserting test data...")
        insert_test_data()
        print("Database layer completed with 5 test pumps.")
        sys.stdout.flush()
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.stdout.flush()