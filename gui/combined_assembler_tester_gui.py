import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageTk
from database import get_db_connection
import os
import sys
from datetime import datetime
import json
import threading
from utils.config import get_logger
from export_utils import send_email, generate_pdf_notification, generate_pump_details_table, generate_test_data_table

logger = get_logger("combined_assembler_tester_gui")

# Determine the base directory for bundled resources
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"

# Define config paths
if getattr(sys, 'frozen', False):
    # Use AppData for persistent config in installed app
    CONFIG_DIR = os.path.join(os.getenv('APPDATA'), "GuthPumpRegistry")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
    DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
else:
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
    DEFAULT_CONFIG_PATH = CONFIG_PATH

LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
OPTIONS_PATH = os.path.join(BASE_DIR, "assets", "pump_options.json")
BUILD_NUMBER = "1.0.0"

def load_config():
    """Load configuration from config.json, creating it with defaults if missing."""
    # Check user-specific config first (writable location)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
            logger.info(f"Loaded user config from {CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Failed to load user config from {CONFIG_PATH}: {str(e)}")
            config = {}
    else:
        # Fall back to bundled default config
        if os.path.exists(DEFAULT_CONFIG_PATH):
            try:
                with open(DEFAULT_CONFIG_PATH, "r") as f:
                    config = json.load(f)
                logger.info(f"Loaded default config from {DEFAULT_CONFIG_PATH}")
            except Exception as e:
                logger.error(f"Failed to load default config from {DEFAULT_CONFIG_PATH}: {str(e)}")
                config = {}
        else:
            config = {}
            logger.warning(f"No config found at {CONFIG_PATH} or {DEFAULT_CONFIG_PATH}")

    # Ensure defaults are applied for required keys
    config.setdefault("document_dirs", {
        "certificate": os.path.join(BASE_DIR, "certificates"),
        "bom": os.path.join(BASE_DIR, "boms"),
        "confirmation": os.path.join(BASE_DIR, "confirmations"),
        "reports": os.path.join(BASE_DIR, "reports"),
        "excel_exports": os.path.join(BASE_DIR, "exports")
    })

    # If user config didn’t exist, create it with defaults
    if not os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=4)
            logger.info(f"Created default config file at {CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Failed to create default config at {CONFIG_PATH}: {str(e)}")

    return config

class CustomTooltip:
    """Custom tooltip class for widgets."""
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
        ttk.Label(self.tooltip_window, text=self.text, background="lightyellow", relief="solid", borderwidth=1, font=("Roboto", 10)).pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

def load_options():
    """Load pump options from JSON file."""
    try:
        with open(OPTIONS_PATH, "r") as f:
            options = json.load(f)
            logger.debug(f"Loaded options from JSON: {options}")
            return options
    except Exception as e:
        logger.error(f"Failed to load options: {str(e)}")
        return {}

def show_combined_assembler_tester_dashboard(root, username, role, logout_callback):
    """Display the combined assembler and tester dashboard for a single Assembler_Tester role."""
    if role != "Assembler_Tester":
        logger.error(f"User {username} with role {role} attempted to access Assembler/Tester Dashboard")
        Messagebox.show_error("Access Denied", "This dashboard is only accessible to the Assembler_Tester role.")
        logout_callback()
        return

    root.state('zoomed')
    for widget in root.winfo_children():
        widget.destroy()

    options = load_options()
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    header_frame = ttk.Frame(main_frame, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20), ipady=20)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 1.0), int(Image.open(LOGO_PATH).height * 1.0)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
        except Exception as e:
            logger.error(f"Logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Assembler/Tester Dashboard", font=("Roboto", 12)).pack(anchor=W, padx=10)

    assembler_frame = ttk.LabelFrame(main_frame, text="Assembly Tasks", padding=20, bootstyle="default")
    assembler_frame.pack(fill=X, padx=10, pady=10)

    assembler_list_frame = ttk.LabelFrame(assembler_frame, text="Pumps in Assembly", padding=10)
    assembler_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    assembler_columns = ("Serial Number", "Assembly Part Number", "Customer", "Branch", "Pump Model", "Configuration")
    assembler_tree = ttk.Treeview(assembler_list_frame, columns=assembler_columns, show="headings", height=10)
    for col in assembler_columns:
        assembler_tree.heading(col, text=col, anchor=W)
        assembler_tree.column(col, width=150, anchor=W)
    assembler_tree.pack(side=LEFT, fill=BOTH, expand=True)
    assembler_scrollbar = ttk.Scrollbar(assembler_list_frame, orient=VERTICAL, command=assembler_tree.yview)
    assembler_scrollbar.pack(side=RIGHT, fill=Y)
    assembler_tree.configure(yscrollcommand=assembler_scrollbar.set)

    def on_mouse_wheel(event):
        if assembler_tree.winfo_exists():
            if event.delta > 0 or event.num == 4:
                assembler_tree.yview_scroll(-1, "units")
            elif event.delta < 0 or event.num == 5:
                assembler_tree.yview_scroll(1, "units")

    assembler_tree.bind("<MouseWheel>", on_mouse_wheel)
    assembler_tree.bind("<Button-4>", on_mouse_wheel)
    assembler_tree.bind("<Button-5>", on_mouse_wheel)

    def refresh_assembler_pump_list():
        """Refresh the list of pumps in assembly."""
        assembler_tree.delete(*assembler_tree.get_children())
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.serial_number, p.assembly_part_number, p.customer, p.branch, p.pump_model, p.configuration
                    FROM pumps p
                    LEFT JOIN bom_items b ON p.serial_number = b.serial_number
                    WHERE p.status = 'Assembler'
                    GROUP BY p.serial_number, p.assembly_part_number, p.customer, p.branch, p.pump_model, p.configuration
                """)
                for pump in cursor.fetchall():
                    assembler_tree.insert("", END, values=(pump[0], pump[1] or "N/A", pump[2], pump[3], pump[4], pump[5]))
            logger.info("Refreshed assembler pump list")
        except Exception as e:
            logger.error(f"Failed to refresh assembler pump list: {str(e)}")
            Messagebox.show_error("Error", f"Failed to load assembly pumps: {str(e)}")

    refresh_assembler_pump_list()
    assembler_tree.bind("<Double-1>", lambda event: show_bom_window(main_frame, assembler_tree, username, refresh_assembler_pump_list))

    testing_frame = ttk.LabelFrame(main_frame, text="Testing Tasks", padding=20, bootstyle="default")
    testing_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    testing_list_frame = ttk.LabelFrame(testing_frame, text="Pumps in Testing", padding=10)
    testing_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    testing_columns = ("Serial Number", "Assembly Part Number", "Customer", "Branch", "Pump Model", "Configuration")
    testing_tree = ttk.Treeview(testing_list_frame, columns=testing_columns, show="headings", height=10)
    for col in testing_columns:
        testing_tree.heading(col, text=col, anchor=W)
        testing_tree.column(col, width=150, anchor=W)
    testing_tree.pack(side=LEFT, fill=BOTH, expand=True)
    testing_scrollbar = ttk.Scrollbar(testing_list_frame, orient=VERTICAL, command=testing_tree.yview)
    testing_scrollbar.pack(side=RIGHT, fill=Y)
    testing_tree.configure(yscrollcommand=testing_scrollbar.set)

    def refresh_testing_pump_list():
        """Refresh the list of pumps in testing."""
        testing_tree.delete(*testing_tree.get_children())
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT serial_number, assembly_part_number, customer, branch, pump_model, configuration
                    FROM pumps WHERE status = 'Testing'
                """)
                for pump in cursor.fetchall():
                    testing_tree.insert("", END, values=(pump[0], pump[1] or "N/A", pump[2], pump[3], pump[4], pump[5]))
            logger.info("Refreshed testing pump list")
        except Exception as e:
            logger.error(f"Failed to refresh testing pump list: {str(e)}")
            Messagebox.show_error("Error", f"Failed to load testing pumps: {str(e)}")

    refresh_testing_pump_list()
    testing_tree.bind("<Double-1>", lambda event: show_test_report(main_frame, testing_tree, username, refresh_testing_pump_list))

    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=10)
    refresh_btn = ttk.Button(footer_frame, text="Refresh", command=lambda: [refresh_assembler_pump_list(), refresh_testing_pump_list()],
                            bootstyle="info", style="large.TButton")
    refresh_btn.pack(side=LEFT, padx=5)
    CustomTooltip(refresh_btn, text="Refresh the assembly and testing pump lists")
    ttk.Button(footer_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

def show_bom_window(parent_frame, tree, username, refresh_callback):
    """Display BOM for verification by Assembler_Tester role."""
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    serial_number = tree.item(selected[0])["values"][0]
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pumps WHERE serial_number = ?", (serial_number,))
            columns = [desc[0] for desc in cursor.description]
            pump_tuple = cursor.fetchone()
            if not pump_tuple:
                logger.warning(f"No pump found for serial_number: {serial_number}")
                return
            pump = dict(zip(columns, pump_tuple))
            cursor.execute("SELECT part_name, part_code, quantity, pulled_at FROM bom_items WHERE serial_number = ? AND pulled_at IS NOT NULL", (serial_number,))
            bom_items = cursor.fetchall()
            cursor.execute("SELECT username, email FROM users WHERE username = ?", (pump["requested_by"],))
            originator = cursor.fetchone()
    except Exception as e:
        logger.error(f"Failed to load BOM data: {str(e)}")
        Messagebox.show_error("Error", f"Failed to load BOM: {str(e)}")
        return

    bom_window = ttk.Toplevel(parent_frame)
    bom_window.title(f"BOM for Pump {serial_number}")
    bom_window.state("zoomed")

    header_frame = ttk.Frame(bom_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.5), int(Image.open(LOGO_PATH).height * 0.5)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
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

    ttk.Label(scrollable_frame, text="Part Number", font=("Roboto", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Part Name", font=("Roboto", 10, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Quantity", font=("Roboto", 10, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Confirmed", font=("Roboto", 10, "bold")).grid(row=0, column=3, padx=5, pady=5, sticky=W)

    confirm_vars = []
    for i, item in enumerate(bom_items, start=1):
        ttk.Label(scrollable_frame, text=item[1]).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        ttk.Label(scrollable_frame, text=item[0]).grid(row=i, column=1, padx=5, pady=5, sticky=W)
        ttk.Label(scrollable_frame, text=str(item[2])).grid(row=i, column=2, padx=5, pady=5, sticky=W)
        confirm_var = ttk.BooleanVar(value=False)
        confirm_check = ttk.Checkbutton(scrollable_frame, variable=confirm_var, state=NORMAL)
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
        """Refresh the list of unpulled BOM items."""
        unpulled_tree.delete(*unpulled_tree.get_children())
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.part_code, b.part_name, COALESCE((
                        SELECT TOP 1 action FROM audit_log 
                        WHERE action LIKE '%' + 'Reason for not pulling ' + b.part_code + ' on ' + b.serial_number + '%'
                        ORDER BY timestamp DESC
                    ), 'No reason provided') AS reason
                    FROM bom_items b
                    WHERE b.serial_number = ? AND b.pulled_at IS NULL
                """, (serial_number,))
                for item in cursor.fetchall():
                    reason = item[2].replace(f"Reason for not pulling {item[0]} on {serial_number}: ", "") if item[2].startswith("Reason") else item[2]
                    unpulled_tree.insert("", END, values=(item[0], item[1], reason))
        except Exception as e:
            logger.error(f"Failed to refresh unpulled list: {str(e)}")
            Messagebox.show_error("Error", f"Failed to load unpulled items: {str(e)}")

    refresh_unpulled_list()

    footer_frame = ttk.Frame(bom_window)
    footer_frame.pack(side=BOTTOM, pady=10)
    submit_btn = ttk.Button(footer_frame, text="Submit", bootstyle="success", style="large.TButton", state=DISABLED)
    submit_btn.pack(pady=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    def check_submit_state():
        all_confirmed = all(var.get() for var in confirm_vars)
        submit_btn.configure(state=NORMAL if all_confirmed else DISABLED)

    def submit_bom():
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE pumps SET status = 'Testing' WHERE serial_number = ?", (serial_number,))
                conn.commit()
                logger.info(f"Pump {serial_number} moved to Testing by {username} (Assembler_Tester role)")

                config = load_config()
                bom_dir = config["document_dirs"]["bom"]
                confirmation_dir = config["document_dirs"]["confirmation"]
                os.makedirs(bom_dir, exist_ok=True)
                os.makedirs(confirmation_dir, exist_ok=True)

                bom_path = os.path.join(bom_dir, f"bom_{serial_number}.pdf")
                bom_data = {
                    "serial_number": serial_number,
                    "assembly_part_number": pump.get("assembly_part_number", "N/A"),
                    "customer": pump["customer"],
                    "branch": pump.get("branch", ""),
                    "pump_model": pump["pump_model"],
                    "configuration": pump["configuration"],
                }
                bom_items_str = "\n".join([f"{item[1]}: {item[0]} (Qty: {item[2]})" for item in bom_items])
                bom_data["bom_items"] = bom_items_str
                generate_pdf_notification(serial_number, bom_data, title=f"BOM - {serial_number}", output_path=bom_path)

                confirmation_path = os.path.join(confirmation_dir, f"confirmation_{serial_number}.pdf")
                confirmation_data = {
                    "serial_number": serial_number,
                    "assembly_part_number": pump.get("assembly_part_number", "N/A"),
                    "status": "Moved to Testing",
                    "assembled_by": username,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                generate_pdf_notification(serial_number, confirmation_data, title=f"Confirmation - {serial_number}", output_path=confirmation_path)

                if originator:
                    pump_data = {
                        "serial_number": pump["serial_number"],
                        "assembly_part_number": pump.get("assembly_part_number", "N/A"),
                        "customer": pump["customer"],
                        "branch": pump.get("branch", ""),
                        "pump_model": pump["pump_model"],
                        "configuration": pump["configuration"],
                        "impeller_size": pump.get("impeller_size", ""),
                        "connection_type": pump.get("connection_type", ""),
                        "pressure_required": pump.get("pressure_required", ""),
                        "flow_rate_required": pump.get("flow_rate_required", ""),
                        "custom_motor": pump.get("custom_motor", ""),
                        "flush_seal_housing": pump.get("flush_seal_housing", ""),
                    }
                    subject = f"Pump {serial_number} Moved to Testing"
                    greeting = f"Dear {originator[0]},"
                    body_content = f"""
                        <p>The assembly of pump {serial_number} is complete and has been moved to the Testing stage.</p>
                        <h3 style="color: #34495e;">Pump Details</h3>
                        {generate_pump_details_table(pump_data)}
                    """
                    footer = "Regards,<br>Assembler/Tester Team"
                    threading.Thread(target=send_email, args=(originator[1], subject, greeting, body_content, footer, bom_path, confirmation_path), daemon=True).start()
                else:
                    logger.warning(f"No originator found for pump {serial_number}")

            refresh_callback()
            bom_window.destroy()
        except Exception as e:
            logger.error(f"Failed to submit BOM: {str(e)}")
            Messagebox.show_error("Error", f"Failed to submit BOM: {str(e)}")

    submit_btn.configure(command=submit_bom)
    for var in confirm_vars:
        var.trace("w", lambda *args: check_submit_state())
    check_submit_state()

def show_test_report(parent_frame, tree, username, refresh_callback):
    """Display test report for Assembler_Tester role with all fields optional."""
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    serial_number = tree.item(selected[0])["values"][0]
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT serial_number, customer, pump_model, configuration, requested_by, branch, impeller_size,
                       connection_type, pressure_required, flow_rate_required, custom_motor, flush_seal_housing,
                       assembly_part_number
                FROM pumps WHERE serial_number = ?
            """, (serial_number,))
            columns = [desc[0] for desc in cursor.description]
            pump_tuple = cursor.fetchone()
            if not pump_tuple:
                logger.warning(f"No pump found for serial_number: {serial_number}")
                return
            pump = dict(zip(columns, pump_tuple))
            cursor.execute("SELECT username, email FROM users WHERE username = ?", (pump["requested_by"],))
            originator = cursor.fetchone()
    except Exception as e:
        logger.error(f"Failed to load pump data: {str(e)}")
        Messagebox.show_error("Error", f"Failed to load pump data: {str(e)}")
        return

    test_window = ttk.Toplevel(parent_frame)
    test_window.title(f"Test Report for Pump {serial_number}")
    test_window.state("zoomed")

    header_frame = ttk.Frame(test_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.5), int(Image.open(LOGO_PATH).height * 0.5)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
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
        if canvas.winfo_exists():
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

    canvas.bind("<MouseWheel>", on_mouse_wheel)
    def on_close():
        try:
            if canvas.winfo_exists():
                canvas.unbind("<MouseWheel>")
            test_window.destroy()
        except Exception as e:
            logger.debug(f"Minor error during window close: {str(e)}")

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

    fab_frame = ttk.LabelFrame(left_frame, text="Fabrication", padding=10)
    fab_frame.pack(pady=(0, 10), fill=X)

    ttk.Label(fab_frame, text="Assembly Part Number:", font=("Roboto", 10)).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=pump.get("assembly_part_number", "N/A"), font=("Roboto", 10)).grid(row=0, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Pump Model:", font=("Roboto", 10)).grid(row=1, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=pump["pump_model"], font=("Roboto", 10)).grid(row=1, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Serial Number:", font=("Roboto", 10)).grid(row=2, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=serial_number, font=("Roboto", 10)).grid(row=2, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Impeller Diameter:", font=("Roboto", 10)).grid(row=3, column=0, padx=5, pady=5, sticky=W)
    impeller_entry = ttk.Entry(fab_frame, width=20)
    impeller_entry.insert(0, pump.get("impeller_size", ""))
    impeller_entry.grid(row=3, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Assembled By:", font=("Roboto", 10)).grid(row=4, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=username, font=("Roboto", 10)).grid(row=4, column=1, padx=5, pady=5, sticky=W)

    details_frame = ttk.LabelFrame(left_frame, text="Details", padding=10)
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

    table_frame = ttk.LabelFrame(right_frame, text="Test Data", padding=10)
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

    hydro_frame = ttk.LabelFrame(right_frame, text="Hydraulic Test", padding=10)
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
        """Submit test report for approval with all fields optional, preparing data for graph."""
        test_data = {
            "invoice_number": invoice_entry.get(),
            "customer": pump["customer"],
            "job_number": job_entry.get(),
            "assembly_part_number": pump.get("assembly_part_number", "N/A"),
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

        for field in ["flowrate", "pressure", "amperage"]:
            for i, value in enumerate(test_data[field]):
                if value.strip():
                    try:
                        float(value)
                    except ValueError:
                        Messagebox.show_error("Error", f"{field.capitalize()} Test {i+1} must be numeric if provided.")
                        return

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE pumps 
                    SET status = 'Pending Approval', 
                        test_data = ? 
                    WHERE serial_number = ?
                """, (json.dumps(test_data), serial_number))
                conn.commit()
                logger.info(f"Pump {serial_number} submitted for approval by {username} (Assembler_Tester role)")

                config = load_config()
                certificate_dir = config["document_dirs"]["certificate"]
                os.makedirs(certificate_dir, exist_ok=True)

                pdf_path = os.path.join(certificate_dir, f"test_certificate_{serial_number}.pdf")
                pump_data = {
                    "serial_number": test_data["serial_number"],
                    "assembly_part_number": test_data["assembly_part_number"],
                    "customer": test_data["customer"],
                    "branch": pump.get("branch", ""),
                    "pump_model": test_data["pump_model"],
                    "configuration": pump["configuration"],
                    "impeller_size": test_data["impeller_diameter"],
                    "connection_type": test_data["pump_connection"],
                    "pressure_required": pump.get("pressure_required", ""),
                    "flow_rate_required": pump.get("flow_rate_required", ""),
                    "custom_motor": test_data["motor_size"],
                    "flush_seal_housing": test_data["flush_arrangement"],
                    "date_of_test": test_data["date_of_test"],
                    "duration_of_test": test_data["duration_of_test"],
                    "test_medium": test_data["test_medium"],
                    "tested_by": test_data["tested_by"],
                    "flowrate": test_data["flowrate"],  # Pass raw list for graph
                    "pressure": test_data["pressure"],   # Pass raw list for graph
                    "amperage": test_data["amperage"],   # Pass raw list for graph
                    # For table display in PDF/email
                    "flowrate_display": ", ".join([v for v in test_data["flowrate"] if v.strip()]) or "Not provided",
                    "pressure_display": ", ".join([v for v in test_data["pressure"] if v.strip()]) or "Not provided",
                    "amperage_display": ", ".join([v for v in test_data["amperage"] if v.strip()]) or "Not provided",
                }
                generate_pdf_notification(serial_number, pump_data, title=f"Test Certificate - {serial_number}", output_path=pdf_path)

                if originator:
                    subject = f"Pump {serial_number} Submitted for Approval"
                    greeting = f"Dear {originator[0]},"
                    body_content = f"""
                        <p>The testing of pump {serial_number} is complete and has been submitted for approval.</p>
                        <h3 style="color: #34495e;">Pump Details</h3>
                        {generate_pump_details_table(pump_data)}
                        <h3 style="color: #34495e;">Test Data</h3>
                        {generate_test_data_table({
                            "flowrate": [v for v in test_data["flowrate"] if v.strip()] or ["Not provided"],
                            "pressure": [v for v in test_data["pressure"] if v.strip()] or ["Not provided"],
                            "amperage": [v for v in test_data["amperage"] if v.strip()] or ["Not provided"]
                        })}
                    """
                    footer = "Regards,<br>Assembler/Tester Team"
                    threading.Thread(target=send_email, args=(originator[1], subject, greeting, body_content, footer, pdf_path), daemon=True).start()
                else:
                    logger.warning(f"No originator found for pump {serial_number}")

            refresh_callback()
            test_window.destroy()
        except Exception as e:
            logger.error(f"Failed to submit test report: {str(e)}")
            Messagebox.show_error("Error", f"Failed to submit test report: {str(e)}")

    complete_btn.configure(command=complete_test)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_combined_assembler_tester_dashboard(root, "testuser", "Assembler_Tester", lambda: print("Logout"))
    root.mainloop()