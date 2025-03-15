import sqlite3
import os
import threading
from datetime import datetime
import sys
from utils.serial_utils import generate_serial_number
from utils.config import get_logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "guth_pump_registry.db")
DB_LOCK = threading.Lock()
logger = get_logger("database")

def connect_db(timeout=20):
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    print("Initializing database...")
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
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
                sequence INTEGER NOT NULL DEFAULT 0,
                year TEXT NOT NULL
            )
        """)
        conn.commit()
    print("Tables created.")

def create_pump(cursor, pump_model, configuration, customer, requested_by):
    serial = generate_serial_number(pump_model, configuration, cursor)
    cursor.execute("""
        INSERT INTO pumps (serial_number, pump_model, configuration, customer, status, created_at, requested_by)
        VALUES (?, ?, ?, ?, 'Stores', ?, ?)
    """, (serial, pump_model, configuration, customer, datetime.now(), requested_by))
    log_action(cursor, requested_by, f"Created pump S/N: {serial}")
    logger.info(f"Pump created: {serial} by {requested_by}")
    return serial

def update_pump_status(cursor, serial_number, new_status, username):
    cursor.execute("UPDATE pumps SET status = ? WHERE serial_number = ?", (new_status, serial_number))
    log_action(cursor, username, f"Updated S/N: {serial_number} to {new_status}")
    logger.info(f"Status updated: {serial_number} to {new_status} by {username}")

def pull_bom_item(cursor, serial_number, part_code, username):
    cursor.execute("UPDATE bom_items SET pulled_at = ? WHERE serial_number = ? AND part_code = ?",
                   (datetime.now(), serial_number, part_code))
    log_action(cursor, username, f"Pulled part {part_code} for S/N: {serial_number}")
    logger.info(f"Part pulled: {part_code} for {serial_number} by {username}")

def verify_bom_item(cursor, serial_number, part_code, username):
    cursor.execute("UPDATE bom_items SET verified_at = ? WHERE serial_number = ? AND part_code = ?",
                   (datetime.now(), serial_number, part_code))
    log_action(cursor, username, f"Verified part {part_code} for S/N: {serial_number}")
    logger.info(f"Part verified: {part_code} for {serial_number} by {username}")

def log_action(cursor, username, action):
    cursor.execute("""
        INSERT INTO audit_log (timestamp, username, action)
        VALUES (?, ?, ?)
    """, (datetime.now(), username, action))

def create_bom_item(cursor, serial_number, part_name, part_code, quantity):
    cursor.execute("""
        INSERT INTO bom_items (serial_number, part_name, part_code, quantity)
        VALUES (?, ?, ?, ?)
    """, (serial_number, part_name, part_code, quantity))

def insert_test_data():
    print("Inserting test data...")
    test_pumps = [
        ("P1 3.0kW", "Standard", "Guth Pinetown", "user1"),
        ("P1 3.0kW", "Standard", "Guth Durban", "user1"),
        ("P1 3.0kW", "Standard", "Guth Cape Town", "user1"),
    ]
    with connect_db() as conn:
        cursor = conn.cursor()
        for pump_model, config, customer, user in test_pumps:
            serial = create_pump(cursor, pump_model, config, customer, user)
            print(f"Inserting pump {serial}...")
            print(f"Inserting BOM for {serial} - Impeller...")
            create_bom_item(cursor, serial, "Impeller", "IMP-001", 1)
            print(f"Inserting BOM for {serial} - Motor...")
            create_bom_item(cursor, serial, "Motor", "MTR-3.0kW", 1)
        conn.commit()
    print("Test data inserted.")

if __name__ == "__main__":
    try:
        print("Starting database initialization...")
        initialize_database()
        print("Database initialized. Inserting test data...")
        insert_test_data()
        print("Database layer completed with 3 test pumps.")
        sys.stdout.flush()
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.stdout.flush()