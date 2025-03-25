# database.py
import sqlite3
import os
import threading
from datetime import datetime
import sys
import bcrypt
import json
from utils.serial_utils import generate_serial_number
from utils.config import get_logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "guth_pump_registry.db")
BOM_PATH = os.path.join(BASE_DIR, "assets", "bom.json")
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
        try:
            # Drop and recreate pumps table with updated schema
            cursor.execute("DROP TABLE IF EXISTS pumps")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pumps (
                    serial_number TEXT PRIMARY KEY,
                    pump_model TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    customer TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('Stores', 'Assembler', 'Testing', 'Pending Approval', 'Completed')),
                    created_at DATETIME NOT NULL,
                    requested_by TEXT NOT NULL,
                    originator TEXT,  -- Added to store the tester who submitted the pump
                    test_data TEXT,  -- Added to store test details as JSON
                    invoice_number TEXT,
                    job_number_1 TEXT,
                    job_number_2 TEXT,
                    test_result TEXT CHECK(test_result IN ('Pass', 'Fail')),
                    test_comments TEXT,
                    motor_voltage TEXT,
                    motor_speed TEXT,
                    mechanical_seal TEXT,
                    test_date DATE,
                    branch TEXT NOT NULL,
                    impeller_size TEXT NOT NULL,
                    connection_type TEXT NOT NULL,
                    pressure_required REAL NOT NULL,  -- Changed to REAL and made NOT NULL
                    flow_rate_required REAL NOT NULL,  -- Changed to REAL and made NOT NULL
                    custom_motor TEXT,
                    flush_seal_housing TEXT
                )
            """)
            print("Pumps table created with updated schema.")
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
            print("BOM items table created.")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('Admin', 'Stores', 'Assembler', 'Testing', 'Pump Originator', 'Approval')),
                    name TEXT,
                    surname TEXT,
                    email TEXT
                )
            """)
            print("Users table created.")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL
                )
            """)
            print("Audit log table created.")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS serial_counter (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_code TEXT NOT NULL,
                    config_code TEXT NOT NULL,
                    sequence INTEGER NOT NULL DEFAULT 0,
                    year TEXT NOT NULL
                )
            """)
            print("Serial counter table created.")
            conn.commit()
            print("Database schema committed.")
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
            raise

def insert_user(cursor, username, password, role, name=None, surname=None, email=None):
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute("""
        INSERT INTO users (username, password_hash, role, name, surname, email)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, password_hash, role, name, surname, email))
    logger.info(f"User inserted: {username} with role {role}")

def update_user(cursor, username, password=None, role=None, name=None, surname=None, email=None):
    if password:
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    else:
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        password_hash = cursor.fetchone()["password_hash"]
    
    cursor.execute("""
        UPDATE users 
        SET password_hash = ?, role = ?, name = ?, surname = ?, email = ?
        WHERE username = ?
    """, (password_hash, role or "Pump Originator", name, surname, email, username))
    logger.info(f"User updated: {username}")

def delete_user(cursor, username):
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    logger.info(f"User deleted: {username}")

def get_all_users(cursor):
    cursor.execute("SELECT username, role, name, surname, email FROM users")
    return cursor.fetchall()

def get_all_pumps(cursor):
    cursor.execute("""
        SELECT serial_number, pump_model, customer, status, test_result, test_date, 
               branch, impeller_size, connection_type, pressure_required, flow_rate_required, 
               custom_motor, flush_seal_housing 
        FROM pumps
    """)
    return cursor.fetchall()

def get_audit_log(cursor):
    cursor.execute("SELECT timestamp, username, action FROM audit_log ORDER BY timestamp DESC")
    return cursor.fetchall()

def check_user(cursor, username, password):
    cursor.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user and bcrypt.checkpw(password.encode('utf-8'), user["password_hash"]):
        return user["role"]
    return None

def get_user_email(cursor, username):
    cursor.execute("SELECT email FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    return user["email"] if user else None

def load_bom_from_json(pump_model, configuration):
    try:
        with open(BOM_PATH, "r") as f:
            bom_data = json.load(f)
            return bom_data.get(pump_model, {}).get(configuration, [])
    except FileNotFoundError:
        logger.error(f"bom.json not found at {BOM_PATH}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in bom.json")
        return []
    except Exception as e:
        logger.error(f"Error loading BOM from JSON: {str(e)}")
        return []

def create_pump(cursor, pump_model, configuration, customer, requested_by, branch="Main", impeller_size="Medium", 
                connection_type="Flange", pressure_required=0.0, flow_rate_required=0.0, custom_motor="", 
                flush_seal_housing="No", insert_bom=True):
    # Validate that pressure_required and flow_rate_required are provided
    if pressure_required is None or flow_rate_required is None:
        raise ValueError("Pressure required and flow rate required are mandatory fields.")
    
    serial = generate_serial_number(pump_model, configuration, cursor)
    cursor.execute("""
        INSERT INTO pumps (serial_number, pump_model, configuration, customer, status, created_at, requested_by,
                          branch, impeller_size, connection_type, pressure_required, flow_rate_required, 
                          custom_motor, flush_seal_housing)
        VALUES (?, ?, ?, ?, 'Stores', ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (serial, pump_model, configuration, customer, datetime.now(), requested_by, branch, impeller_size, 
          connection_type, float(pressure_required), float(flow_rate_required), custom_motor, flush_seal_housing))
    
    if insert_bom:
        bom_items = load_bom_from_json(pump_model, configuration)
        for item in bom_items:
            create_bom_item(cursor, serial, item["part_name"], item["part_code"], item["quantity"])
        logger.info(f"Inserted {len(bom_items)} BOM items for pump {serial}")

    log_action(cursor, requested_by, f"Created pump S/N: {serial}")
    logger.info(f"Pump created: {serial} by {requested_by}")
    return serial

def update_pump_status(cursor, serial_number, new_status, username):
    cursor.execute("UPDATE pumps SET status = ? WHERE serial_number = ?", (new_status, serial_number))
    log_action(cursor, username, f"Updated S/N: {serial_number} to {new_status}")
    logger.info(f"Status updated: {serial_number} to {new_status} by {username}")

def update_test_data(cursor, serial_number, test_data, username):
    # Store test data as JSON and set status to 'Pending Approval'
    cursor.execute("""
        UPDATE pumps 
        SET test_data = ?, status = 'Pending Approval', originator = ?
        WHERE serial_number = ?
    """, (json.dumps(test_data), username, serial_number))
    log_action(cursor, username, f"Submitted test data for S/N: {serial_number}")
    logger.info(f"Test data submitted for {serial_number} by {username}")

def approve_pump(cursor, serial_number, username):
    # Retrieve test data and update status to 'Completed'
    cursor.execute("SELECT test_data, originator FROM pumps WHERE serial_number = ?", (serial_number,))
    pump = cursor.fetchone()
    if pump and pump["test_data"]:
        test_data = json.loads(pump["test_data"])
        test_data["approved_by"] = username
        test_data["approval_date"] = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("UPDATE pumps SET status = 'Completed', test_data = ? WHERE serial_number = ?", 
                      (json.dumps(test_data), serial_number))
        log_action(cursor, username, f"Approved S/N: {serial_number}")
        logger.info(f"Pump {serial_number} approved by {username}")
        return test_data
    return None

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
        ("P1 3.0KW", "Standard", "Guth Pinetown", "user1", "Guth Pinetown", "Medium", "Flange", 2.5, 1000, "", "No"),
        ("P1 3.0KW", "Standard", "Guth Durban", "user1", "Guth Durban", "Small", "Threaded", 3.0, 1200, "", "Yes"),
        ("P1 3.0KW", "Standard", "Guth Cape Town", "user1", "Guth Cape Town", "Large", "Welded", 2.0, 800, "", "No"),
    ]
    test_users = [
        ("user1", "password", "Pump Originator", "John", "Doe", "john.doe@example.com"),
        ("stores1", "password", "Stores", "Jane", "Smith", "jane.smith@example.com"),
        ("assembler1", "password", "Assembler", "Bob", "Jones", "bob.jones@example.com"),
        ("tester1", "password", "Testing", "Alice", "Brown", "alice.brown@example.com"),
        ("approver1", "password", "Approval", "Manager", "Smith", "manager.smith@example.com"),
        ("admin1", "password", "Admin", "Admin", "User", "admin@example.com"),
    ]
    with connect_db() as conn:
        cursor = conn.cursor()
        for username, password, role, name, surname, email in test_users:
            insert_user(cursor, username, password, role, name, surname, email)
        for pump_model, config, customer, user, branch, impeller, conn_type, press, flow, motor, flush in test_pumps:
            serial = create_pump(cursor, pump_model, config, customer, user, branch, impeller, conn_type, press, flow, motor, flush)
            print(f"Inserting pump {serial}...")
        conn.commit()
    print("Test data inserted.")

if __name__ == "__main__":
    try:
        print("Starting database initialization...")
        initialize_database()
        print("Database initialized. Inserting test data...")
        insert_test_data()
        print("Database layer completed with 3 test pumps and 6 test users.")
        sys.stdout.flush()
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.stdout.flush()