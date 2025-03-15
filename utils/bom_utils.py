import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOM_JSON_PATH = os.path.join(BASE_DIR, "data", "bom_items.json")

def generate_bom(serial_number):
    """Generate BOM for a pump from bom_items.json."""
    if not os.path.exists(BOM_JSON_PATH):
        return [{"part_name": "Impeller", "part_code": "IMP-001", "quantity": 1},
                {"part_name": "Motor", "part_code": "MTR-3.0kW", "quantity": 1}]  # Default
    with open(BOM_JSON_PATH, "r") as f:
        bom_data = json.load(f)
    return bom_data.get(serial_number, [])

if __name__ == "__main__":
    print(generate_bom("5101 001 - 25"))
