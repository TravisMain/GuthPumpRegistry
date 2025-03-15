import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from database import connect_db, update_test_data
from utils.config import get_logger

logger = get_logger("testing")

def show_testing_gui(root, username):
    frame = ttk.Frame(root)
    frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
    ttk.Label(frame, text="Testing Dashboard", font=("Helvetica", 16, "bold")).pack(pady=10)

    # Serial Number
    ttk.Label(frame, text="Serial Number:").pack()
    serial_entry = ttk.Entry(frame)
    serial_entry.pack(pady=5)

    # Invoice Number
    ttk.Label(frame, text="Invoice Number:").pack()
    invoice_entry = ttk.Entry(frame)
    invoice_entry.pack(pady=5)

    # Job Numbers
    ttk.Label(frame, text="Job Number 1:").pack()
    job1_entry = ttk.Entry(frame)
    job1_entry.pack(pady=5)
    ttk.Label(frame, text="Job Number 2:").pack()
    job2_entry = ttk.Entry(frame)
    job2_entry.pack(pady=5)

    # Test Result
    ttk.Label(frame, text="Test Result:").pack()
    result_combo = ttk.Combobox(frame, values=["Pass", "Fail"])
    result_combo.pack(pady=5)

    # Comments
    ttk.Label(frame, text="Test Comments:").pack()
    comments_entry = ttk.Entry(frame)
    comments_entry.pack(pady=5)

    # Motor Voltage
    ttk.Label(frame, text="Motor Voltage:").pack()
    voltage_entry = ttk.Entry(frame)
    voltage_entry.pack(pady=5)

    # Motor Speed
    ttk.Label(frame, text="Motor Speed:").pack()
    speed_entry = ttk.Entry(frame)
    speed_entry.pack(pady=5)

    # Mechanical Seal
    ttk.Label(frame, text="Mechanical Seal:").pack()
    seal_entry = ttk.Entry(frame)
    seal_entry.pack(pady=5)

    # Test Date
    ttk.Label(frame, text="Test Date (YYYY-MM-DD):").pack()
    date_entry = ttk.Entry(frame)
    date_entry.pack(pady=5)

    def save_test_data():
        serial = serial_entry.get()
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM pumps WHERE serial_number = ?", (serial,))
            pump = cursor.fetchone()
            if not pump or pump["status"] != "Testing":
                ttk.Label(frame, text="Pump not found or not in Testing status", bootstyle=DANGER).pack(pady=10)
                return
            update_test_data(cursor, serial, invoice_entry.get(), job1_entry.get(), job2_entry.get(),
                            result_combo.get(), comments_entry.get(), voltage_entry.get(), speed_entry.get(),
                            seal_entry.get(), date_entry.get(), username)
            conn.commit()
        ttk.Label(frame, text=f"Test data saved for S/N: {serial}", bootstyle=SUCCESS).pack(pady=10)
        logger.info(f"GUI: Test data saved for {serial} by {username}")

    ttk.Button(frame, text="Save Test Data", command=save_test_data, bootstyle=SUCCESS).pack(pady=20)