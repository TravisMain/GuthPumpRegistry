import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from database import connect_db, create_pump, create_bom_item
from utils.config import get_logger

logger = get_logger("pump_originator")

def show_pump_originator_gui(root, username):
    frame = ttk.Frame(root)
    frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
    ttk.Label(frame, text="Create New Pump", font=("Helvetica", 16, "bold")).pack(pady=10)

    ttk.Label(frame, text="Pump Model:").pack()
    model_entry = ttk.Entry(frame)
    model_entry.insert(0, "P1 3.0kW")
    model_entry.pack(pady=5)

    ttk.Label(frame, text="Configuration:").pack()
    config_entry = ttk.Entry(frame)
    config_entry.insert(0, "Standard")
    config_entry.pack(pady=5)

    ttk.Label(frame, text="Customer:").pack()
    customer_entry = ttk.Entry(frame)
    customer_entry.insert(0, "Guth Test")
    customer_entry.pack(pady=5)

    def create():
        with connect_db() as conn:
            cursor = conn.cursor()
            serial = create_pump(cursor, model_entry.get(), config_entry.get(), customer_entry.get(), username)
            create_bom_item(cursor, serial, "Impeller", "IMP-001", 1)
            create_bom_item(cursor, serial, "Motor", "MTR-3.0kW", 1)
            conn.commit()
        ttk.Label(frame, text=f"Created S/N: {serial}", bootstyle=SUCCESS).pack(pady=10)
        logger.info(f"GUI: Pump {serial} created by {username}")

    ttk.Button(frame, text="Create Pump", command=create, bootstyle=SUCCESS).pack(pady=20)