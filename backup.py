import shutil
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "guth_pump_registry.db")
BACKUP_DIR = os.path.join(BASE_DIR, "data", "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"guth_pump_registry_{timestamp}.db")
    shutil.copy(DB_PATH, backup_path)
    print(f"Backup created at {backup_path}")

if __name__ == "__main__":
    backup_database()
