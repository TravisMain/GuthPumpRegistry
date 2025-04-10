import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageTk
from database import get_db_connection
import os
import sys
from datetime import datetime, timedelta
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
    # Add instruction under the heading
    ttk.Label(header_frame, text="This dashboard lets you assemble and test pump assemblies. Manage tasks and submit test reports for approval.",
              font=("Roboto", 10), wraplength=600).pack(anchor=W, padx=10)

    assembler_frame = ttk.LabelFrame(main_frame, text="Assembly Tasks", padding=20, bootstyle="default")
    assembler_frame.pack(fill=X, padx=10, pady=10)

    assembler_list_frame = ttk.LabelFrame(assembler_frame, text="Pumps in Assembly", padding=10)
    assembler_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    assembler_columns = ("Serial Number", "Assembly Part Number", "Customer", "Branch", "Pump Model", "Configuration", "Mechanical Seal", "O ring Material", "Impeller Size", "Flush Seal Housing")
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
                    SELECT p.serial_number, p.assembly_part_number, p.customer, p.branch, p.pump_model, p.configuration,
                           p.mechanical_seals, p.o_ring_material, p.impeller_size, p.flush_seal_housing
                    FROM pumps p
                    LEFT JOIN bom_items b ON p.serial_number = b.serial_number
                    WHERE p.status = 'Assembler'
                    GROUP BY p.serial_number, p.assembly_part_number, p.customer, p.branch, p.pump_model, p.configuration,
                             p.mechanical_seals, p.o_ring_material, p.impeller_size, p.flush_seal_housing
                """)
                for pump in cursor.fetchall():
                    assembler_tree.insert("", END, values=(pump[0], pump[1] or "N/A", pump[2], pump[3], pump[4], pump[5], pump[6] or "N/A", pump[7] or "N/A", pump[8] or "N/A", pump[9] or "N/A"))
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

    # Header with Serial Number, Assembly Part Number, Pump Model (matching Stores dashboard style)
    header_info_frame = ttk.Frame(header_frame)
    header_info_frame.pack(anchor=W, padx=10)

    # Serial Number
    serial_frame = ttk.Frame(header_info_frame)
    serial_frame.pack(anchor=W, pady=5)
    ttk.Label(serial_frame, text="Serial Number: ", font=("Roboto", 14)).pack(side=LEFT)  # Not bold
    ttk.Label(serial_frame, text=serial_number, font=("Roboto", 14, "bold")).pack(side=LEFT)  # Bold

    # Assembly Part Number
    assembly_part_number = pump.get("assembly_part_number", "N/A")
    assembly_frame = ttk.Frame(header_info_frame)
    assembly_frame.pack(anchor=W, pady=5)
    ttk.Label(assembly_frame, text="Assembly Part Number: ", font=("Roboto", 14)).pack(side=LEFT)  # Not bold
    ttk.Label(assembly_frame, text=assembly_part_number, font=("Roboto", 14, "bold")).pack(side=LEFT)  # Bold

    # Pump Model
    pump_model_frame = ttk.Frame(header_info_frame)
    pump_model_frame.pack(anchor=W, pady=5)
    ttk.Label(pump_model_frame, text="Pump Model: ", font=("Roboto", 14)).pack(side=LEFT)  # Not bold
    ttk.Label(pump_model_frame, text=pump['pump_model'], font=("Roboto", 14, "bold")).pack(side=LEFT)  # Bold

    # Main content frame to manage layout
    content_frame = ttk.Frame(bom_window)
    content_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Bill of Materials (Received Items)
    bom_frame = ttk.LabelFrame(content_frame, text="Bill of Materials (Received Items)", padding=10)
    bom_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

    canvas = ttk.Canvas(bom_frame)
    scrollbar = ttk.Scrollbar(bom_frame, orient=VERTICAL, command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill=Y)

    # Enable mouse wheel scrolling for the BOM table
    def on_mouse_wheel(event):
        if canvas.winfo_exists():
            if event.delta > 0 or event.num == 4:  # Scroll up
                canvas.yview_scroll(-1, "units")
            elif event.delta < 0 or event.num == 5:  # Scroll down
                canvas.yview_scroll(1, "units")

    canvas.bind("<MouseWheel>", on_mouse_wheel)  # Windows
    canvas.bind("<Button-4>", on_mouse_wheel)    # Linux/macOS scroll up
    canvas.bind("<Button-5>", on_mouse_wheel)    # Linux/macOS scroll down

    # Clean up bindings on window close
    def on_close():
        try:
            if canvas.winfo_exists():
                canvas.unbind("<MouseWheel>")
                canvas.unbind("<Button-4>")
                canvas.unbind("<Button-5>")
            bom_window.destroy()
        except Exception as e:
            logger.debug(f"Minor error during BOM window close: {str(e)}")

    bom_window.protocol("WM_DELETE_WINDOW", on_close)

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

    # Items Not Pulled
    unpulled_frame = ttk.LabelFrame(content_frame, text="Items Not Pulled", padding=10)
    unpulled_frame.pack(fill=X, pady=(0, 10))
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

    # Notes Section (Read-Only)
    notes_frame = ttk.LabelFrame(content_frame, text="Notes from Stores", padding=10)
    notes_frame.pack(fill=X, pady=(0, 10))
    notes_text = ttk.Text(notes_frame, height=5, width=80, font=("Roboto", 10), state="disabled")
    notes_text.pack(fill=X, expand=True, padx=5, pady=5)

    # Retrieve and display notes from the pumps table
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT notes FROM pumps WHERE serial_number = ?", (serial_number,))
            result = cursor.fetchone()
            notes = result[0] if result and result[0] else "No notes provided."
            notes_text.configure(state="normal")
            notes_text.insert("1.0", notes)
            notes_text.configure(state="disabled")
    except Exception as e:
        logger.error(f"Failed to load notes for pump {serial_number}: {str(e)}")
        notes_text.configure(state="normal")
        notes_text.insert("1.0", "Error loading notes.")
        notes_text.configure(state="disabled")

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
    """Display simplified test report for Assembler_Tester role with a tablet-friendly interface."""
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

    # Start timer for Duration of Test
    start_time = datetime.now()
    duration_submitted = False

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
    ttk.Label(header_frame, text="Pump Test Report", font=("Roboto", 16, "bold")).pack(anchor=W, padx=10)

    main_frame = ttk.Frame(test_window)
    main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

    # Pump Details Section (Non-editable)
    details_frame = ttk.LabelFrame(main_frame, text="Pump Details", padding=15)
    details_frame.pack(fill=X, pady=(0, 20))

    ttk.Label(details_frame, text="Pump Model:", font=("Roboto", 14, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky=W)
    ttk.Label(details_frame, text=pump["pump_model"], font=("Roboto", 14)).grid(row=0, column=1, padx=10, pady=10, sticky=W)

    ttk.Label(details_frame, text="Serial Number:", font=("Roboto", 14, "bold")).grid(row=1, column=0, padx=10, pady=10, sticky=W)
    ttk.Label(details_frame, text=serial_number, font=("Roboto", 14)).grid(row=1, column=1, padx=10, pady=10, sticky=W)

    ttk.Label(details_frame, text="Impeller Diameter:", font=("Roboto", 14, "bold")).grid(row=2, column=0, padx=10, pady=10, sticky=W)
    ttk.Label(details_frame, text=pump.get("impeller_size", ""), font=("Roboto", 14)).grid(row=2, column=1, padx=10, pady=10, sticky=W)

    # Test Data Section (Editable)
    table_frame = ttk.LabelFrame(main_frame, text="Test Data", padding=15)
    table_frame.pack(fill=BOTH, expand=True, pady=(0, 20))

    ttk.Label(table_frame, text="Flowrate (L/h)", font=("Roboto", 14, "bold")).grid(row=0, column=1, padx=15, pady=10)
    ttk.Label(table_frame, text="Suction Pressure (bar)", font=("Roboto", 14, "bold")).grid(row=0, column=2, padx=15, pady=10)
    ttk.Label(table_frame, text="Discharge Pressure (bar)", font=("Roboto", 14, "bold")).grid(row=0, column=3, padx=15, pady=10)
    ttk.Label(table_frame, text="Amperage", font=("Roboto", 14, "bold")).grid(row=0, column=4, padx=15, pady=10)

    flow_entries = []
    suction_pressure_entries = []
    discharge_pressure_entries = []
    amp_entries = []
    for i in range(1, 6):
        ttk.Label(table_frame, text=f"Test {i}", font=("Roboto", 14, "bold")).grid(row=i, column=0, padx=15, pady=10, sticky=W)
        flow_entry = ttk.Entry(table_frame, width=20, font=("Roboto", 14))
        flow_entry.grid(row=i, column=1, padx=15, pady=10)
        suction_pressure_entry = ttk.Entry(table_frame, width=20, font=("Roboto", 14))
        suction_pressure_entry.grid(row=i, column=2, padx=15, pady=10)
        discharge_pressure_entry = ttk.Entry(table_frame, width=20, font=("Roboto", 14))
        discharge_pressure_entry.grid(row=i, column=3, padx=15, pady=10)
        amp_entry = ttk.Entry(table_frame, width=20, font=("Roboto", 14))
        amp_entry.grid(row=i, column=4, padx=15, pady=10)
        flow_entries.append(flow_entry)
        suction_pressure_entries.append(suction_pressure_entry)
        discharge_pressure_entries.append(discharge_pressure_entry)
        amp_entries.append(amp_entry)

    # Hydraulic Test Section
    hydro_frame = ttk.LabelFrame(main_frame, text="Hydraulic Test", padding=15)
    hydro_frame.pack(fill=X, pady=(0, 20))

    ttk.Label(hydro_frame, text="Date of Test:", font=("Roboto", 14, "bold")).grid(row=0, column=0, padx=10, pady=10, sticky=W)
    ttk.Label(hydro_frame, text=datetime.now().strftime("%Y-%m-%d"), font=("Roboto", 14)).grid(row=0, column=1, padx=10, pady=10, sticky=W)

    # Footer with Submit Button
    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(fill=X, pady=10)
    complete_btn = ttk.Button(footer_frame, text="Submit for Approval", bootstyle="success", style="large.TButton")
    complete_btn.pack(pady=(0, 10))
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    def complete_test():
        """Submit test report for approval with simplified fields."""
        nonlocal duration_submitted
        end_time = datetime.now()
        duration = end_time - start_time
        duration_str = str(duration).split('.')[0]  # Format as HH:MM:SS

        # Calculate pressure as Discharge Pressure - Suction Pressure for each test
        pressure_values = []
        for suction, discharge in zip(suction_pressure_entries, discharge_pressure_entries):
            suction_val = suction.get().strip()
            discharge_val = discharge.get().strip()
            if suction_val and discharge_val:
                try:
                    pressure = float(discharge_val) - float(suction_val)
                    pressure_values.append(str(pressure))
                except ValueError:
                    Messagebox.show_error("Error", "Suction Pressure and Discharge Pressure must be numeric if provided.")
                    return
            else:
                pressure_values.append("")

        test_data = {
            "pump_model": pump["pump_model"],
            "serial_number": serial_number,
            "impeller_diameter": pump.get("impeller_size", ""),
            "date_of_test": datetime.now().strftime("%Y-%m-%d"),
            "duration_of_test": duration_str,
            "test_medium": "Water",  # Default to Water
            "tested_by": username,
            "flowrate": [entry.get() for entry in flow_entries],
            "suction_pressure": [entry.get() for entry in suction_pressure_entries],
            "discharge_pressure": [entry.get() for entry in discharge_pressure_entries],
            "pressure": pressure_values,  # Calculated as Discharge - Suction
            "amperage": [entry.get() for entry in amp_entries],
            "approval_date": datetime.now().strftime("%Y-%m-%d"),
        }

        for field in ["flowrate", "suction_pressure", "discharge_pressure", "amperage"]:
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
                    "assembly_part_number": pump.get("assembly_part_number", "N/A"),
                    "customer": pump["customer"],
                    "branch": pump.get("branch", ""),
                    "pump_model": test_data["pump_model"],
                    "configuration": pump["configuration"],
                    "impeller_size": test_data["impeller_diameter"],
                    "connection_type": pump.get("connection_type", ""),
                    "pressure_required": pump.get("pressure_required", ""),
                    "flow_rate_required": pump.get("flow_rate_required", ""),
                    "custom_motor": pump.get("custom_motor", ""),
                    "flush_seal_housing": pump.get("flush_seal_housing", ""),
                    "date_of_test": test_data["date_of_test"],
                    "duration_of_test": test_data["duration_of_test"],
                    "test_medium": test_data["test_medium"],
                    "tested_by": test_data["tested_by"],
                    "flowrate": test_data["flowrate"],  # Pass raw list for graph
                    "pressure": test_data["pressure"],   # Pass calculated pressure for graph
                    "amperage": test_data["amperage"],   # Pass raw list for graph
                    # For table display in PDF/email
                    "flowrate_display": ", ".join([v for v in test_data["flowrate"] if v.strip()]) or "Not provided",
                    "suction_pressure_display": ", ".join([v for v in test_data["suction_pressure"] if v.strip()]) or "Not provided",
                    "discharge_pressure_display": ", ".join([v for v in test_data["discharge_pressure"] if v.strip()]) or "Not provided",
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
                            "suction_pressure": [v for v in test_data["suction_pressure"] if v.strip()] or ["Not provided"],
                            "discharge_pressure": [v for v in test_data["discharge_pressure"] if v.strip()] or ["Not provided"],
                            "pressure": [v for v in test_data["pressure"] if v.strip()] or ["Not provided"],
                            "amperage": [v for v in test_data["amperage"] if v.strip()] or ["Not provided"]
                        })}
                    """
                    footer = "Regards,<br>Assembler/Tester Team"
                    threading.Thread(target=send_email, args=(originator[1], subject, greeting, body_content, footer, pdf_path), daemon=True).start()
                else:
                    logger.warning(f"No originator found for pump {serial_number}")

            duration_submitted = True
            refresh_callback()
            test_window.destroy()
        except Exception as e:
            logger.error(f"Failed to submit test report: {str(e)}")
            Messagebox.show_error("Error", f"Failed to submit test report: {str(e)}")

    complete_btn.configure(command=complete_test)

    # Reset timer if window is closed without submitting
    def on_close():
        nonlocal duration_submitted
        if not duration_submitted:
            logger.debug(f"Test report window for {serial_number} closed without submitting; timer reset")
        test_window.destroy()

    test_window.protocol("WM_DELETE_WINDOW", on_close)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_combined_assembler_tester_dashboard(root, "testuser", "Assembler_Tester", lambda: print("Logout"))
    root.mainloop()