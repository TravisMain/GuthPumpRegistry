import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from database import connect_db, verify_bom_item, update_pump_status

def show_assembler_gui(root, username):
    frame = ttk.Frame(root)
    frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

    ttk.Label(frame, text="Assembler - Verify BOM", font=("Helvetica", 16, "bold")).pack(pady=10)

    ttk.Label(frame, text="Serial Number:").pack()
    serial_entry = ttk.Entry(frame)
    serial_entry.pack(pady=5)

    def verify_and_accept():
        serial = serial_entry.get()
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT part_code FROM bom_items WHERE serial_number = ?", (serial,))
            parts = cursor.fetchall()
            for part in parts:
                verify_bom_item(cursor, serial, part["part_code"], username)
            update_pump_status(cursor, serial, "Testing", username)
            conn.commit()
        ttk.Label(frame, text=f"BOM verified for S/N: {serial}", bootstyle=SUCCESS).pack(pady=10)

    ttk.Button(frame, text="Verify & Accept", command=verify_and_accept, bootstyle=INFO).pack(pady=20)