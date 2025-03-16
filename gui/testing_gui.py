import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from database import connect_db, update_test_data, get_user_email
from utils.doc_utils import generate_certificate, send_email
from utils.config import get_logger

logger = get_logger("testing_gui")

def show_testing_gui(root, username):
    frame = ttk.Frame(root)
    frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

    ttk.Label(frame, text="Pump Testing", font=("Helvetica", 16, "bold")).pack(pady=10)

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT serial_number, pump_model, customer FROM pumps WHERE status = 'Testing'")
        pumps = cursor.fetchall()

    pump_var = ttk.StringVar()
    ttk.Label(frame, text="Select Pump:").pack()
    pump_dropdown = ttk.Combobox(frame, textvariable=pump_var, values=[f"{p['serial_number']} - {p['pump_model']}" for p in pumps])
    pump_dropdown.pack(pady=5)

    invoice_entry = ttk.Entry(frame)
    ttk.Label(frame, text="Invoice Number:").pack()
    invoice_entry.pack(pady=5)

    job1_entry = ttk.Entry(frame)
    ttk.Label(frame, text="Job Number 1:").pack()
    job1_entry.pack(pady=5)

    job2_entry = ttk.Entry(frame)
    ttk.Label(frame, text="Job Number 2:").pack()
    job2_entry.pack(pady=5)

    result_var = ttk.StringVar()
    ttk.Label(frame, text="Test Result:").pack()
    ttk.Radiobutton(frame, text="Pass", variable=result_var, value="Pass").pack(side=LEFT, padx=10)
    ttk.Radiobutton(frame, text="Fail", variable=result_var, value="Fail").pack(side=LEFT, padx=10)

    comments_entry = ttk.Entry(frame)
    ttk.Label(frame, text="Test Comments:").pack()
    comments_entry.pack(pady=5)

    voltage_entry = ttk.Entry(frame)
    ttk.Label(frame, text="Motor Voltage:").pack()
    voltage_entry.pack(pady=5)

    speed_entry = ttk.Entry(frame)
    ttk.Label(frame, text="Motor Speed:").pack()
    speed_entry.pack(pady=5)

    seal_entry = ttk.Entry(frame)
    ttk.Label(frame, text="Mechanical Seal:").pack()
    seal_entry.pack(pady=5)

    date_entry = ttk.Entry(frame)
    ttk.Label(frame, text="Test Date (YYYY-MM-DD):").pack()
    date_entry.pack(pady=5)

    def submit_test():
        serial_number = pump_var.get().split(" - ")[0]
        invoice = invoice_entry.get()
        job1 = job1_entry.get()
        job2 = job2_entry.get()
        result = result_var.get()
        comments = comments_entry.get()
        voltage = voltage_entry.get()
        speed = speed_entry.get()
        seal = seal_entry.get()
        test_date = date_entry.get()

        with connect_db() as conn:
            cursor = conn.cursor()
            update_test_data(cursor, serial_number, invoice, job1, job2, result, comments, voltage, speed, seal, test_date, username)
            conn.commit()
            pump = next(p for p in pumps if p["serial_number"] == serial_number)
            pdf_path = generate_certificate(serial_number, pump["pump_model"], pump["customer"], result, test_date, username)
            email = get_user_email(cursor, username)
            if email:
                success = send_email(email, serial_number, pdf_path)
                if not success:
                    ttk.Label(frame, text=f"Email failed—certificate saved at {pdf_path}", bootstyle=WARNING).pack(pady=10)
            else:
                ttk.Label(frame, text=f"No email for {username}—certificate saved at {pdf_path}", bootstyle=WARNING).pack(pady=10)

        for widget in frame.winfo_children():
            widget.destroy()
        show_testing_gui(root, username)

    ttk.Button(frame, text="Submit", command=submit_test, bootstyle=SUCCESS).pack(pady=20)