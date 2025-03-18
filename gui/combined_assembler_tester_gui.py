import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox  # For error messages
from PIL import Image, ImageTk
from database import connect_db
import os
from datetime import datetime
import json
import threading
from utils.config import get_logger
from export_utils import send_email, generate_pdf_notification, generate_pump_details_table, generate_test_data_table

logger = get_logger("combined_assembler_tester_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
OPTIONS_PATH = os.path.join(BASE_DIR, "assets", "pump_options.json")
BUILD_NUMBER = "1.0.0"

# Custom Tooltip class (reused from dashboard_gui)
class CustomTooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height()
        self.tooltip_window = ttk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tooltip_window, text=self.text, background="lightyellow", relief="solid", borderwidth=1, font=("Roboto", 10))
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

def load_options():
    with open(OPTIONS_PATH, "r") as f:
        options = json.load(f)
    logger.debug(f"Loaded options from JSON: {options}")
    return options

def show_combined_assembler_tester_dashboard(root, username, role, logout_callback):
    for widget in root.winfo_children():
        widget.destroy()

    root.state('zoomed')
    options = load_options()
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Header
    header_frame = ttk.Frame(main_frame, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20), ipady=20)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH)
            img_resized = img.resize((int(img.width * 1.0), int(img.height * 1.0)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            logo_label = ttk.Label(header_frame, image=logo)
            logo_label.image = logo
            logo_label.pack(side=RIGHT, padx=10)
        except Exception as e:
            logger.error(f"Logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Assembler and Tester Dashboard", font=("Roboto", 12)).pack(anchor=W, padx=10)

    # Assembler Section (on top)
    assembler_frame = ttk.LabelFrame(main_frame, text="Assembler Tasks", padding=20, bootstyle="default")
    assembler_frame.pack(fill=X, padx=10, pady=10)

    # Assembler Pump Inventory
    assembler_list_frame = ttk.LabelFrame(assembler_frame, text="Pumps in Assembler", padding=10)
    assembler_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    assembler_columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration")  # Removed "Received"
    assembler_tree = ttk.Treeview(assembler_list_frame, columns=assembler_columns, show="headings", height=10)
    for col in assembler_columns:
        assembler_tree.heading(col, text=col, anchor=W)
        assembler_tree.column(col, width=150, anchor=W)
    assembler_tree.pack(side=LEFT, fill=BOTH, expand=True)
    assembler_scrollbar = ttk.Scrollbar(assembler_list_frame, orient=VERTICAL, command=assembler_tree.yview)
    assembler_scrollbar.pack(side=RIGHT, fill=Y)
    assembler_tree.configure(yscrollcommand=assembler_scrollbar.set)

    def refresh_assembler_pump_list():
        for item in assembler_tree.get_children():
            assembler_tree.delete(item)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.serial_number, p.customer, p.branch, p.pump_model, p.configuration
                FROM pumps p
                LEFT JOIN bom_items b ON p.serial_number = b.serial_number
                WHERE p.status = 'Assembler'
                GROUP BY p.serial_number, p.customer, p.branch, p.pump_model, p.configuration
            """)  # Removed CASE statement for "Received"
            for pump in cursor.fetchall():
                assembler_tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"],
                                                      pump["pump_model"], pump["configuration"]))  # Removed "received"

    refresh_assembler_pump_list()
    assembler_tree.bind("<Double-1>", lambda event: show_bom_window(main_frame, assembler_tree, username, refresh_assembler_pump_list))

    # Tester Section (below assembler)
    testing_frame = ttk.LabelFrame(main_frame, text="Tester Tasks", padding=20, bootstyle="default")
    testing_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Testing Pump Inventory
    testing_list_frame = ttk.LabelFrame(testing_frame, text="Pumps in Testing", padding=10)
    testing_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    testing_columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration")
    testing_tree = ttk.Treeview(testing_list_frame, columns=testing_columns, show="headings", height=10)
    for col in testing_columns:
        testing_tree.heading(col, text=col, anchor=W)
        testing_tree.column(col, width=150, anchor=W)
    testing_tree.pack(side=LEFT, fill=BOTH, expand=True)
    testing_scrollbar = ttk.Scrollbar(testing_list_frame, orient=VERTICAL, command=testing_tree.yview)
    testing_scrollbar.pack(side=RIGHT, fill=Y)
    testing_tree.configure(yscrollcommand=testing_scrollbar.set)

    def refresh_testing_pump_list():
        for item in testing_tree.get_children():
            testing_tree.delete(item)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT serial_number, customer, branch, pump_model, configuration
                FROM pumps WHERE status = 'Testing'
            """)
            for pump in cursor.fetchall():
                testing_tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"],
                                                    pump["pump_model"], pump["configuration"]))

    refresh_testing_pump_list()
    testing_tree.bind("<Double-1>", lambda event: show_test_report(main_frame, testing_tree, username, refresh_testing_pump_list))

    # Footer
    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=10)
    refresh_btn = ttk.Button(footer_frame, text="Refresh", command=lambda: [refresh_assembler_pump_list(), refresh_testing_pump_list()], 
                            bootstyle="info", style="large.TButton")
    refresh_btn.pack(side=LEFT, padx=5)
    CustomTooltip(refresh_btn, text="Refresh the assembler and tester pump lists")
    ttk.Button(footer_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

# From assembler_gui.py
def show_bom_window(parent_frame, tree, username, refresh_callback):
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    serial_number = tree.item(selected[0])["values"][0]
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pumps WHERE serial_number = ?", (serial_number,))
        pump = cursor.fetchone()
        if not pump:
            logger.warning(f"No pump found for serial_number: {serial_number}")
            return
        cursor.execute("SELECT part_name, part_code, quantity, pulled_at FROM bom_items WHERE serial_number = ? AND pulled_at IS NOT NULL", (serial_number,))
        bom_items = cursor.fetchall()
        logger.debug(f"Fetched {len(bom_items)} received BOM items for {serial_number}: {[(item['part_name'], item['part_code']) for item in bom_items]}")
        cursor.execute("SELECT username, email FROM users WHERE username = ?", (pump["requested_by"],))
        originator = cursor.fetchone()

    bom_window = ttk.Toplevel(parent_frame)
    bom_window.title(f"BOM for Pump {serial_number}")
    bom_window.state("zoomed")

    header_frame = ttk.Frame(bom_window, style="white.TFrame")
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
            logger.error(f"BOM window logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Pump {serial_number}", font=("Roboto", 14, "bold")).pack(anchor=W, padx=10)

    bom_frame = ttk.LabelFrame(bom_window, text="Bill of Materials (Received Items)", padding=10)
    bom_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    canvas = ttk.Canvas(bom_frame)
    scrollbar = ttk.Scrollbar(bom_frame, orient=VERTICAL, command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill=Y)

    # BOM Headers
    ttk.Label(scrollable_frame, text="Part Number", font=("Roboto", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Part Name", font=("Roboto", 10, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Quantity", font=("Roboto", 10, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Confirmed", font=("Roboto", 10, "bold")).grid(row=0, column=3, padx=5, pady=5, sticky=W)

    # BOM Items
    confirm_vars = []
    for i, item in enumerate(bom_items, start=1):
        ttk.Label(scrollable_frame, text=item["part_code"]).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        ttk.Label(scrollable_frame, text=item["part_name"]).grid(row=i, column=1, padx=5, pady=5, sticky=W)
        ttk.Label(scrollable_frame, text=str(item["quantity"])).grid(row=i, column=2, padx=5, pady=5, sticky=W)

        confirm_var = ttk.BooleanVar(value=False)
        confirm_check = ttk.Checkbutton(scrollable_frame, variable=confirm_var)
        confirm_check.grid(row=i, column=3, padx=5, pady=5)
        confirm_vars.append(confirm_var)

    unpulled_frame = ttk.LabelFrame(bom_window, text="Items Not Pulled", padding=10)
    unpulled_frame.pack(fill=X, padx=10, pady=10)
    unpulled_columns = ("Part Code", "Part Name", "Reason")
    unpulled_tree = ttk.Treeview(unpulled_frame, columns=unpulled_columns, show="headings", height=5)
    for col in unpulled_columns:
        unpulled_tree.heading(col, text=col, anchor=W)
        unpulled_tree.column(col, width=200, anchor=W)
    unpulled_tree.pack(side=LEFT, fill=X, expand=True)
    unpulled_scrollbar = ttk.Scrollbar(unpulled_frame, orient=VERTICAL, command=unpulled_tree.yview)
    unpulled_scrollbar.pack(side=RIGHT, fill=Y)
    unpulled_tree.configure(yscrollcommand=unpulled_scrollbar.set)

    def refresh_unpulled_list():
        for item in unpulled_tree.get_children():
            unpulled_tree.delete(item)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.part_code, b.part_name, COALESCE((
                    SELECT action FROM audit_log 
                    WHERE action LIKE '%Reason for not pulling ' || b.part_code || ' on ' || b.serial_number || '%'
                    ORDER BY timestamp DESC LIMIT 1
                ), 'No reason provided') AS reason
                FROM bom_items b
                WHERE b.serial_number = ? AND b.pulled_at IS NULL
            """, (serial_number,))
            for item in cursor.fetchall():
                reason = item["reason"].replace(f"Reason for not pulling {item['part_code']} on {serial_number}: ", "") if item["reason"].startswith("Reason") else item["reason"]
                unpulled_tree.insert("", END, values=(item["part_code"], item["part_name"], reason))

    refresh_unpulled_list()

    footer_frame = ttk.Frame(bom_window)
    footer_frame.pack(side=BOTTOM, pady=10)
    submit_btn = ttk.Button(footer_frame, text="Submit", bootstyle="success", style="large.TButton", state=DISABLED)
    submit_btn.pack(pady=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    def check_submit_state():
        all_confirmed = all(var.get() for var in confirm_vars)
        logger.debug(f"All confirmed: {all_confirmed}")
        submit_btn.configure(state=NORMAL if all_confirmed else DISABLED)

    def submit_bom():
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pumps SET status = 'Testing' WHERE serial_number = ?", (serial_number,))
            conn.commit()
            logger.info(f"Pump {serial_number} moved to Testing by {username}")
            cursor.execute("SELECT status FROM pumps WHERE serial_number = ?", (serial_number,))
            new_status = cursor.fetchone()["status"]
            logger.debug(f"Post-submit status for {serial_number}: {new_status}")

            if originator:
                pump_data = {
                    "serial_number": pump["serial_number"],
                    "customer": pump["customer"],
                    "branch": pump["branch"] if "branch" in pump else "",
                    "pump_model": pump["pump_model"],
                    "configuration": pump["configuration"],
                    "impeller_size": pump["impeller_size"] if "impeller_size" in pump else "",
                    "connection_type": pump["connection_type"] if "connection_type" in pump else "",
                    "pressure_required": pump["pressure_required"] if "pressure_required" in pump else "",
                    "flow_rate_required": pump["flow_rate_required"] if "flow_rate_required" in pump else "",
                    "custom_motor": pump["custom_motor"] if "custom_motor" in pump else "",
                    "flush_seal_housing": pump["flush_seal_housing"] if "flush_seal_housing" in pump else "",
                }

                subject = f"Pump {serial_number} Moved to Testing"
                greeting = f"Dear {originator['username']},"
                body_content = f"""
                    <p>The assembly of pump {serial_number} is complete, and it has been moved to the Testing stage.</p>
                    <h3 style="color: #34495e;">Pump Details</h3>
                    {generate_pump_details_table(pump_data)}
                """
                footer = "Regards,<br>Assembly Team"
                threading.Thread(target=send_email, args=(originator["email"], subject, greeting, body_content, footer), daemon=True).start()
            else:
                logger.warning(f"No originator found for pump {serial_number}")

        refresh_callback()
        bom_window.destroy()

    submit_btn.configure(command=submit_bom)

    for var in confirm_vars:
        var.trace("w", lambda *args: check_submit_state())

    check_submit_state()

# From testing_gui.py
def show_test_report(parent_frame, tree, username, refresh_callback):
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    serial_number = tree.item(selected[0])["values"][0]
    with connect_db() as conn:
        cursor = conn.cursor()
        # Updated query to include requested_by and other relevant columns
        cursor.execute("""
            SELECT serial_number, customer, pump_model, configuration, requested_by, branch, impeller_size,
                   connection_type, pressure_required, flow_rate_required, custom_motor, flush_seal_housing
            FROM pumps WHERE serial_number = ?
        """, (serial_number,))
        pump = cursor.fetchone()
        if not pump:
            logger.warning(f"No pump found for serial_number: {serial_number}")
            return

        # Fetch originator's details
        cursor.execute("SELECT username, email FROM users WHERE username = ?", (pump["requested_by"],))
        originator = cursor.fetchone()
        if not originator or not originator["email"]:
            logger.warning(f"No email found for requested_by {pump['requested_by']} of pump {serial_number}")
            originator = None  # Proceed without email if not found

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

    # Bind the mouse wheel event to the canvas only
    canvas.bind("<MouseWheel>", on_mouse_wheel)

    # Clean up binding when the window is closed
    def on_close():
        canvas.unbind("<MouseWheel>")
        test_window.destroy()

    test_window.protocol("WM_DELETE_WINDOW", on_close)

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
    impeller_entry.insert(0, pump["impeller_size"] if "impeller_size" in pump else "")  # Safe access
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
            "approval_date": datetime.now().strftime("%Y-%m-%d"),
        }

        # Validate test data
        if not all(test_data["flowrate"]) or not all(test_data["pressure"]) or not all(test_data["amperage"]):
            Messagebox.show_error("Error", "All test data fields must be filled.")
            return

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

            if originator:
                pump_data = {
                    "serial_number": test_data["serial_number"],
                    "customer": test_data["customer"],
                    "branch": pump["branch"] if "branch" in pump else "",
                    "pump_model": test_data["pump_model"],
                    "configuration": pump["configuration"],
                    "impeller_size": test_data["impeller_diameter"],
                    "connection_type": test_data["pump_connection"],
                    "pressure_required": pump["pressure_required"] if "pressure_required" in pump else "",
                    "flow_rate_required": pump["flow_rate_required"] if "flow_rate_required" in pump else "",
                    "custom_motor": test_data["motor_size"],
                    "flush_seal_housing": test_data["flush_arrangement"],
                }

                # Generate PDF certificate
                pdf_path = generate_pdf_notification(serial_number, pump_data, title=f"Test Certificate - {serial_number}")
                subject = f"Pump {serial_number} Submitted for Approval"
                greeting = f"Dear {originator['username']},"
                body_content = f"""
                    <p>The testing of pump {serial_number} is complete, and it has been submitted for approval.</p>
                    <h3 style="color: #34495e;">Pump Details</h3>
                    {generate_pump_details_table(pump_data)}
                    <h3 style="color: #34495e;">Test Data</h3>
                    {generate_test_data_table({
                        "flowrate": test_data["flowrate"],
                        "pressure": test_data["pressure"],
                        "amperage": test_data["amperage"]
                    })}
                """
                footer = "Regards,<br>Testing Team"
                threading.Thread(target=send_email, args=(originator["email"], subject, greeting, body_content, footer, pdf_path), daemon=True).start()
            else:
                logger.warning(f"No originator found for pump {serial_number}")

        refresh_callback()
        test_window.destroy()

    complete_btn.configure(command=complete_test)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_combined_assembler_tester_dashboard(root, "testuser", "Assembler/Tester", lambda: print("Logout"))
    root.mainloop()