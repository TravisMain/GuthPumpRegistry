import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from database import get_db_connection, create_pump
import os
import sys
import json
from utils.config import get_logger

logger = get_logger("pump_originator")

# Determine the base directory for bundled resources
if getattr(sys, 'frozen', False):
    # Running as a bundled executable (PyInstaller)
    BASE_DIR = sys._MEIPASS
else:
    # Running in development mode
    BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"

BUILD_NUMBER = "1.0.0"
OPTIONS_PATH = os.path.join(BASE_DIR, "assets", "pump_options.json")
ASSEMBLY_PART_NUMBERS_PATH = os.path.join(BASE_DIR, "assets", "assembly_part_numbers.json")

def load_options(file_path, key=""):
    """Load options from a JSON file."""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []
        with open(file_path, "r") as f:
            data = json.load(f)
            result = data.get(key, data) if key else data
            logger.debug(f"Loaded options from {file_path}: {result}")
            return result
    except Exception as e:
        logger.error(f"Failed to load options from {file_path}: {str(e)}")
        return []

def show_pump_originator_gui(root, username, logout_callback):
    """Display the Pump Originator GUI for creating pumps and viewing status."""
    root.state('zoomed')
    for widget in root.winfo_children():
        widget.destroy()

    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

    create_frame = ttk.LabelFrame(main_frame, text="Create New Pump", padding=10)
    create_frame.pack(fill=X, padx=10, pady=10)

    ttk.Label(create_frame, text="Create New Pump", font=("Helvetica", 16, "bold")).pack(pady=10)

    options = load_options(OPTIONS_PATH)
    assembly_part_numbers = load_options(ASSEMBLY_PART_NUMBERS_PATH, "assembly_part_numbers")

    # Log the loaded options for debugging
    logger.debug(f"Loaded options: {options}")
    logger.debug(f"Loaded assembly part numbers: {assembly_part_numbers}")

    # Check if options are empty and display an error if they are
    if not options or not assembly_part_numbers:
        ttk.Label(create_frame, text="Error: Failed to load pump options or assembly part numbers.", font=("Roboto", 12), bootstyle="danger").pack(pady=10)
        logger.error("Pump options or assembly part numbers are empty. Fields will not be rendered.")
        return main_frame

    fields = [
        ("Pump Model", ttk.Combobox, options.get("pump_model", []), "P1 3.0KW"),
        ("Configuration", ttk.Combobox, options.get("configuration", []), "Standard"),
        ("Customer", ttk.Entry, None, "Guth Test"),
        ("Branch", ttk.Combobox, options.get("branch", []), "Main"),
        ("Assembly Part Number", ttk.Combobox, assembly_part_numbers, assembly_part_numbers[0] if assembly_part_numbers else "N/A"),
        ("Pressure Required (bar)", ttk.Entry, None, ""),
        ("Flow Rate Required (L/h)", ttk.Entry, None, ""),
        ("Impeller Size", ttk.Combobox, options.get("impeller_size", {}).get("P1 3.0KW", []), "Medium"),
        ("Connection Type", ttk.Combobox, options.get("connection_type", []), "Flange"),
        ("Custom Motor", ttk.Entry, None, ""),
        ("Flush Seal Housing", ttk.Checkbutton, ["Yes", "No"], "No")
    ]
    entries = {}
    for i, (label, widget_type, opts, default) in enumerate(fields):
        ttk.Label(create_frame, text=f"{label}:").pack()
        if widget_type == ttk.Entry:
            entry = widget_type(create_frame)
            if default:
                entry.insert(0, default)
        elif widget_type == ttk.Combobox:
            entry = widget_type(create_frame, values=opts, state="readonly")
            entry.set(default if default in opts else opts[0] if opts else "N/A")
        elif widget_type == ttk.Checkbutton:
            var = ttk.BooleanVar(value=default == "Yes")
            entry = widget_type(create_frame, text="", variable=var, bootstyle="success-round-toggle")
            entries[label.lower().replace(" ", "_")] = var
            entry.pack(pady=5)
            continue
        entry.pack(pady=5)
        entries[label.lower().replace(" ", "_")] = entry

    status_label = ttk.Label(create_frame, text="", bootstyle=SUCCESS)
    status_label.pack(pady=10)

    def create():
        """Create a new pump with validated inputs."""
        data = {key: entry.get() if not isinstance(entry, ttk.BooleanVar) else "Yes" if entry.get() else "No" for key, entry in entries.items()}
        
        required_fields = ["pump_model", "configuration", "customer", "branch", "assembly_part_number", "pressure_required", "flow_rate_required", "impeller_size", "connection_type"]
        missing = [field.replace("_", " ").title() for field in required_fields if not data[field]]
        if missing:
            Messagebox.show_error(f"Missing required fields: {', '.join(missing)}", "Validation Error")
            return

        try:
            pressure_required = float(data["pressure_required"])
            flow_rate_required = float(data["flow_rate_required"])
            if pressure_required < 0 or flow_rate_required < 0:
                Messagebox.show_error("Pressure Required and Flow Rate Required must be non-negative", "Validation Error")
                return
        except ValueError:
            Messagebox.show_error("Pressure Required and Flow Rate Required must be numeric", "Validation Error")
            return

        try:
            with get_db_connection() as conn:
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
                conn.commit()
            status_label.config(text=f"Created S/N: {serial}")
            logger.info(f"Pump {serial} created by {username}")
            refresh_stores_pumps()
            refresh_all_pumps()
        except Exception as e:
            logger.error(f"Failed to create pump: {str(e)}")
            Messagebox.show_error("Error", f"Failed to create pump: {str(e)}")

    ttk.Button(create_frame, text="Create Pump", command=create, bootstyle=SUCCESS).pack(pady=20)

    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill=BOTH, expand=True, pady=10)

    all_pumps_tab = ttk.Frame(notebook)
    notebook.add(all_pumps_tab, text="All Pumps")
    all_pumps_frame = ttk.LabelFrame(all_pumps_tab, text="All Pumps", padding=10)
    all_pumps_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    columns = ("Serial Number", "Assembly Part Number", "Customer", "Branch", "Pump Model", "Configuration", "Created At", "Status", "Pressure Required", "Flow Rate Required")
    all_pumps_tree = ttk.Treeview(all_pumps_frame, columns=columns, show="headings", height=15)
    for col in columns:
        all_pumps_tree.heading(col, text=col, anchor=W)
        all_pumps_tree.column(col, width=150, anchor=W)
    all_pumps_tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar_all = ttk.Scrollbar(all_pumps_frame, orient=VERTICAL, command=all_pumps_tree.yview)
    scrollbar_all.pack(side=RIGHT, fill=Y)
    all_pumps_tree.configure(yscrollcommand=scrollbar_all.set)

    def refresh_all_pumps():
        """Refresh the All Pumps table."""
        all_pumps_tree.delete(*all_pumps_tree.get_children())
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT serial_number, assembly_part_number, customer, branch, pump_model, configuration, created_at, status, pressure_required, flow_rate_required
                    FROM pumps
                """)
                for pump in cursor.fetchall():
                    # pump is a tuple: (serial_number, assembly_part_number, customer, branch, pump_model, configuration, created_at, status, pressure_required, flow_rate_required)
                    all_pumps_tree.insert("", END, values=(pump[0], pump[1] or "N/A", pump[2], pump[3], pump[4], pump[5], pump[6], pump[7], pump[8], pump[9]))
            logger.info("Refreshed All Pumps table")
        except Exception as e:
            logger.error(f"Failed to refresh all pumps: {str(e)}")
            Messagebox.show_error("Error", f"Failed to load pumps: {str(e)}")

    refresh_all_pumps()
    ttk.Button(all_pumps_frame, text="Refresh", command=refresh_all_pumps, bootstyle="info", style="large.TButton").pack(pady=5)

    stores_tab = ttk.Frame(notebook)
    notebook.add(stores_tab, text="Pumps in Stores")
    stores_frame = ttk.LabelFrame(stores_tab, text="Pumps in Stores", padding=10)
    stores_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    stores_tree = ttk.Treeview(stores_frame, columns=columns, show="headings", height=15)
    for col in columns:
        stores_tree.heading(col, text=col, anchor=W)
        stores_tree.column(col, width=150, anchor=W)
    stores_tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar_stores = ttk.Scrollbar(stores_frame, orient=VERTICAL, command=stores_tree.yview)
    scrollbar_stores.pack(side=RIGHT, fill=Y)
    stores_tree.configure(yscrollcommand=scrollbar_stores.set)

    def refresh_stores_pumps():
        """Refresh the Pumps in Stores table."""
        stores_tree.delete(*stores_tree.get_children())
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT serial_number, assembly_part_number, customer, branch, pump_model, configuration, created_at, status, pressure_required, flow_rate_required
                    FROM pumps WHERE status = 'Stores'
                """)
                for pump in cursor.fetchall():
                    # pump is a tuple: (serial_number, assembly_part_number, customer, branch, pump_model, configuration, created_at, status, pressure_required, flow_rate_required)
                    stores_tree.insert("", END, values=(pump[0], pump[1] or "N/A", pump[2], pump[3], pump[4], pump[5], pump[6], pump[7], pump[8], pump[9]))
            logger.info("Refreshed Pumps in Stores table")
        except Exception as e:
            logger.error(f"Failed to refresh stores pumps: {str(e)}")
            Messagebox.show_error("Error", f"Failed to load pumps: {str(e)}")

    refresh_stores_pumps()
    ttk.Button(stores_frame, text="Refresh", command=refresh_stores_pumps, bootstyle="info", style="large.TButton").pack(pady=5)

    ttk.Button(main_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=10)
    ttk.Label(main_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(main_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_pump_originator_gui(root, "testuser", lambda: print("Logout"))
    root.mainloop()