import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
from database import connect_db
import os
from datetime import datetime
from utils.config import get_logger
import json

logger = get_logger("testing_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
BUILD_NUMBER = "1.0.0"

def show_testing_dashboard(root, username, role, logout_callback):
    for widget in root.winfo_children():
        widget.destroy()

    root.state('zoomed')
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    header_frame = ttk.Frame(main_frame, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20), ipady=20)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH)
            img_resized = img.resize((int(img.width * 0.75), int(img.height * 0.75)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            logo_label = ttk.Label(header_frame, image=logo)
            logo_label.image = logo
            logo_label.pack(side=RIGHT, padx=10)
        except Exception as e:
            logger.error(f"Testing logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="View and manage pumps in Testing status.", font=("Roboto", 12)).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Testing Pump Inventory", font=("Roboto", 16, "bold")).pack(pady=10)

    pump_list_frame = ttk.LabelFrame(main_frame, text="Pumps in Testing", padding=10)
    pump_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration")
    tree = ttk.Treeview(pump_list_frame, columns=columns, show="headings", height=15)
    for col in columns:
        tree.heading(col, text=col, anchor=W)
        tree.column(col, width=150, anchor=W)
    tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar = ttk.Scrollbar(pump_list_frame, orient=VERTICAL, command=tree.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    tree.configure(yscrollcommand=scrollbar.set)

    def refresh_pump_list():
        for item in tree.get_children():
            tree.delete(item)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT serial_number, customer, branch, pump_model, configuration
                FROM pumps WHERE status = 'Testing'
            """)
            for pump in cursor.fetchall():
                tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"],
                                            pump["pump_model"], pump["configuration"]))

    refresh_pump_list()
    tree.bind("<Double-1>", lambda event: show_test_report(main_frame, tree, username, refresh_pump_list))

    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=10)
    ttk.Button(footer_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

def show_test_report(parent_frame, tree, username, refresh_callback):
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    serial_number = tree.item(selected[0])["values"][0]
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT customer, pump_model, configuration FROM pumps WHERE serial_number = ?", (serial_number,))
        pump = cursor.fetchone()
        if not pump:
            logger.warning(f"No pump found for serial_number: {serial_number}")
            return

    test_window = ttk.Toplevel(parent_frame)
    test_window.title(f"Test Report for Pump {serial_number}")
    test_window.state("zoomed")

    header_frame = ttk.Frame(test_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH)
            img_resized = img.resize((int(img.width * 0.5), int(img.height * 0.5)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            logo_label = ttk.Label(header_frame, image=logo)
            logo_label.image = logo
            logo_label.pack(side=RIGHT, padx=10)
        except Exception as e:
            logger.error(f"Test report logo load failed: {str(e)}")
    ttk.Label(header_frame, text="Pump Test Report", font=("Roboto", 14, "bold")).pack(anchor=W, padx=10)

    canvas = ttk.Canvas(test_window)
    scrollbar = ttk.Scrollbar(test_window, orient=VERTICAL, command=canvas.yview)
    main_frame = ttk.Frame(canvas)

    main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=main_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)
    scrollbar.pack(side=RIGHT, fill=Y)

    def on_mouse_wheel(event):
        canvas.yview_scroll(-1 * (event.delta // 120), "units")
    canvas.bind_all("<MouseWheel>", on_mouse_wheel)

    top_frame = ttk.Frame(main_frame)
    top_frame.grid(row=0, column=0, pady=(0, 15), sticky=W)

    ttk.Label(top_frame, text="Invoice Number:", font=("Roboto", 10)).grid(row=0, column=0, padx=10, pady=2, sticky=W)
    invoice_entry = ttk.Entry(top_frame, width=30)
    invoice_entry.grid(row=0, column=1, padx=10, pady=2, sticky=W)

    ttk.Label(top_frame, text="Customer:", font=("Roboto", 10)).grid(row=1, column=0, padx=10, pady=2, sticky=W)
    ttk.Label(top_frame, text=pump["customer"], font=("Roboto", 10)).grid(row=1, column=1, padx=10, pady=2, sticky=W)

    ttk.Label(top_frame, text="Job Number:", font=("Roboto", 10)).grid(row=2, column=0, padx=10, pady=2, sticky=W)
    job_entry = ttk.Entry(top_frame, width=30)
    job_entry.grid(row=2, column=1, padx=10, pady=2, sticky=W)

    main_layout = ttk.Frame(main_frame)
    main_layout.grid(row=1, column=0, pady=15, sticky=W+E)

    left_frame = ttk.Frame(main_layout)
    left_frame.pack(side=LEFT, padx=15, fill=Y)

    fab_frame = ttk.LabelFrame(left_frame, text="Fabrication", padding=10, labelwidget=ttk.Label(left_frame, text="Fabrication", font=("Roboto", 12, "bold")))
    fab_frame.pack(pady=(0, 10), fill=X)

    ttk.Label(fab_frame, text="Pump Model:", font=("Roboto", 10)).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=pump["pump_model"], font=("Roboto", 10)).grid(row=0, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Serial Number:", font=("Roboto", 10)).grid(row=1, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=serial_number, font=("Roboto", 10)).grid(row=1, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Impeller Diameter:", font=("Roboto", 10)).grid(row=2, column=0, padx=5, pady=5, sticky=W)
    impeller_entry = ttk.Entry(fab_frame, width=20)
    impeller_entry.grid(row=2, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Assembled By:", font=("Roboto", 10)).grid(row=3, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=username, font=("Roboto", 10)).grid(row=3, column=1, padx=5, pady=5, sticky=W)

    details_frame = ttk.LabelFrame(left_frame, text="Details", padding=10, labelwidget=ttk.Label(left_frame, text="Details", font=("Roboto", 12, "bold")))
    details_frame.pack(fill=X)

    fields_left = [
        ("Motor Size:", ttk.Entry(details_frame, width=20)),
        ("Motor Speed:", ttk.Entry(details_frame, width=20)),
        ("Motor Volts:", ttk.Entry(details_frame, width=20)),
        ("Motor Enclosure:", ttk.Entry(details_frame, width=20)),
        ("Mechanical Seal:", ttk.Entry(details_frame, width=20)),
    ]
    fields_right = [
        ("Frequency:", ttk.Entry(details_frame, width=20)),
        ("Pump Housing:", ttk.Entry(details_frame, width=20)),
        ("Pump Connection:", ttk.Entry(details_frame, width=20)),
        ("Suction:", ttk.Entry(details_frame, width=20)),
        ("Discharge:", ttk.Entry(details_frame, width=20)),
        ("Flush Arrangement:", ttk.Label(details_frame, text="Yes" if "flush" in pump["configuration"].lower() else "No", font=("Roboto", 10))),
    ]
    for i, (label, widget) in enumerate(fields_left):
        ttk.Label(details_frame, text=label, font=("Roboto", 10)).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        widget.grid(row=i, column=1, padx=5, pady=5, sticky=W)
    for i, (label, widget) in enumerate(fields_right):
        ttk.Label(details_frame, text=label, font=("Roboto", 10)).grid(row=i, column=2, padx=5, pady=5, sticky=W)
        widget.grid(row=i, column=3, padx=5, pady=5, sticky=W)

    right_frame = ttk.Frame(main_layout)
    right_frame.pack(side=LEFT, padx=15, fill=BOTH, expand=True)

    table_frame = ttk.LabelFrame(right_frame, text="Test Data", padding=10, labelwidget=ttk.Label(right_frame, text="Test Data", font=("Roboto", 12, "bold")))
    table_frame.pack(pady=(0, 10), fill=BOTH, expand=True)

    ttk.Label(table_frame, text="Flowrate (l/h)", font=("Roboto", 10)).grid(row=0, column=1, padx=5, pady=5)
    ttk.Label(table_frame, text="Pressure (bar)", font=("Roboto", 10)).grid(row=0, column=2, padx=5, pady=5)
    ttk.Label(table_frame, text="Amperage", font=("Roboto", 10)).grid(row=0, column=3, padx=5, pady=5)

    flow_entries = []
    pressure_entries = []
    amp_entries = []
    for i in range(1, 6):
        ttk.Label(table_frame, text=f"Test {i}", font=("Roboto", 10)).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        flow_entry = ttk.Entry(table_frame, width=15)
        flow_entry.grid(row=i, column=1, padx=5, pady=5)
        pressure_entry = ttk.Entry(table_frame, width=15)
        pressure_entry.grid(row=i, column=2, padx=5, pady=5)
        amp_entry = ttk.Entry(table_frame, width=15)
        amp_entry.grid(row=i, column=3, padx=5, pady=5)
        flow_entries.append(flow_entry)
        pressure_entries.append(pressure_entry)
        amp_entries.append(amp_entry)

    hydro_frame = ttk.LabelFrame(right_frame, text="Hydraulic Test", padding=10, labelwidget=ttk.Label(right_frame, text="Hydraulic Test", font=("Roboto", 12, "bold")))
    hydro_frame.pack(fill=X)

    ttk.Label(hydro_frame, text="Date of Test:", font=("Roboto", 10)).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(hydro_frame, text=datetime.now().strftime("%Y-%m-%d"), font=("Roboto", 10)).grid(row=0, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(hydro_frame, text="Duration of Test:", font=("Roboto", 10)).grid(row=1, column=0, padx=5, pady=5, sticky=W)
    duration_entry = ttk.Entry(hydro_frame, width=20)
    duration_entry.grid(row=1, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(hydro_frame, text="Test Medium:", font=("Roboto", 10)).grid(row=2, column=0, padx=5, pady=5, sticky=W)
    medium_entry = ttk.Entry(hydro_frame, width=20)
    medium_entry.grid(row=2, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(hydro_frame, text="Tested By:", font=("Roboto", 10)).grid(row=3, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(hydro_frame, text=username, font=("Roboto", 10)).grid(row=3, column=1, padx=5, pady=5, sticky=W)

    approval_frame = ttk.Frame(main_frame)
    approval_frame.grid(row=2, column=0, pady=15, sticky=W+E)
    ttk.Label(approval_frame, text="Approved By:", font=("Roboto", 10)).pack(side=LEFT, padx=10)
    name_entry = ttk.Entry(approval_frame, width=20)
    name_entry.pack(side=LEFT, padx=10)
    ttk.Label(approval_frame, text="Date:", font=("Roboto", 10)).pack(side=LEFT, padx=10)
    ttk.Label(approval_frame, text=datetime.now().strftime("%Y-%m-%d"), font=("Roboto", 10)).pack(side=LEFT, padx=10)

    footer_frame = ttk.Frame(main_frame)
    footer_frame.grid(row=3, column=0, pady=15, sticky=W+E)
    complete_btn = ttk.Button(footer_frame, text="Submit for Approval", bootstyle="success", style="large.TButton")
    complete_btn.pack(pady=(0, 5))
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    def complete_test():
        test_data = {
            "invoice_number": invoice_entry.get(),
            "customer": pump["customer"],
            "job_number": job_entry.get(),
            "pump_model": pump["pump_model"],
            "serial_number": serial_number,
            "impeller_diameter": impeller_entry.get(),
            "assembled_by": username,
            "motor_size": fields_left[0][1].get(),
            "motor_speed": fields_left[1][1].get(),
            "motor_volts": fields_left[2][1].get(),
            "motor_enclosure": fields_left[3][1].get(),
            "mechanical_seal": fields_left[4][1].get(),
            "frequency": fields_right[0][1].get(),
            "pump_housing": fields_right[1][1].get(),
            "pump_connection": fields_right[2][1].get(),
            "suction": fields_right[3][1].get(),
            "discharge": fields_right[4][1].get(),
            "flush_arrangement": fields_right[5][1].cget("text"),
            "date_of_test": datetime.now().strftime("%Y-%m-%d"),
            "duration_of_test": duration_entry.get(),
            "test_medium": medium_entry.get(),
            "tested_by": username,
            "flowrate": [entry.get() for entry in flow_entries],
            "pressure": [entry.get() for entry in pressure_entries],
            "amperage": [entry.get() for entry in amp_entries],
            "approved_by": name_entry.get(),
            "approval_date": datetime.now().strftime("%Y-%m-%d"),
        }

        # Store test data and originator in the database
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pumps 
                SET status = 'Pending Approval', 
                    originator = ?, 
                    test_data = ? 
                WHERE serial_number = ?
            """, (username, json.dumps(test_data), serial_number))
            conn.commit()
            logger.info(f"Pump {serial_number} submitted for approval by {username}")

        refresh_callback()
        test_window.destroy()

    complete_btn.configure(command=complete_test)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_testing_dashboard(root, "tester1", "testing", lambda: print("Logged off"))
    root.mainloop()