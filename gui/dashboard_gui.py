# dashboard_gui.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox  # For error messages
from ttkbootstrap import Style  # For custom styling
from PIL import Image, ImageTk
from database import connect_db, create_pump
import os
from datetime import datetime
import json
import threading
import sqlite3
from utils.config import get_logger
from export_utils import send_email, generate_pdf_notification, generate_pump_details_table

logger = get_logger("dashboard_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
OPTIONS_PATH = os.path.join(BASE_DIR, "assets", "pump_options.json")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
BUILD_NUMBER = "1.0.0"
STORES_EMAIL = "stores@guth.co.za"  # Update as needed

# Default directories if not specified in config
DEFAULT_DIRS = {
    "certificate": os.path.join(BASE_DIR, "certificates"),
    "bom": os.path.join(BASE_DIR, "boms"),
    "confirmation": os.path.join(BASE_DIR, "confirmations"),
    "reports": os.path.join(BASE_DIR, "reports"),
    "excel_exports": os.path.join(BASE_DIR, "exports")
}

def load_config():
    """Load configuration from config.json, or create it with defaults if it doesn't exist."""
    if not os.path.exists(CONFIG_PATH):
        # Create default config
        config = {"document_dirs": DEFAULT_DIRS}
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        logger.info(f"Created default config file at {CONFIG_PATH}")
        return config
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    # Ensure all required keys exist
    if "document_dirs" not in config:
        config["document_dirs"] = DEFAULT_DIRS
    for key, default_path in DEFAULT_DIRS.items():
        if key not in config["document_dirs"]:
            config["document_dirs"][key] = default_path
    return config

# Custom Tooltip class to replace ttkbootstrap.Tooltip
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
        self.tooltip_window.wm_overrideredirect(True)  # Remove window decorations
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

def generate_bom_checklist(serial_number, bom_items, output_path):
    """
    Generate a BOM checklist PDF for the given serial number and BOM items.
    The checklist will have a table with columns: Item, Quantity, Check.
    """
    title = f"BOM Checklist - Pump {serial_number}"
    logger.debug(f"Generating BOM checklist for serial_number: {serial_number}, bom_items: {bom_items}")

    # Prepare data for the PDF
    data = {
        "bom_items": bom_items,  # Pass the raw BOM items list
        "instructions": "Tick the 'Check' column as you pull each item.",
        "generated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        generate_pdf_notification(serial_number, data, title=title, output_path=output_path)
        logger.info(f"BOM checklist PDF generated at {output_path}")
    except Exception as e:
        logger.error(f"Failed to generate BOM checklist PDF: {str(e)}")
        raise

def show_dashboard(root, username, role, logout_callback):
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
            # Increase size by 30% from 0.75 (0.75 * 1.3 = 0.975, round to 1.0)
            img_resized = img.resize((int(img.width * 1.0), int(img.height * 1.0)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            logo_label = ttk.Label(header_frame, image=logo)
            logo_label.image = logo
            logo_label.pack(side=RIGHT, padx=10)
        except Exception as e:
            logger.error(f"Dashboard logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Create new pump assemblies and view all pumps in the database.", font=("Roboto", 12)).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Create New Pump Assembly", font=("Roboto", 16, "bold")).pack(pady=10)

    # Form
    form_frame = ttk.LabelFrame(main_frame, text="New Pump Details", padding=10, bootstyle="default")
    form_frame.pack(fill=X, padx=10, pady=5)

    fields = [
        ("Customer", "entry", None, True),
        ("Branch", "combobox", options["branch"], True),
        ("Pump Model", "combobox", options["pump_model"], True),
        ("Configuration", "combobox", options["configuration"], True),
        ("Impeller Size", "combobox", None, True),  # Options will be set dynamically
        ("Connection Type", "combobox", options["connection_type"], True),
        ("Pressure Required", "entry", None, True),  # Now mandatory
        ("Flow Rate Required", "entry", None, True),  # Now mandatory
        ("Custom Motor", "entry", None, False),
        ("Flush Seal Housing", "checkbutton", None, False)
    ]
    entries = {}
    custom_impeller_entry = ttk.Entry(form_frame, font=("Roboto", 10))
    custom_impeller_entry.grid(row=fields.index(("Impeller Size", "combobox", None, True)), column=2, pady=3, padx=5, sticky=EW)
    custom_impeller_entry.grid_remove()  # Hide initially

    # For Connection Type "Other"
    other_entry = ttk.Entry(form_frame, font=("Roboto", 10), state="disabled")
    other_entry.grid(row=fields.index(("Connection Type", "combobox", options["connection_type"], True)), column=2, pady=3, sticky=EW)
    other_entry.grid_remove()

    tooltips = {
        "customer": "Select the customer branch for this pump",
        "branch": "Select the branch responsible for this pump",
        "pump model": "Select the pump model based on power rating",
        "configuration": "Choose the pump configuration type",
        "impeller size": "Choose the impeller size or enter a custom size if 'Other' is selected",
        "connection type": "Select the type of connection for the pump or enter a custom type if 'Other' is selected",
        "pressure required": "Enter the required pressure (e.g., 5 bar)",
        "flow rate required": "Enter the required flow rate (e.g., 10 L/min)",
        "custom motor": "Enter details if a custom motor is required",
        "flush seal housing": "Check if flush seal housing is required"
    }

    for i, (label, widget_type, opts, required) in enumerate(fields):
        label_widget = ttk.Label(form_frame, text=f"{label}{' *' if required else ''}:", font=("Roboto", 10))
        label_widget.grid(row=i, column=0, pady=3, sticky=W)
        CustomTooltip(label_widget, tooltips[label.lower()])  # Use custom tooltip

        if widget_type == "entry":
            entry = ttk.Entry(form_frame, font=("Roboto", 10))
        elif widget_type == "combobox":
            if label == "Pump Model":
                pump_model_combobox = ttk.Combobox(form_frame, values=opts, font=("Roboto", 10), state="readonly")
                pump_model_combobox.set(opts[0])
                entry = pump_model_combobox
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
                connection_opts = opts.copy()
                if "Other" not in connection_opts:
                    connection_opts.append("Other")
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

    form_frame.grid_columnconfigure(1, weight=1)
    error_label = ttk.Label(form_frame, text="", font=("Roboto", 10), bootstyle="danger")
    error_label.grid(row=len(fields), column=0, columnspan=2, pady=3)

    def submit_pump():
        data = {}
        for key, entry in entries.items():
            if isinstance(entry, (ttk.Entry, ttk.Combobox)):
                data[key] = entry.get().strip()
            elif isinstance(entry, ttk.Checkbutton):
                data[key] = "Yes" if entry.instate(['selected']) else "No"
        if data["connection_type"] == "Other":
            data["connection_type"] = other_entry.get().strip()
            if not data["connection_type"]:
                error_label.config(text="Please enter a custom connection type.")
                return
        if data["impeller_size"] == "Other":
            data["impeller_size"] = custom_impeller_entry.get().strip()
            if not data["impeller_size"]:
                error_label.config(text="Please enter a custom impeller size.")
                return

        # Validate required fields
        required_fields = [f[0].lower().replace(" ", "_") for f in fields if f[3]]
        missing = [field.replace("_", " ").title() for field in required_fields if not data[field]]
        if missing:
            error_label.config(text=f"Missing required fields: {', '.join(missing)}")
            return

        # Validate pressure_required and flow_rate_required are numeric and non-negative
        try:
            pressure_required = float(data["pressure_required"])
            flow_rate_required = float(data["flow_rate_required"])
        except ValueError:
            error_label.config(text="Pressure Required and Flow Rate Required must be numeric values.")
            return

        if pressure_required < 0 or flow_rate_required < 0:
            error_label.config(text="Pressure Required and Flow Rate Required must be non-negative values.")
            return

        try:
            with connect_db() as conn:
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
                    insert_bom=True
                )
                # Fetch the BOM for the newly created pump (use bom_items table)
                try:
                    cursor.execute("SELECT part_name, quantity FROM bom_items WHERE serial_number = ?", (serial,))
                    bom_items = cursor.fetchall()
                    logger.debug(f"Fetched BOM items for serial {serial}: {bom_items}")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Failed to fetch BOM items: {str(e)}. Proceeding with empty BOM.")
                    bom_items = []
                conn.commit()
                logger.info(f"New pump created by {username}: {serial} with BOM")
        except Exception as e:
            error_label.config(text=f"Failed to create pump: {str(e)}", bootstyle="danger")
            logger.error(f"Failed to create pump: {str(e)}")
            return

        # Prepare pump data for email and PDF
        pump_data = {
            "serial_number": serial,
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
            "requested_by": username,
        }

        # Load configuration
        config = load_config()
        certificate_dir = config["document_dirs"]["certificate"]
        confirmation_dir = config["document_dirs"]["confirmation"]
        bom_dir = config["document_dirs"]["bom"]
        if not os.path.exists(certificate_dir):
            os.makedirs(certificate_dir)
        if not os.path.exists(confirmation_dir):
            os.makedirs(confirmation_dir)
        if not os.path.exists(bom_dir):
            os.makedirs(bom_dir)

        # Generate PDF for new pump assembly notification and save to certificate directory
        pdf_path = os.path.join(certificate_dir, f"new_pump_notification_{serial}.pdf")
        try:
            generate_pdf_notification(serial, pump_data, title="New Pump Assembly Notification", output_path=pdf_path)
            os.startfile(pdf_path, "print")
            logger.info(f"PDF generated and print dialog opened for pump {serial} at {pdf_path}")
        except Exception as e:
            logger.error(f"Failed to generate PDF or open print dialog for {serial}: {str(e)}")

        # Generate BOM checklist PDF and save to bom directory
        bom_pdf_path = os.path.join(bom_dir, f"bom_checklist_{serial}.pdf")
        try:
            generate_bom_checklist(serial, bom_items, output_path=bom_pdf_path)
            os.startfile(bom_pdf_path, "print")
            logger.info(f"BOM checklist PDF generated and print dialog opened for pump {serial} at {bom_pdf_path}")
        except Exception as e:
            logger.error(f"Failed to generate BOM checklist PDF or open print dialog for {serial}: {str(e)}")

        # Generate confirmation document for pump creation
        confirmation_path = os.path.join(confirmation_dir, f"confirmation_pump_created_{serial}.pdf")
        confirmation_data = {
            "serial_number": serial,
            "status": "Created",
            "created_by": username,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        generate_pdf_notification(serial, confirmation_data, title=f"Confirmation - Pump Created {serial}", output_path=confirmation_path)
        logger.info(f"Saved confirmation to {confirmation_path}")

        # Send email to stores with all PDFs attached
        subject = f"New Pump Assembly Created: {serial}"
        greeting = "Dear Stores Team,"
        body_content = f"""
            <p>A new pump assembly has been created and requires stock to be booked out of Sage and pulled. Please open the Guth Pump Assembly Program to start the process.</p>
            <h3 style="color: #34495e;">Pump Details</h3>
            {generate_pump_details_table(pump_data)}
            <p>The Bill of Materials (BOM) checklist is attached for your reference. Please use it to pull the required items.</p>
        """
        footer = "Regards,<br>Guth Pump Registry"
        attachments = [pdf_path, confirmation_path, bom_pdf_path]
        threading.Thread(target=send_email, args=(STORES_EMAIL, subject, greeting, body_content, footer, *attachments), daemon=True).start()

        error_label.config(text="Pump created successfully!", bootstyle="success")
        refresh_all_pumps()
        refresh_stores_pumps()

    # Place Submit and Logoff buttons side by side
    ttk.Button(form_frame, text="Submit", command=submit_pump, bootstyle="success", style="large.TButton").grid(row=len(fields) + 1, column=0, pady=5, padx=5, sticky=W)
    ttk.Button(form_frame, text="Logoff", command=logout_callback, bootstyle="secondary", style="large.TButton").grid(row=len(fields) + 1, column=1, pady=5, padx=5, sticky=W)

    # Custom style for the Notebook tabs
    style = Style()
    style.configure(
        "Custom.TNotebook.Tab",
        background="#007bff",  # Blue color for unselected tabs
        foreground="white",   # White text for unselected tabs
        padding=[10, 5]       # Padding for better appearance
    )
    # Ensure the selected tab uses the default theme's appearance
    style.map(
        "Custom.TNotebook.Tab",
        background=[("selected", style.lookup("TNotebook.Tab", "background"))],  # Default selected tab background
        foreground=[("selected", style.lookup("TNotebook.Tab", "foreground"))]   # Default selected tab foreground
    )

    # Tabbed Section: All Pumps and Pumps in Stores
    notebook = ttk.Notebook(main_frame, style="Custom.TNotebook")
    notebook.pack(fill=BOTH, expand=True, pady=10)

    # Tab 1: All Pumps
    all_pumps_tab = ttk.Frame(notebook)
    notebook.add(all_pumps_tab, text="All Pumps")
    all_pumps_frame = ttk.LabelFrame(all_pumps_tab, text="All Pumps", padding=10)
    all_pumps_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Search and Filter Section for All Pumps
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

    # All Pumps Treeview
    columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration", "Impeller Size", "Connection Type", 
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
        for item in all_pumps_tree.get_children():
            all_pumps_tree.delete(item)
        search_term = search_entry_all.get().lower()
        filter_status = filter_combobox_all.get()

        with connect_db() as conn:
            cursor = conn.cursor()
            query = """
                SELECT serial_number, customer, branch, pump_model, configuration, impeller_size, connection_type, 
                       pressure_required, flow_rate_required, custom_motor, flush_seal_housing, status 
                FROM pumps
            """
            params = []
            if filter_status != "All":
                query += " WHERE status = ?"
                params.append(filter_status)
            cursor.execute(query, params)

            for pump in cursor.fetchall():
                if search_term in pump["serial_number"].lower():
                    all_pumps_tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"], pump["pump_model"], 
                                                          pump["configuration"], pump["impeller_size"], pump["connection_type"], 
                                                          pump["pressure_required"], pump["flow_rate_required"], pump["custom_motor"], 
                                                          pump["flush_seal_housing"], pump["status"]))
        logger.info("Refreshed All Pumps table")

    # Bind search and filter updates for All Pumps
    search_entry_all.bind("<KeyRelease>", lambda event: refresh_all_pumps())
    filter_combobox_all.bind("<<ComboboxSelected>>", lambda event: refresh_all_pumps())

    # Tab 2: Pumps in Stores
    stores_tab = ttk.Frame(notebook)
    notebook.add(stores_tab, text="Pumps in Stores")
    stores_frame = ttk.LabelFrame(stores_tab, text="Pumps in Stores", padding=10)
    stores_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Search and Filter Section for Pumps in Stores
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

    # Pumps in Stores Treeview
    stores_tree = ttk.Treeview(stores_frame, columns=columns, show="headings", height=12)
    for col in columns:
        stores_tree.heading(col, text=col, anchor=W)
        stores_tree.column(col, width=120, anchor=W)
    stores_tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar_stores = ttk.Scrollbar(stores_frame, orient=VERTICAL, command=stores_tree.yview)
    scrollbar_stores.pack(side=RIGHT, fill=Y)
    stores_tree.configure(yscrollcommand=scrollbar_stores.set)

    def refresh_stores_pumps():
        for item in stores_tree.get_children():
            stores_tree.delete(item)
        search_term = search_entry_stores.get().lower()
        filter_branch = filter_combobox_stores.get()

        with connect_db() as conn:
            cursor = conn.cursor()
            query = """
                SELECT serial_number, customer, branch, pump_model, configuration, impeller_size, connection_type, 
                       pressure_required, flow_rate_required, custom_motor, flush_seal_housing, status 
                FROM pumps WHERE customer = 'Stores'
            """
            params = []
            if filter_branch != "All":
                query += " AND branch = ?"
                params.append(filter_branch)
            cursor.execute(query, params)

            for pump in cursor.fetchall():
                if search_term in pump["serial_number"].lower():
                    stores_tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"], pump["pump_model"], 
                                                       pump["configuration"], pump["impeller_size"], pump["connection_type"], 
                                                       pump["pressure_required"], pump["flow_rate_required"], pump["custom_motor"], 
                                                       pump["flush_seal_housing"], pump["status"]))
        logger.info("Refreshed Pumps in Stores table")

    # Bind search and filter updates for Pumps in Stores
    search_entry_stores.bind("<KeyRelease>", lambda event: refresh_stores_pumps())
    filter_combobox_stores.bind("<<ComboboxSelected>>", lambda event: refresh_stores_pumps())

    # Initial population of both tables
    refresh_all_pumps()
    refresh_stores_pumps()

    # Bind double-click to edit for both Treeviews
    all_pumps_tree.bind("<Double-1>", lambda event: edit_pump_window(main_frame, all_pumps_tree, root, username, role, logout_callback))
    stores_tree.bind("<Double-1>", lambda event: edit_pump_window(main_frame, stores_tree, root, username, role, logout_callback))

    # Footer
    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=5, fill=X)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(expand=True)
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack(expand=True)

    return main_frame

def edit_pump_window(parent_frame, tree, root, username, role, logout_callback):
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    serial_number = tree.item(selected[0])["values"][0]
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pumps WHERE serial_number = ?", (serial_number,))
        pump = cursor.fetchone()
        if pump:
            pump_dict = dict(pump)
            logger.debug(f"Pump data fetched for edit: {pump_dict}")
        else:
            logger.warning(f"No pump found for serial_number: {serial_number}")
            return

    edit_window = ttk.Toplevel(parent_frame)
    edit_window.title(f"Edit Pump {serial_number}")
    edit_window.geometry("702x810")

    header_frame = ttk.Frame(edit_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH)
            # Increase size by 30% from 0.5 (0.5 * 1.3 = 0.65)
            img_resized = img.resize((int(img.width * 0.65), int(img.height * 0.65)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            logo_label = ttk.Label(header_frame, image=logo)
            logo_label.image = logo
            logo_label.pack(side=RIGHT, padx=10)
        except Exception as e:
            logger.error(f"Edit pump logo load failed: {str(e)}")
    ttk.Label(header_frame, text="View or edit pump details.", font=("Roboto", 12)).pack(anchor=W, padx=10)

    frame = ttk.Frame(edit_window, padding=20)
    frame.pack(fill=BOTH, expand=True)

    options = load_options()
    fields = [
        ("serial_number", "entry", None),
        ("customer", "entry", None),
        ("branch", "combobox", options["branch"]),
        ("pump_model", "combobox", options["pump_model"]),
        ("configuration", "combobox", options["configuration"]),
        ("impeller_size", "combobox", None),  # Options will be set dynamically
        ("connection_type", "combobox", options["connection_type"]),
        ("pressure_required", "entry", None),
        ("flow_rate_required", "entry", None),
        ("custom_motor", "entry", None),
        ("flush_seal_housing", "checkbutton", None)
    ]
    entries = {}
    custom_impeller_entry = ttk.Entry(frame, font=("Roboto", 12))
    custom_impeller_entry.grid(row=fields.index(("impeller_size", "combobox", None)), column=2, pady=5, padx=5, sticky=EW)
    if pump_dict.get("impeller_size") not in options["impeller_size"][pump_dict.get("pump_model", "P1 3.0KW")]:
        custom_impeller_entry.insert(0, pump_dict.get("impeller_size", ""))
    custom_impeller_entry.grid_remove()  # Hide if not "Other"

    for i, (field, widget_type, opts) in enumerate(fields):
        ttk.Label(frame, text=f"{field.replace('_', ' ').title()}:", font=("Roboto", 14)).grid(row=i, column=0, pady=5, sticky=W)
        value = pump_dict.get(field, "")
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
            elif field == "impeller_size":
                impeller_combobox = ttk.Combobox(frame, font=("Roboto", 12), state="readonly")
                initial_pump_model = pump_dict.get("pump_model", "P1 3.0KW")
                impeller_opts = options["impeller_size"].get(initial_pump_model, []) + ["Other"]
                impeller_combobox["values"] = impeller_opts
                if value in impeller_opts:
                    impeller_combobox.set(value)
                else:
                    impeller_combobox.set("Other")
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
                connection_opts = opts.copy()
                if "Other" not in connection_opts:
                    connection_opts.append("Other")
                connection_combobox = ttk.Combobox(frame, values=connection_opts, font=("Roboto", 12), state="readonly")
                connection_combobox.set(value if value in connection_opts else connection_opts[0] if connection_opts[0] != "Other" else connection_opts[1] if len(connection_opts) > 1 else "")
                entry = connection_combobox
            else:
                entry = ttk.Combobox(frame, values=opts, font=("Roboto", 12), state="readonly")
                entry.set(value if value in opts else opts[0])
        elif widget_type == "checkbutton":
            entry = ttk.Checkbutton(frame, text="", bootstyle="success-round-toggle")
            entry.state(['selected'] if value == "Yes" else ['!selected'])
        entry.grid(row=i, column=1, pady=5, sticky=EW)
        entries[field] = entry

    frame.grid_columnconfigure(1, weight=1)

    def save_changes():
        data = {}
        for key, entry in entries.items():
            if isinstance(entry, (ttk.Entry, ttk.Combobox)):
                data[key] = entry.get()
            elif isinstance(entry, ttk.Checkbutton):
                data[key] = "Yes" if entry.instate(['selected']) else "No"
        if data["impeller_size"] == "Other":
            data["impeller_size"] = custom_impeller_entry.get().strip()
            if not data["impeller_size"]:
                Messagebox.show_error("Error", "Please enter a custom impeller size.")
                return

        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pumps 
                SET pump_model = ?, configuration = ?, customer = ?, branch = ?, impeller_size = ?, 
                    connection_type = ?, pressure_required = ?, flow_rate_required = ?, custom_motor = ?, 
                    flush_seal_housing = ?
                WHERE serial_number = ?
            """, (data["pump_model"], data["configuration"], data["customer"], data["branch"], data["impeller_size"],
                  data["connection_type"], data["pressure_required"], data["flow_rate_required"], data["custom_motor"],
                  data["flush_seal_housing"], serial_number))
            conn.commit()
            logger.info(f"Updated pump {serial_number} by {username}")
        show_dashboard(root, username, role, logout_callback)
        edit_window.destroy()

    def retest_pump():
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pumps SET status = ? WHERE serial_number = ?", ("Testing", serial_number))
            conn.commit()
            logger.info(f"Pump {serial_number} set to Testing for retest by {username}")

            # Load configuration
            config = load_config()
            confirmation_dir = config["document_dirs"]["confirmation"]
            if not os.path.exists(confirmation_dir):
                os.makedirs(confirmation_dir)

            # Generate confirmation document for retest
            confirmation_path = os.path.join(confirmation_dir, f"confirmation_retest_{serial_number}.pdf")
            confirmation_data = {
                "serial_number": serial_number,
                "status": "Sent for Retest",
                "action_by": username,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            generate_pdf_notification(serial_number, confirmation_data, title=f"Confirmation - Retest {serial_number}", output_path=confirmation_path)
            logger.info(f"Saved retest confirmation to {confirmation_path}")

            # Send email to stores with confirmation PDF attached
            subject = f"Pump {serial_number} Sent for Retest"
            greeting = "Dear Stores Team,"
            body_content = f"""
                <p>Pump {serial_number} has been sent for retesting. Please ensure the necessary preparations are made.</p>
                <h3 style="color: #34495e;">Pump Details</h3>
                <table border="1" style="border-collapse: collapse;">
                    <tr><th>Serial Number</th><td>{serial_number}</td></tr>
                    <tr><th>Customer</th><td>{pump_dict['customer']}</td></tr>
                    <tr><th>Branch</th><td>{pump_dict['branch']}</td></tr>
                    <tr><th>Pump Model</th><td>{pump_dict['pump_model']}</td></tr>
                    <tr><th>Configuration</th><td>{pump_dict['configuration']}</td></tr>
                </table>
            """
            footer = "Regards,<br>Guth Pump Registry"
            threading.Thread(target=send_email, args=(STORES_EMAIL, subject, greeting, body_content, footer, confirmation_path), daemon=True).start()

        show_dashboard(root, username, role, logout_callback)
        edit_window.destroy()

    button_frame = ttk.Frame(frame)
    button_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)
    ttk.Button(button_frame, text="Save", command=save_changes, bootstyle="success", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Button(button_frame, text="Retest", command=retest_pump, bootstyle="warning", style="large.TButton").pack(side=LEFT, padx=5)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_dashboard(root, "testuser", "admin", lambda: print("Logged off"))
    root.mainloop()