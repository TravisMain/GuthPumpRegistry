import pyodbc
import os
import sys
import threading
from datetime import datetime
import json
import bcrypt
from utils.serial_utils import generate_serial_number
from utils.config import get_logger

logger = get_logger("database")

# Determine the base directory for bundled resources
if getattr(sys, 'frozen', False):
    # Running as a bundled executable (PyInstaller)
    BASE_DIR = sys._MEIPASS
else:
    # Running in development mode
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
BOM_PATH = os.path.join(BASE_DIR, "assets", "bom.json")
DB_LOCK = threading.Lock()

# Connection pool (singleton pattern)
_conn_pool = None

def load_config():
    """Load configuration from config.json, raising an error if missing."""
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError("config.json not found. Run installer to set up.")
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def get_db_connection():
    """Get a singleton database connection."""
    global _conn_pool
    try:
        config = load_config()
        conn_str = config.get("connection_string")
        if not conn_str:
            raise ValueError("No connection string found in config.json")
        if _conn_pool is None or _conn_pool.closed:
            with DB_LOCK:
                if _conn_pool is None or _conn_pool.closed:
                    _conn_pool = pyodbc.connect(conn_str)
                    logger.info("Database connection established successfully")
        return _conn_pool
    except pyodbc.Error as e:
        error_msg = f"Failed to connect to the database: {str(e)}"
        logger.error(error_msg)
        if "IM002" in str(e):
            error_msg += "\nThe required ODBC driver is not installed on this PC. Please install 'ODBC Driver 17 for SQL Server' and try again."
        raise Exception(error_msg)
    except Exception as e:
        logger.error(f"Unexpected error while connecting to the database: {str(e)}")
        raise

def initialize_database():
    """Initialize the GuthPumpRegistry tables if they do not exist."""
    config = load_config()
    conn_str = config.get("connection_string")
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("USE GuthPumpRegistry")
            cursor.execute("""
                IF EXISTS (SELECT * FROM sys.tables WHERE name = 'bom_items')
                DROP TABLE bom_items
            """)
            cursor.execute("""
                IF EXISTS (SELECT * FROM sys.tables WHERE name = 'pumps')
                DROP TABLE pumps
            """)
            cursor.execute("""
                IF EXISTS (SELECT * FROM sys.tables WHERE name = 'users')
                DROP TABLE users
            """)
            cursor.execute("""
                IF EXISTS (SELECT * FROM sys.tables WHERE name = 'audit_log')
                DROP TABLE audit_log
            """)
            cursor.execute("""
                IF EXISTS (SELECT * FROM sys.tables WHERE name = 'serial_counter')
                DROP TABLE serial_counter
            """)
            cursor.execute("""
                CREATE TABLE pumps (
                    serial_number NVARCHAR(50) PRIMARY KEY,
                    pump_model NVARCHAR(50) NOT NULL,
                    configuration NVARCHAR(50) NOT NULL,
                    customer NVARCHAR(50) NOT NULL,
                    status NVARCHAR(20) NOT NULL CHECK(status IN ('Stores', 'Assembler', 'Testing', 'Pending Approval', 'Completed')),
                    created_at DATETIME NOT NULL,
                    requested_by NVARCHAR(50) NOT NULL,
                    originator NVARCHAR(50),
                    test_data NVARCHAR(MAX),
                    invoice_number NVARCHAR(50),
                    job_number_1 NVARCHAR(50),
                    job_number_2 NVARCHAR(50),
                    test_result NVARCHAR(10) CHECK(test_result IN ('Pass', 'Fail')),
                    test_comments NVARCHAR(MAX),
                    motor_voltage NVARCHAR(20),
                    motor_speed NVARCHAR(20),
                    mechanical_seal NVARCHAR(50),
                    test_date DATE,
                    branch NVARCHAR(50) NOT NULL,
                    impeller_size NVARCHAR(50) NOT NULL,
                    connection_type NVARCHAR(50) NOT NULL,
                    pressure_required FLOAT NOT NULL,
                    flow_rate_required FLOAT NOT NULL,
                    custom_motor NVARCHAR(50),
                    flush_seal_housing NVARCHAR(10),
                    assembly_part_number NVARCHAR(50)
                )
            """)
            cursor.execute("""
                CREATE TABLE bom_items (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    serial_number NVARCHAR(50),
                    part_name NVARCHAR(100) NOT NULL,
                    part_code NVARCHAR(50) NOT NULL,
                    quantity INT NOT NULL,
                    pulled_at DATETIME,
                    verified_at DATETIME,
                    FOREIGN KEY (serial_number) REFERENCES pumps(serial_number) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                CREATE TABLE users (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    username NVARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARBINARY(255) NOT NULL,
                    role NVARCHAR(20) NOT NULL CHECK(role IN ('Admin', 'Stores', 'Assembler_Tester', 'Pump Originator', 'Approval')),
                    name NVARCHAR(50),
                    surname NVARCHAR(50),
                    email NVARCHAR(100)
                )
            """)
            cursor.execute("""
                CREATE TABLE audit_log (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    timestamp DATETIME NOT NULL,
                    username NVARCHAR(50) NOT NULL,
                    action NVARCHAR(MAX) NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE serial_counter (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    model_code NVARCHAR(50) NOT NULL,
                    config_code NVARCHAR(50) NOT NULL,
                    sequence INT NOT NULL DEFAULT 0,
                    year NVARCHAR(4) NOT NULL
                )
            """)
            cursor.execute("IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_pumps_status') CREATE INDEX idx_pumps_status ON pumps(status)")
            cursor.execute("IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_bom_items_serial') CREATE INDEX idx_bom_items_serial ON bom_items(serial_number)")
            conn.commit()
            logger.info("Database tables initialized.")
    except pyodbc.Error as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def hash_password(password):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def insert_user(cursor, username, password, role, name=None, surname=None, email=None):
    """Insert a new user with hashed password."""
    try:
        password_hash = hash_password(password)
        cursor.execute("INSERT INTO users (username, password_hash, role, name, surname, email) VALUES (?, ?, ?, ?, ?, ?)",
                       (username, password_hash, role, name, surname, email))
        logger.info(f"User inserted: {username} with role {role}")
    except pyodbc.IntegrityError:
        logger.info(f"User {username} already exists, skipping insertion")

def check_user(cursor, username, password):
    """Verify user credentials and return role if valid."""
    cursor.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user:
        # password_hash (index 0) is bytes from VARBINARY, no encoding needed
        if bcrypt.checkpw(password.encode('utf-8'), user[0]):
            return user[1]  # Index 1 = role
    return None

def create_pump(cursor, pump_model, configuration, customer, requested_by, branch="Main", impeller_size="Medium",
                connection_type="Flange", pressure_required=0.0, flow_rate_required=0.0, custom_motor="",
                flush_seal_housing="No", assembly_part_number=None, insert_bom=True):
    """Create a new pump record and optionally insert BOM items."""
    if pressure_required is None or flow_rate_required is None:
        raise ValueError("Pressure and flow rate are mandatory.")
    serial = generate_serial_number(pump_model, configuration, cursor)
    cursor.execute("""
        INSERT INTO pumps (serial_number, pump_model, configuration, customer, status, created_at, requested_by,
                          branch, impeller_size, connection_type, pressure_required, flow_rate_required,
                          custom_motor, flush_seal_housing, assembly_part_number)
        VALUES (?, ?, ?, ?, 'Stores', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (serial, pump_model, configuration, customer, datetime.now(), requested_by, branch, impeller_size,
          connection_type, float(pressure_required), float(flow_rate_required), custom_motor, flush_seal_housing,
          assembly_part_number))
    
    if insert_bom:
        bom_items = load_bom_from_json(pump_model, configuration)
        for item in bom_items:
            cursor.execute("INSERT INTO bom_items (serial_number, part_name, part_code, quantity) VALUES (?, ?, ?, ?)",
                           (serial, item["part_name"], item["part_code"], item["quantity"]))
        logger.info(f"Inserted {len(bom_items)} BOM items for pump {serial}")

    cursor.execute("INSERT INTO audit_log (timestamp, username, action) VALUES (?, ?, ?)",
                   (datetime.now(), requested_by, f"Created pump S/N: {serial}"))
    return serial

def pull_bom_item(cursor, serial_number, part_code, username):
    """Mark a BOM item as pulled and log the action."""
    cursor.execute("UPDATE bom_items SET pulled_at = ? WHERE serial_number = ? AND part_code = ?",
                   (datetime.now(), serial_number, part_code))
    cursor.execute("INSERT INTO audit_log (timestamp, username, action) VALUES (?, ?, ?)",
                   (datetime.now(), username, f"Pulled part {part_code} for S/N: {serial_number}"))

def update_pump_status(cursor, serial_number, new_status, username):
    """Update the status of a pump and log the action."""
    cursor.execute("UPDATE pumps SET status = ? WHERE serial_number = ?", (new_status, serial_number))
    cursor.execute("INSERT INTO audit_log (timestamp, username, action) VALUES (?, ?, ?)",
                   (datetime.now(), username, f"Updated S/N: {serial_number} to {new_status}"))
    logger.info(f"Status updated: {serial_number} to {new_status} by {username}")

def load_bom_from_json(pump_model, configuration):
    """Load BOM items from JSON file."""
    try:
        with open(BOM_PATH, "r") as f:
            bom_data = json.load(f)
            return bom_data.get(pump_model, {}).get(configuration, [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load BOM from JSON: {str(e)}")
        return []

def insert_test_data():
    """Insert initial test data into the database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            test_users = [
                ("user1", "password", "Pump Originator", "John", "Doe", "john.doe@guth.co.za"),
                ("stores1", "password", "Stores", "Jane", "Smith", "jane.smith@guth.co.za"),
                ("assembler_tester1", "password", "Assembler_Tester", "Alex", "Taylor", "alex.taylor@guth.co.za"),
                ("approver1", "password", "Approval", "Manager", "Smith", "manager.smith@guth.co.za"),
                ("admin1", "password", "Admin", "Admin", "User", "admin@guth.co.za"),
            ]
            for user in test_users:
                insert_user(cursor, *user)
            test_pumps = [
                ("P1 3.0KW", "Standard", "Guth Pinetown", "user1", "Guth Pinetown", "Medium", "Flange", 2.5, 1000, "", "No", "APN-001"),
                ("P1 3.0KW", "Standard", "Guth Durban", "user1", "Guth Durban", "Small", "Threaded", 3.0, 1200, "", "Yes", "APN-002"),
                ("P1 3.0KW", "Standard", "Guth Cape Town", "user1", "Guth Cape Town", "Large", "Welded", 2.0, 800, "", "No", "APN-003"),
            ]
            for pump in test_pumps:
                create_pump(cursor, *pump)
            conn.commit()
            logger.info("Test data inserted successfully.")
    except Exception as e:
        logger.error(f"Failed to insert test data: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        initialize_database()
        insert_test_data()
    except Exception as e:
        print(f"Initialization failed: {e}")
        print("Please ensure the GuthPumpRegistry database exists on the server or contact your database administrator.")
        input("Press any key to continue . . .")