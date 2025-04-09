import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap import Style
from PIL import Image, ImageTk
import pyodbc
import os
import sys
from datetime import datetime
import json
import threading
from utils.config import get_logger
from export_utils import send_email, generate_pdf_notification, generate_pump_details_table
from database import get_db_connection, create_pump

logger = get_logger("dashboard_gui")

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
ASSEMBLY_PART_NUMBERS_PATH = os.path.join(BASE_DIR, "assets", "assembly_part_numbers.json")
BUILD_NUMBER = "1.0.0"
STORES_EMAIL = "stores@guth.co.za"

def load_config():
    """Load configuration from config.json, creating it with defaults if missing."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
            logger.info(f"Loaded user config from {CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Failed to load user config from {CONFIG_PATH}: {str(e)}")
            config = {}
    else:
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

    config.setdefault("document_dirs", {
        "certificate": os.path.join(BASE_DIR, "certificates"),
        "bom": os.path.join(BASE_DIR, "boms"),
        "confirmation": os.path.join(BASE_DIR, "confirmations"),
        "reports": os.path.join(BASE_DIR, "reports"),
        "excel_exports": os.path.join(BASE_DIR, "exports")
    })

    if not os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=4)
            logger.info(f"Created default config file at {CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Failed to create default config at {CONFIG_PATH}: {str(e)}")

    return config

def load_options(file_path=OPTIONS_PATH, key=""):
    """Load options from a JSON file."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            return data.get(key, data) if key else data
    except Exception as e:
        logger.error(f"Failed to load options from {file_path}: {str(e)}")
        return []

def load_assembly_part_numbers():
    """Load assembly part numbers from JSON file."""
    return load_options(ASSEMBLY_PART_NUMBERS_PATH, "assembly_part_numbers")

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

def generate_bom_checklist(serial_number, bom_items, output_path):
    """Generate a BOM checklist PDF."""
    title = f"BOM Checklist - Pump {serial_number}"
    data = {
        "bom_items": bom_items,
        "instructions": "Tick the 'Check' column as you pull each item.",
        "generated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        generate_pdf_notification(serial_number, data, title=title, output_path=output_path)
        logger.info(f"BOM checklist PDF generated at {output_path}")
    except Exception as e:
        logger.error(f"Failed to generate BOM checklist PDF: {str(e)}")
        raise

def check_stores_minimum_quantity():
    """Placeholder to check Stores minimum pump quantities."""
    logger.debug("check_stores_minimum_quantity called (placeholder)")
    pass

def show_dashboard(root, username, role, logout_callback):
    """Display the Pump Originator dashboard."""
    root.state('zoomed')
    for widget in root.winfo_children():
        widget.destroy()

    options = load_options()
    assembly_part_numbers = load_assembly_part_numbers()
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
            logger.error(f"Dashboard logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Create new pump assemblies and view all pumps.", font=("Roboto", 12)).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Create New Pump Assembly", font=("Roboto", 16, "bold")).pack(pady=10)

    form_frame = ttk.LabelFrame(main_frame, text="New Pump Details", padding=10, bootstyle="default")
    form_frame.pack(fill=X, padx=10, pady=5)

    fields = [
        ("Customer", "entry", None, True),
        ("Branch", "combobox", options["branch"], True),
        ("Assembly Part Number", "entry", None, True),
        ("Pump Model", "combobox", options["pump_model"], True),
        ("Configuration", "combobox", options["configuration"], True),
        ("Impeller Size", "combobox", None, True),
        ("Connection Type", "combobox", options["connection_type"], True),
        ("Pressure Required", "entry", None, True),
        ("Flow Rate Required", "entry", None, True),
        ("Custom Motor", "entry", None, False),
        ("Flush Seal Housing", "checkbutton", None, False),
        ("Send to Stores", "checkbutton", None, False)
    ]
    entries = {}
    custom_impeller_entry = ttk.Entry(form_frame, font=("Roboto", 10))
    custom_impeller_entry.grid(row=fields.index(("Impeller Size", "combobox", None, True)), column=2, pady=3, padx=5, sticky=EW)
    custom_impeller_entry.grid_remove()

    other_entry = ttk.Entry(form_frame, font=("Roboto", 10), state="disabled")
    other_entry.grid(row=fields.index(("Connection Type", "combobox", options["connection_type"], True)), column=2, pady=3, sticky=EW)
    other_entry.grid_remove()

    tooltips = {
        "customer": "Select the customer branch for this pump",
        "branch": "Select the branch responsible for this pump",
        "assembly part number": "Enter the assembly part number for this pump",
        "pump model": "Select the pump model based on power rating",
        "configuration": "Choose the pump configuration type",
        "impeller size": "Choose the impeller size or enter a custom size if 'Other' is selected",
        "connection type": "Select the type of connection or enter a custom type if 'Other' is selected",
        "pressure required": "Enter the required pressure (e.g., 5 bar)",
        "flow rate required": "Enter the required flow rate (e.g., 10 L/min)",
        "custom motor": "Enter details if a custom motor is required",
        "flush seal housing": "Check if flush seal housing is required",
        "send to stores": "Check to send this pump directly to Stores upon creation"
    }

    for i, (label, widget_type, opts, required) in enumerate(fields):
        label_widget = ttk.Label(form_frame, text=f"{label}{' *' if required else ''}:", font=("Roboto", 10))
        label_widget.grid(row=i, column=0, pady=3, sticky=W)
        CustomTooltip(label_widget, tooltips[label.lower()])

        if widget_type == "entry":
            entry = ttk.Entry(form_frame, font=("Roboto", 10))
        elif widget_type == "combobox":
            if label == "Pump Model":
                pump_model_combobox = ttk.Combobox(form_frame, values=opts, font=("Roboto", 10), state="readonly")
                pump_model_combobox.set(opts[0])
                entry = pump_model_combobox
            elif label == "Configuration":
                configuration_combobox = ttk.Combobox(form_frame, values=opts, font=("Roboto", 10), state="readonly")
                configuration_combobox.set(opts[0])
                entry = configuration_combobox
            elif label == "Impeller Size":
                impeller_combobox = ttk.Combobox(form_frame, font=("Roboto", 10), state="readonly")
                initial_pump_model = pump_model_combobox.get()
                impeller_opts = options["impeller_size"].get(initial_pump_model, []) + ["Other"]
                impeller_combobox["values"] = impeller_opts
                impeller_combobox.set(impeller_opts[0])

                def on_pump_model_select(event):
                    selected_pump_model = pump_model_combobox.get()
                    new_impeller_opts = options["impeller_size"].get(selected_pump_model, []) + ["Other"]
                    impeller_combobox["values"] = new_impeller_opts
                    impeller_combobox.set(new_impeller_opts[0])
                    custom_impeller_entry.grid_remove()

                def on_impeller_select(event):
                    if impeller_combobox.get() == "Other":
                        custom_impeller_entry.grid()
                    else:
                        custom_impeller_entry.grid_remove()

                pump_model_combobox.bind("<<ComboboxSelected>>", on_pump_model_select)
                impeller_combobox.bind("<<ComboboxSelected>>", on_impeller_select)
                entry = impeller_combobox
            elif label == "Connection Type":
                connection_opts = opts + ["Other"] if "Other" not in opts else opts
                connection_combobox = ttk.Combobox(form_frame, values=connection_opts, font=("Roboto", 10), state="readonly")
                connection_combobox.set(connection_opts[0] if connection_opts[0] != "Other" else connection_opts[1] if len(connection_opts) > 1 else "")

                def on_connection_select(event):
                    if connection_combobox.get() == "Other":
                        other_entry.grid()
                        other_entry.configure(state="normal")
                    else:
                        other_entry.grid_remove()
                        other_entry.configure(state="disabled")

                connection_combobox.bind("<<ComboboxSelected>>", on_connection_select)
                entry = connection_combobox
            else:
                entry = ttk.Combobox(form_frame, values=opts, font=("Roboto", 10), state="readonly")
                entry.set(opts[0])
        elif widget_type == "checkbutton":
            entry = ttk.Checkbutton(form_frame, text="", bootstyle="success-round-toggle")
        entry.grid(row=i, column=1, pady=3, sticky=EW)
        entries[label.lower().replace(" ", "_")] = entry

    # Auto-populate Pump Model and Configuration based on Assembly Part Number
    assembly_part_entry = entries["assembly_part_number"]
    assembly_part_mapping = options.get("assembly_part_mapping", {})

    def on_assembly_part_change(event):
        part_number = assembly_part_entry.get().strip()
        mapping = assembly_part_mapping.get(part_number, None)
        if mapping:
            pump_model_combobox.set(mapping["pump_model"])
            configuration_combobox.set(mapping["configuration"])
            # Trigger impeller size update
            selected_pump_model = pump_model_combobox.get()
            new_impeller_opts = options["impeller_size"].get(selected_pump_model, []) + ["Other"]
            impeller_combobox["values"] = new_impeller_opts
            impeller_combobox.set(new_impeller_opts[0])
            custom_impeller_entry.grid_remove()
        else:
            # Reset to default if no mapping found, but allow manual selection
            pump_model_combobox.set(options["pump_model"][0])
            configuration_combobox.set(options["configuration"][0])
            selected_pump_model = pump_model_combobox.get()
            new_impeller_opts = options["impeller_size"].get(selected_pump_model, []) + ["Other"]
            impeller_combobox["values"] = new_impeller_opts
            impeller_combobox.set(new_impeller_opts[0])
            custom_impeller_entry.grid_remove()

    assembly_part_entry.bind("<KeyRelease>", on_assembly_part_change)

    # Handle "Send to Stores" toggle
    customer_entry = entries["customer"]
    send_to_stores_check = entries["send_to_stores"]
    send_to_stores_check.configure(command=lambda: (customer_entry.configure(state="disabled"), customer_entry.delete(0, END), customer_entry.insert(0, "Stores")) if send_to_stores_check.instate(['selected']) else (customer_entry.configure(state="normal"), customer_entry.delete(0, END)))

    form_frame.grid_columnconfigure(1, weight=1)
    error_label = ttk.Label(form_frame, text="", font=("Roboto", 10), bootstyle="danger")
    error_label.grid(row=len(fields), column=0, columnspan=2, pady=3)

    def submit_pump():
        """Create a new pump assembly and notify Stores if applicable."""
        global pyodbc
        try:
            import pyodbc  # Force re-import to ensure it’s available
            logger.debug("pyodbc re-imported in submit_pump successfully")
        except ImportError as e:
            logger.error(f"Failed to re-import pyodbc in submit_pump: {str(e)}")
            raise
        except NameError as e:
            logger.error(f"pyodbc NameError in submit_pump before use: {str(e)}")
            raise

        data = {key: entry.get().strip() if isinstance(entry, (ttk.Entry, ttk.Combobox)) else "Yes" if entry.instate(['selected']) else "No" for key, entry in entries.items()}
        if data["connection_type"] == "Other":
            data["connection_type"] = other_entry.get().strip() or (error_label.config(text="Please enter a custom connection type.") and None) or None
            if not data["connection_type"]:
                return
        if data["impeller_size"] == "Other":
            data["impeller_size"] = custom_impeller_entry.get().strip() or (error_label.config(text="Please enter a custom impeller size.") and None) or None
            if not data["impeller_size"]:
                return

        if data["send_to_stores"] == "Yes":
            data["customer"] = "Stores"

        required_fields = ["pump_model", "configuration", "customer", "branch", "assembly_part_number", "pressure_required", "flow_rate_required", "impeller_size", "connection_type"]
        missing = [field.replace("_", " ").title() for field in required_fields if not data[field]]
        if missing:
            error_label.config(text=f"Missing required fields: {', '.join(missing)}")
            return

        try:
            pressure_required, flow_rate_required = float(data["pressure_required"]), float(data["flow_rate_required"])
            if pressure_required < 0 or flow_rate_required < 0:
                error_label.config(text="Pressure and Flow Rate must be non-negative")
                return
        except ValueError:
            error_label.config(text="Pressure and Flow Rate must be numeric")
            return

        try:
            logger.debug("Attempting to get database connection in submit_pump")
            with get_db_connection() as conn:
                logger.debug("Database connection obtained in submit_pump")
                cursor = conn.cursor()
                serial = create_pump(
                    cursor,
                    data["pump_model"],
                    data["configuration"],
                    data["customer"],
                    username,
                    data["branch"],
                    data["impeller_size"],
                    data["connection_type"],
                    pressure_required,
                    flow_rate_required,
                    data["custom_motor"],
                    data["flush_seal_housing"],
                    data["assembly_part_number"],
                    insert_bom=True
                )
                cursor.execute("SELECT part_code, part_name, quantity FROM bom_items WHERE serial_number = ?", (serial,))
                bom_items = [{"part_code": row[0], "part_name": row[1], "quantity": row[2]} for row in cursor.fetchall()]
                conn.commit()
                logger.info(f"New pump created by {username}: {serial} with BOM")

            pump_data = {
                "serial_number": serial,
                "assembly_part_number": data["assembly_part_number"],
                "customer": data["customer"],
                "branch": data["branch"],
                "pump_model": data["pump_model"],
                "configuration": data["configuration"],
                "impeller_size": data["impeller_size"],
                "connection_type": data["connection_type"],
                "pressure_required": data["pressure_required"],
                "flow_rate_required": data["flow_rate_required"],
                "custom_motor": data["custom_motor"],
                "flush_seal_housing": data["flush_seal_housing"],
                "requested_by": username
            }
            logger.debug(f"pump_data: {pump_data}")

            config = load_config()
            notifications_dir = os.path.join(BASE_DIR, "docs", "Notifications")
            os.makedirs(notifications_dir, exist_ok=True)
            for dir_key in ["confirmation", "bom"]:
                dir_path = config["document_dirs"][dir_key]
                os.makedirs(dir_path, exist_ok=True)

            pdf_path = os.path.join(notifications_dir, f"new_pump_notification_{serial}.pdf")
            bom_pdf_path = os.path.join(config["document_dirs"]["bom"], f"bom_checklist_{serial}.pdf")
            confirmation_path = os.path.join(config["document_dirs"]["confirmation"], f"confirmation_pump_created_{serial}.pdf")

            logger.debug(f"Generating PDF at {pdf_path}")
            generate_pdf_notification(serial, pump_data, title="New Pump Assembly Notification", output_path=pdf_path)
            os.startfile(pdf_path, "print")
            logger.debug(f"Generating BOM PDF at {bom_pdf_path}")
            generate_bom_checklist(serial, bom_items, output_path=bom_pdf_path)
            os.startfile(bom_pdf_path, "print")
            logger.debug(f"Generating confirmation PDF at {confirmation_path}")
            confirmation_data = {"serial_number": serial, "assembly_part_number": data["assembly_part_number"], "status": "Created", "created_by": username, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            generate_pdf_notification(serial, confirmation_data, title=f"Confirmation - Pump Created {serial}", output_path=confirmation_path)

            subject = f"New Pump Assembly Created: {serial}"
            body_content = f"""
                <p>A new pump assembly has been created and requires stock to be booked out of Sage and pulled.</p>
                <h3 style="color: #34495e;">Pump Details</h3>
                {generate_pump_details_table(pump_data)}
                <p>The BOM checklist is attached.</p>
            """
            logger.debug(f"Sending email to {STORES_EMAIL} with subject: {subject}")
            threading.Thread(target=send_email, args=(STORES_EMAIL, subject, "Dear Stores Team,", body_content, "Regards,<br>Guth Pump Registry", pdf_path, confirmation_path, bom_pdf_path), daemon=True).start()

            if data["send_to_stores"] == "Yes":
                check_stores_minimum_quantity()

            error_label.config(text="Pump created successfully!", bootstyle="success")
            refresh_all_pumps()
            refresh_stores_pumps()
        except Exception as e:
            logger.error(f"Failed to create pump: {str(e)}", exc_info=True)
            Messagebox.show_error("Error", f"Failed to create pump: {str(e)}")

    ttk.Button(form_frame, text="Submit", command=submit_pump, bootstyle="success", style="large.TButton").grid(row=len(fields) + 1, column=0, pady=5, padx=5, sticky=W)
    ttk.Button(form_frame, text="Logoff", command=logout_callback, bootstyle="secondary", style="large.TButton").grid(row=len(fields) + 1, column=1, pady=5, padx=5, sticky=W)

    style = Style()
    style.configure("Custom.TNotebook.Tab", background="#007bff", foreground="white", padding=[10, 5])
    style.map("Custom.TNotebook.Tab", background=[("selected", style.lookup("TNotebook.Tab", "background"))], foreground=[("selected", style.lookup("TNotebook.Tab", "foreground"))])

    notebook = ttk.Notebook(main_frame, style="Custom.TNotebook")
    notebook.pack(fill=BOTH, expand=True, pady=10)

    all_pumps_tab = ttk.Frame(notebook)
    notebook.add(all_pumps_tab, text="All Pumps")
    all_pumps_frame = ttk.LabelFrame(all_pumps_tab, text="All Pumps", padding=10)
    all_pumps_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    search_filter_frame_all = ttk.Frame(all_pumps_frame)
    search_filter_frame_all.pack(fill=X, pady=(0, 5))
    ttk.Label(search_filter_frame_all, text="Search by Serial Number:", font=("Roboto", 10)).pack(side=LEFT, padx=5)
    search_entry_all = ttk.Entry(search_filter_frame_all, font=("Roboto", 10), width=20)
    search_entry_all.pack(side=LEFT, padx=5)
    CustomTooltip(search_entry_all, "Enter a serial number to search (partial matches allowed)")
    ttk.Label(search_filter_frame_all, text="Filter by Status:", font=("Roboto", 10)).pack(side=LEFT, padx=5)
    filter_combobox_all = ttk.Combobox(search_filter_frame_all, values=["All", "Stores", "Assembler", "Testing", "Pending Approval", "Completed"], font=("Roboto", 10), state="readonly")
    filter_combobox_all.set("All")
    filter_combobox_all.pack(side=LEFT, padx=5)
    CustomTooltip(filter_combobox_all, "Filter pumps by their current status")

    columns = ("Serial Number", "Assembly Part Number", "Customer", "Branch", "Pump Model", "Configuration", "Impeller Size", "Connection Type",
               "Pressure Required", "Flow Rate Required", "Custom Motor", "Flush Seal Housing", "Status")
    all_pumps_tree = ttk.Treeview(all_pumps_frame, columns=columns, show="headings", height=12)
    for col in columns:
        all_pumps_tree.heading(col, text=col, anchor=W)
        all_pumps_tree.column(col, width=120, anchor=W)
    all_pumps_tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar_all = ttk.Scrollbar(all_pumps_frame, orient=VERTICAL, command=all_pumps_tree.yview)
    scrollbar_all.pack(side=RIGHT, fill=Y)
    all_pumps_tree.configure(yscrollcommand=scrollbar_all.set)

    def refresh_all_pumps():
        """Refresh the All Pumps table with search and filter."""
        all_pumps_tree.delete(*all_pumps_tree.get_children())
        search_term = search_entry_all.get().lower()
        filter_status = filter_combobox_all.get()
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT serial_number, assembly_part_number, customer, branch, pump_model, configuration, impeller_size, connection_type,
                           pressure_required, flow_rate_required, custom_motor, flush_seal_housing, status
                    FROM pumps
                """
                params = []
                if filter_status != "All":
                    query += " WHERE status = ?"
                    params.append(filter_status)
                cursor.execute(query, params)
                for pump in cursor.fetchall():
                    if search_term in pump[0].lower():
                        all_pumps_tree.insert("", END, values=(pump[0], pump[1] or "N/A", pump[2], pump[3], pump[4], pump[5], pump[6], pump[7], pump[8], pump[9], pump[10], pump[11], pump[12]))
            logger.info("Refreshed All Pumps table")
        except Exception as e:
            logger.error(f"Failed to refresh all pumps: {str(e)}")
            Messagebox.show_error("Error", f"Failed to load pumps: {str(e)}")

    search_entry_all.bind("<KeyRelease>", lambda event: refresh_all_pumps())
    filter_combobox_all.bind("<<ComboboxSelected>>", lambda event: refresh_all_pumps())

    stores_tab = ttk.Frame(notebook)
    notebook.add(stores_tab, text="Pumps in Stores")
    stores_frame = ttk.LabelFrame(stores_tab, text="Pumps in Stores", padding=10)
    stores_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    search_filter_frame_stores = ttk.Frame(stores_frame)
    search_filter_frame_stores.pack(fill=X, pady=(0, 5))
    ttk.Label(search_filter_frame_stores, text="Search by Serial Number:", font=("Roboto", 10)).pack(side=LEFT, padx=5)
    search_entry_stores = ttk.Entry(search_filter_frame_stores, font=("Roboto", 10), width=20)
    search_entry_stores.pack(side=LEFT, padx=5)
    CustomTooltip(search_entry_stores, "Enter a serial number to search (partial matches allowed)")
    ttk.Label(search_filter_frame_stores, text="Filter by Branch:", font=("Roboto", 10)).pack(side=LEFT, padx=5)
    filter_combobox_stores = ttk.Combobox(search_filter_frame_stores, values=["All"] + options["branch"], font=("Roboto", 10), state="readonly")
    filter_combobox_stores.set("All")
    filter_combobox_stores.pack(side=LEFT, padx=5)
    CustomTooltip(filter_combobox_stores, "Filter pumps by branch")

    stores_tree = ttk.Treeview(stores_frame, columns=columns, show="headings", height=12)
    for col in columns:
        stores_tree.heading(col, text=col, anchor=W)
        stores_tree.column(col, width=120, anchor=W)
    stores_tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar_stores = ttk.Scrollbar(stores_frame, orient=VERTICAL, command=stores_tree.yview)
    scrollbar_stores.pack(side=RIGHT, fill=Y)
    stores_tree.configure(yscrollcommand=scrollbar_stores.set)

    def refresh_stores_pumps():
        """Refresh the Pumps in Stores table with search and filter, showing only pumps with customer = 'Stores'."""
        stores_tree.delete(*stores_tree.get_children())
        search_term = search_entry_stores.get().lower()
        filter_branch = filter_combobox_stores.get()
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT serial_number, assembly_part_number, customer, branch, pump_model, configuration, impeller_size, connection_type,
                           pressure_required, flow_rate_required, custom_motor, flush_seal_housing, status
                    FROM pumps WHERE customer = 'Stores'
                """
                params = []
                if filter_branch != "All":
                    query += " AND branch = ?"
                    params.append(filter_branch)
                cursor.execute(query, params)
                for pump in cursor.fetchall():
                    if search_term in pump[0].lower():
                        stores_tree.insert("", END, values=(pump[0], pump[1] or "N/A", pump[2], pump[3], pump[4], pump[5], pump[6], pump[7], pump[8], pump[9], pump[10], pump[11], pump[12]))
            logger.info("Refreshed Pumps in Stores table")
            check_stores_minimum_quantity()
        except Exception as e:
            logger.error(f"Failed to refresh stores pumps: {str(e)}")
            Messagebox.show_error("Error", f"Failed to load pumps: {str(e)}")

    search_entry_stores.bind("<KeyRelease>", lambda event: refresh_stores_pumps())
    filter_combobox_stores.bind("<<ComboboxSelected>>", lambda event: refresh_stores_pumps())

    refresh_all_pumps()
    refresh_stores_pumps()

    all_pumps_tree.bind("<Double-1>", lambda event: edit_pump_window(main_frame, all_pumps_tree, root, username, role, logout_callback))
    stores_tree.bind("<Double-1>", lambda event: edit_pump_window(main_frame, stores_tree, root, username, role, logout_callback))

    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=5, fill=X)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(expand=True)
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack(expand=True)

    return main_frame

def edit_pump_window(parent_frame, tree, root, username, role, logout_callback):
    """Edit or retest a pump record."""
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
    except Exception as e:
        logger.error(f"Failed to load pump data: {str(e)}")
        Messagebox.show_error("Error", f"Failed to load pump: {str(e)}")
        return

    edit_window = ttk.Toplevel(parent_frame)
    edit_window.title(f"Edit Pump {serial_number}")
    edit_window.geometry("702x810")

    header_frame = ttk.Frame(edit_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.65), int(Image.open(LOGO_PATH).height * 0.65)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
        except Exception as e:
            logger.error(f"Edit pump logo load failed: {str(e)}")
    ttk.Label(header_frame, text="View or edit pump details.", font=("Roboto", 12)).pack(anchor=W, padx=10)

    frame = ttk.Frame(edit_window, padding=20)
    frame.pack(fill=BOTH, expand=True)

    options = load_options()
    assembly_part_numbers = load_assembly_part_numbers()
    fields = [
        ("serial_number", "entry", None),
        ("customer", "entry", None),
        ("branch", "combobox", options["branch"]),
        ("assembly_part_number", "entry", None),
        ("pump_model", "combobox", options["pump_model"]),
        ("configuration", "combobox", options["configuration"]),
        ("impeller_size", "combobox", None),
        ("connection_type", "combobox", options["connection_type"]),
        ("pressure_required", "entry", None),
        ("flow_rate_required", "entry", None),
        ("custom_motor", "entry", None),
        ("flush_seal_housing", "checkbutton", None)
    ]
    entries = {}
    custom_impeller_entry = ttk.Entry(frame, font=("Roboto", 12))
    custom_impeller_entry.grid(row=fields.index(("impeller_size", "combobox", None)), column=2, pady=5, padx=5, sticky=EW)
    if pump.get("impeller_size") not in options["impeller_size"].get(pump.get("pump_model", "P1 3.0KW"), []):
        custom_impeller_entry.insert(0, pump.get("impeller_size", ""))
    custom_impeller_entry.grid_remove()

    assembly_part_mapping = options.get("assembly_part_mapping", {})

    for i, (field, widget_type, opts) in enumerate(fields):
        ttk.Label(frame, text=f"{field.replace('_', ' ').title()}:", font=("Roboto", 14)).grid(row=i, column=0, pady=5, sticky=W)
        value = pump.get(field, "")
        if widget_type == "entry":
            entry = ttk.Entry(frame, font=("Roboto", 12))
            entry.insert(0, value if value else "")
            if field == "serial_number":
                entry.configure(state="readonly")
        elif widget_type == "combobox":
            if field == "pump_model":
                pump_model_combobox = ttk.Combobox(frame, values=opts, font=("Roboto", 12), state="readonly")
                pump_model_combobox.set(value if value in opts else opts[0])
                entry = pump_model_combobox
            elif field == "configuration":
                entry = ttk.Combobox(frame, values=opts, font=("Roboto", 12), state="readonly")
                entry.set(value if value in opts else opts[0])
            elif field == "impeller_size":
                impeller_combobox = ttk.Combobox(frame, font=("Roboto", 12), state="readonly")
                initial_pump_model = pump.get("pump_model", "P1 3.0KW")
                impeller_opts = options["impeller_size"].get(initial_pump_model, []) + ["Other"]
                impeller_combobox["values"] = impeller_opts
                impeller_combobox.set(value if value in impeller_opts else "Other" if value else impeller_opts[0])
                if impeller_combobox.get() == "Other":
                    custom_impeller_entry.grid()

                def on_pump_model_select(event):
                    selected_pump_model = pump_model_combobox.get()
                    new_impeller_opts = options["impeller_size"].get(selected_pump_model, []) + ["Other"]
                    impeller_combobox["values"] = new_impeller_opts
                    impeller_combobox.set(new_impeller_opts[0])
                    custom_impeller_entry.grid_remove()

                def on_impeller_select(event):
                    if impeller_combobox.get() == "Other":
                        custom_impeller_entry.grid()
                    else:
                        custom_impeller_entry.grid_remove()

                pump_model_combobox.bind("<<ComboboxSelected>>", on_pump_model_select)
                impeller_combobox.bind("<<ComboboxSelected>>", on_impeller_select)
                entry = impeller_combobox
            elif field == "connection_type":
                connection_opts = opts + ["Other"] if "Other" not in opts else opts
                entry = ttk.Combobox(frame, values=connection_opts, font=("Roboto", 12), state="readonly")
                entry.set(value if value in connection_opts else connection_opts[0] if connection_opts[0] != "Other" else connection_opts[1] if len(connection_opts) > 1 else "")
            else:
                entry = ttk.Combobox(frame, values=opts, font=("Roboto", 12), state="readonly")
                entry.set(value if value in opts else opts[0])
        elif widget_type == "checkbutton":
            entry = ttk.Checkbutton(frame, text="", bootstyle="success-round-toggle")
            entry.state(['selected'] if value == "Yes" else ['!selected'])
        entry.grid(row=i, column=1, pady=5, sticky=EW)
        entries[field] = entry

    # Auto-populate Pump Model and Configuration in edit window
    assembly_part_entry = entries["assembly_part_number"]
    def on_assembly_part_change_edit(event):
        part_number = assembly_part_entry.get().strip()
        mapping = assembly_part_mapping.get(part_number, None)
        if mapping:
            pump_model_combobox.set(mapping["pump_model"])
            entries["configuration"].set(mapping["configuration"])
            selected_pump_model = pump_model_combobox.get()
            new_impeller_opts = options["impeller_size"].get(selected_pump_model, []) + ["Other"]
            impeller_combobox["values"] = new_impeller_opts
            impeller_combobox.set(new_impeller_opts[0])
            custom_impeller_entry.grid_remove()

    assembly_part_entry.bind("<KeyRelease>", on_assembly_part_change_edit)

    frame.grid_columnconfigure(1, weight=1)

    def save_changes():
        """Save changes to the pump record."""
        data = {key: entry.get() if isinstance(entry, (ttk.Entry, ttk.Combobox)) else "Yes" if entry.instate(['selected']) else "No" for key, entry in entries.items()}
        if data["impeller_size"] == "Other":
            data["impeller_size"] = custom_impeller_entry.get().strip()
            if not data["impeller_size"]:
                Messagebox.show_error("Error", "Please enter a custom impeller size.")
                return
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE pumps 
                    SET pump_model = ?, configuration = ?, customer = ?, branch = ?, impeller_size = ?, 
                        connection_type = ?, pressure_required = ?, flow_rate_required = ?, custom_motor = ?, 
                        flush_seal_housing = ?, assembly_part_number = ?
                    WHERE serial_number = ?
                """, (data["pump_model"], data["configuration"], data["customer"], data["branch"], data["impeller_size"],
                      data["connection_type"], float(data["pressure_required"] or 0), float(data["flow_rate_required"] or 0),
                      data["custom_motor"], data["flush_seal_housing"], data["assembly_part_number"], serial_number))
                conn.commit()
                logger.info(f"Updated pump {serial_number} by {username}")
            show_dashboard(root, username, role, logout_callback)
            edit_window.destroy()
        except Exception as e:
            logger.error(f"Failed to save pump changes: {str(e)}")
            Messagebox.show_error("Error", f"Failed to save changes: {str(e)}")

    def retest_pump():
        """Set pump status to Testing and notify Stores."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE pumps SET status = 'Testing' WHERE serial_number = ?", (serial_number,))
                conn.commit()
                logger.info(f"Pump {serial_number} set to Testing for retest by {username}")

                config = load_config()
                confirmation_dir = config["document_dirs"]["confirmation"]
                os.makedirs(confirmation_dir, exist_ok=True)

                confirmation_path = os.path.join(confirmation_dir, f"confirmation_retest_{serial_number}.pdf")
                confirmation_data = {
                    "serial_number": serial_number,
                    "assembly_part_number": pump.get("assembly_part_number", "N/A"),
                    "status": "Sent for Retest",
                    "action_by": username,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                generate_pdf_notification(serial_number, confirmation_data, title=f"Confirmation - Retest {serial_number}", output_path=confirmation_path)
                logger.info(f"Saved retest confirmation to {confirmation_path}")

                subject = f"Pump {serial_number} Sent for Retest"
                body_content = f"""
                    <p>Pump {serial_number} has been sent for retesting.</p>
                    <h3 style="color: #34495e;">Pump Details</h3>
                    <table border="1" style="border-collapse: collapse;">
                        <tr><th>Serial Number</th><td>{serial_number}</td></tr>
                        <tr><th>Assembly Part Number</th><td>{pump.get('assembly_part_number', 'N/A')}</td></tr>
                        <tr><th>Customer</th><td>{pump['customer']}</td></tr>
                        <tr><th>Branch</th><td>{pump['branch']}</td></tr>
                        <tr><th>Pump Model</th><td>{pump['pump_model']}</td></tr>
                        <tr><th>Configuration</th><td>{pump['configuration']}</td></tr>
                    </table>
                """
                threading.Thread(target=send_email, args=(STORES_EMAIL, subject, "Dear Stores Team,", body_content, "Regards,<br>Guth Pump Registry", confirmation_path), daemon=True).start()

            show_dashboard(root, username, role, logout_callback)
            edit_window.destroy()
        except Exception as e:
            logger.error(f"Failed to retest pump: {str(e)}")
            Messagebox.show_error("Error", f"Failed to retest pump: {str(e)}")

    button_frame = ttk.Frame(frame)
    button_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)
    ttk.Button(button_frame, text="Save", command=save_changes, bootstyle="success", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Button(button_frame, text="Retest", command=retest_pump, bootstyle="warning", style="large.TButton").pack(side=LEFT, padx=5)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_dashboard(root, "testuser", "admin", lambda: print("Logged off"))
    root.mainloop()