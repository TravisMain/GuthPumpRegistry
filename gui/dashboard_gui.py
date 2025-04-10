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

# Constants
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    CONFIG_DIR = os.path.join(os.getenv('APPDATA'), "GuthPumpRegistry")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
    DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
else:
    BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
    DEFAULT_CONFIG_PATH = CONFIG_PATH

LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
OPTIONS_PATH = os.path.join(BASE_DIR, "assets", "pump_options.json")
PUMP_CURVES_DIR = os.path.join(BASE_DIR, "assets", "pump_curves")
PUMP_SIZING_PATH = os.path.join(BASE_DIR, "assets", "pump_sizing.json")
BUILD_NUMBER = "1.0.0"
STORES_EMAIL = "stores@guth.co.za"

def load_config():
    """Load configuration from config.json, creating it with defaults if missing."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
            logger.info(f"Loaded user config from {CONFIG_PATH}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {CONFIG_PATH}: {e}")
    elif os.path.exists(DEFAULT_CONFIG_PATH):
        try:
            with open(DEFAULT_CONFIG_PATH, "r") as f:
                config = json.load(f)
            logger.info(f"Loaded default config from {DEFAULT_CONFIG_PATH}")
            return config
        except Exception as e:
            logger.error(f"Failed to load default config from {DEFAULT_CONFIG_PATH}: {e}")
    else:
        config = {
            "document_dirs": {
                "certificate": os.path.join(BASE_DIR, "certificates"),
                "bom": os.path.join(BASE_DIR, "boms"),
                "confirmation": os.path.join(BASE_DIR, "confirmations"),
                "reports": os.path.join(BASE_DIR, "reports"),
                "excel_exports": os.path.join(BASE_DIR, "exports")
            }
        }
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=4)
            logger.info(f"Created default config file at {CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Failed to create default config at {CONFIG_PATH}: {e}")
        logger.warning(f"No config found at {CONFIG_PATH} or {DEFAULT_CONFIG_PATH}, using defaults")
        return config

def load_options(file_path=OPTIONS_PATH, key=""):
    """Load options from a JSON file."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            logger.info(f"Loaded options from {file_path}")
            return data.get(key, data) if key else data
    except Exception as e:
        logger.error(f"Failed to load options from {file_path}: {e}")
        return {}

def load_pump_sizing(file_path=PUMP_SIZING_PATH):
    """Load pump sizing data from pump_sizing.json."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            logger.info(f"Loaded pump sizing data from {file_path}")
            return data
    except Exception as e:
        logger.error(f"Failed to load pump sizing data from {file_path}: {e}")
        return []

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
        logger.error(f"Failed to generate BOM checklist PDF: {e}")
        raise

class PumpOriginatorDashboard:
    """Class to manage the Pump Originator dashboard."""
    def __init__(self, root, username, role, logout_callback):
        self.root = root
        self.username = username
        self.role = role
        self.logout_callback = logout_callback
        self.options = load_options()
        self.pump_sizing = load_pump_sizing()
        self.main_frame = None
        self.show_dashboard()

    def refresh_all_pumps(self):
        """Refresh the All Pumps table with search and filter."""
        self.all_pumps_tree.delete(*self.all_pumps_tree.get_children())
        search_type = self.search_type_all.get()
        search_term = self.search_entry_all.get().lower()
        filter_status = self.filter_combobox_all.get()

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT serial_number, customer, branch, pump_model, configuration, impeller_size, connection_type,
                           pressure_required, flow_rate_required, custom_motor, flush_seal_housing, status
                    FROM pumps
                """
                conditions = []
                params = []
                if filter_status != "All":
                    conditions.append("status = ?")
                    params.append(filter_status)
                if search_term and search_type:
                    if search_type == "Serial Number":
                        conditions.append("LOWER(serial_number) LIKE ?")
                    elif search_type == "Customer":
                        conditions.append("LOWER(customer) LIKE ?")
                    elif search_type == "Branch":
                        conditions.append("LOWER(branch) LIKE ?")
                    elif search_type == "Pump Model":
                        conditions.append("LOWER(pump_model) LIKE ?")
                    params.append(f"%{search_term}%")

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                cursor.execute(query, params)
                for pump in cursor.fetchall():
                    self.all_pumps_tree.insert("", END, values=(pump[0], pump[1], pump[2], pump[3], pump[4], pump[5], pump[6], pump[7], pump[8], pump[9], pump[10], pump[11]))
            logger.info("Refreshed All Pumps table")
        except Exception as e:
            logger.error(f"Failed to refresh all pumps: {e}")
            Messagebox.show_error("Error", f"Failed to load pumps: {e}")

    def refresh_stock_pumps(self):
        """Refresh the Pumps in Stock table with search and filter."""
        self.stock_tree.delete(*self.stock_tree.get_children())
        search_type = self.search_type_stock.get()
        search_term = self.search_entry_stock.get().lower()
        filter_branch = self.filter_combobox_stock.get()

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT serial_number, customer, branch, pump_model, configuration, impeller_size, connection_type,
                           pressure_required, flow_rate_required, custom_motor, flush_seal_housing, status
                    FROM pumps WHERE status = 'Stores'
                """
                conditions = []
                params = []
                if filter_branch != "All":
                    conditions.append("branch = ?")
                    params.append(filter_branch)
                if search_term and search_type:
                    if search_type == "Serial Number":
                        conditions.append("LOWER(serial_number) LIKE ?")
                    elif search_type == "Customer":
                        conditions.append("LOWER(customer) LIKE ?")
                    elif search_type == "Branch":
                        conditions.append("LOWER(branch) LIKE ?")
                    elif search_type == "Pump Model":
                        conditions.append("LOWER(pump_model) LIKE ?")
                    params.append(f"%{search_term}%")

                if conditions:
                    query += " AND " + " AND ".join(conditions)

                cursor.execute(query, params)
                for pump in cursor.fetchall():
                    self.stock_tree.insert("", END, values=(pump[0], pump[1], pump[2], pump[3], pump[4], pump[5], pump[6], pump[7], pump[8], pump[9], pump[10], pump[11]))
            logger.info("Refreshed Pumps in Stock table")
        except Exception as e:
            logger.error(f"Failed to refresh stock pumps: {e}")
            Messagebox.show_error("Error", f"Failed to load pumps: {e}")

    def find_suitable_pumps(self, flow_rate, pressure):
        """Find pumps that match the specified flow rate (L/hr) and pressure (bar), returning the top 3 best matches."""
        try:
            flow_rate = float(flow_rate)  # Flow Rate Required in L/hr
            pressure = float(pressure)  # Pressure Required in bar
            logger.debug(f"Finding suitable pumps for flow rate: {flow_rate} L/hr, pressure: {pressure} bar")
        except ValueError:
            logger.debug("Invalid flow rate or pressure for pump suggestion")
            return []

        suitable_pumps = []
        for pump in self.pump_sizing:
            pump_id = pump["id"]
            for impeller in pump["impellers"]:
                dia = impeller["diameter_mm"]
                capacity_range = impeller["capacity_range_Lhr"]
                pressure_range = impeller["pressure_range_bar"]
                if (capacity_range[0] <= flow_rate <= capacity_range[1] and
                    pressure_range[0] <= pressure <= pressure_range[1]):
                    # Calculate suitability score based on proximity to the midpoint of ranges
                    capacity_mid = (capacity_range[1] + capacity_range[0]) / 2
                    pressure_mid = (pressure_range[1] + pressure_range[0]) / 2
                    # Normalize the differences (using range spans to scale)
                    capacity_span = capacity_range[1] - capacity_range[0] if capacity_range[1] != capacity_range[0] else 1
                    pressure_span = pressure_range[1] - pressure_range[0] if pressure_range[1] != pressure_range[0] else 1
                    capacity_diff = abs(flow_rate - capacity_mid) / capacity_span
                    pressure_diff = abs(pressure - pressure_mid) / pressure_span
                    # Total score (lower is better, meaning closer to midpoint)
                    score = capacity_diff + pressure_diff
                    suitable_pumps.append({
                        "pump_id": pump_id,
                        "impeller_diameter": dia,
                        "capacity_range_Lhr": capacity_range,
                        "pressure_range_bar": pressure_range,
                        "suitability_score": score
                    })

        # Sort by suitability score (ascending) and take top 3
        suitable_pumps.sort(key=lambda x: x["suitability_score"])
        top_pumps = suitable_pumps[:3]
        logger.info(f"Top 3 suitable pumps found: {[pump['pump_id'] for pump in top_pumps]}")
        return top_pumps

    def update_impeller(self, event=None):
        """Update impeller size options based on pump model."""
        model = self.fab_entries["pump_model"].get()
        if model:
            for pump in self.pump_sizing:
                if pump["id"] == model:
                    impeller_sizes = [str(impeller["diameter_mm"]) for impeller in pump["impellers"]]
                    self.fab_entries["impeller_size"]["values"] = impeller_sizes
                    self.fab_entries["impeller_size"].set(impeller_sizes[0] if impeller_sizes else "")
                    logger.debug(f"Updated impeller sizes for {model}: {impeller_sizes}")
                    break
            else:
                self.fab_entries["impeller_size"]["values"] = []
                self.fab_entries["impeller_size"].set("")
                logger.warning(f"No impeller sizes found for {model}")

    def update_recommended_pumps(self, event=None):
        """Update the recommended pumps panel based on flow rate and pressure, showing only the top 3 best matches."""
        flow_rate = self.details_entries["flow_rate_required"].get()
        pressure = self.details_entries["pressure_required"].get()
        suitable_pumps = self.find_suitable_pumps(flow_rate, pressure)

        # Clear the current content in the right frame
        for widget in self.right_frame.winfo_children():
            widget.destroy()

        if not suitable_pumps:
            ttk.Label(self.right_frame, text="No suitable pumps found for the specified duty.", font=("Roboto", 12)).pack(pady=20)
            return

        # Create a notebook for tabs with custom styling
        style = Style()
        style.configure("Pump.TNotebook", tabposition="n", background="#f0f0f0")
        style.configure("Pump.TNotebook.Tab", font=("Roboto", 12), padding=[10, 5], background="#d3d3d3", foreground="black")
        style.map("Pump.TNotebook.Tab",
                  background=[("selected", "#007bff"), ("!selected", "#d3d3d3")],
                  foreground=[("selected", "white"), ("!selected", "black")],
                  relief=[("selected", "raised"), ("!selected", "flat")])

        pump_notebook = ttk.Notebook(self.right_frame, style="Pump.TNotebook")
        pump_notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        for pump in suitable_pumps:
            pump_id = pump["pump_id"]
            impeller_dia = pump["impeller_diameter"]
            capacity_range = pump["capacity_range_Lhr"]
            pressure_range = pump["pressure_range_bar"]

            # Create a tab for each pump
            tab = ttk.Frame(pump_notebook)
            pump_notebook.add(tab, text=pump_id)

            # Scrollable frame for the tab
            tab_container = ttk.Frame(tab)
            tab_container.pack(fill=BOTH, expand=True)
            canvas_tab = ttk.Canvas(tab_container)
            canvas_tab.pack(side=LEFT, fill=BOTH, expand=True)
            scrollbar_tab = ttk.Scrollbar(tab_container, orient=VERTICAL, command=canvas_tab.yview)
            scrollbar_tab.pack(side=RIGHT, fill=Y)
            tab_frame = ttk.Frame(canvas_tab)
            canvas_tab.configure(yscrollcommand=scrollbar_tab.set)
            canvas_tab.create_window((0, 0), window=tab_frame, anchor="nw")
            tab_frame.bind("<Configure>", lambda e, c=canvas_tab: c.configure(scrollregion=c.bbox("all")))

            # Mouse wheel binding for the tab
            def _on_mousewheel_tab(event, canvas=canvas_tab):
                logger.debug(f"Mouse wheel event on tab for {pump_id}")
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            canvas_tab.bind("<MouseWheel>", _on_mousewheel_tab)

            # Top frame for Pump ID and Select button
            top_frame = ttk.Frame(tab_frame)
            top_frame.pack(fill=X, pady=5)
            ttk.Label(top_frame, text=f"Pump ID: {pump_id}", font=("Roboto", 12, "bold")).pack(side=LEFT, padx=5)

            # Select button (styled like Logoff and Submit)
            def select_pump(pump_id=pump_id, impeller_dia=impeller_dia):
                self.fab_entries["pump_model"].set(pump_id)
                self.update_impeller()  # Update impeller sizes based on selected pump
                self.fab_entries["impeller_size"].set(str(impeller_dia))
                self.error_label.config(text=f"Selected {pump_id} with impeller diameter {impeller_dia} mm", bootstyle="success")

            ttk.Button(top_frame, text="Select", command=select_pump, bootstyle="success", style="large.TButton").pack(side=RIGHT, padx=5)

            # Display pump details
            ttk.Label(tab_frame, text=f"Recommended Impeller Diameter: {impeller_dia} mm", font=("Roboto", 10)).pack(anchor=W, padx=5)
            ttk.Label(tab_frame, text=f"Capacity Range: {capacity_range[0]} - {capacity_range[1]} L/hr", font=("Roboto", 10)).pack(anchor=W, padx=5)
            ttk.Label(tab_frame, text=f"Pressure Range: {pressure_range[0]} - {pressure_range[1]} bar", font=("Roboto", 10)).pack(anchor=W, padx=5)

            # Display pump curve (shrunk by 15%)
            curve_path = os.path.join(PUMP_CURVES_DIR, f"{pump_id}.png")
            if os.path.exists(curve_path):
                try:
                    img = Image.open(curve_path)
                    new_width = int(798 * 0.85)  # 85% of original width
                    new_height = int(1140 * 0.85)  # 85% of original height
                    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    curve_image = ImageTk.PhotoImage(img_resized)
                    curve_label = ttk.Label(tab_frame, image=curve_image)
                    curve_label.pack(pady=10)
                    curve_label.image = curve_image  # Keep reference
                    curve_label.bind("<MouseWheel>", lambda e, c=canvas_tab: _on_mousewheel_tab(e, c))
                    logger.info(f"Displayed pump curve for {pump_id} from {curve_path} at {new_width}x{new_height}")
                except Exception as e:
                    logger.error(f"Failed to load pump curve image {curve_path}: {e}")
                    ttk.Label(tab_frame, text=f"Error loading pump curve: {e}", font=("Roboto", 10)).pack(pady=10)
            else:
                logger.warning(f"Pump curve not found: {curve_path}")
                ttk.Label(tab_frame, text=f"No pump curve available for {pump_id}", font=("Roboto", 10)).pack(pady=10)

    def show_dashboard(self):
        """Display the Pump Originator dashboard."""
        self.root.state('zoomed')
        for widget in self.root.winfo_children():
            widget.destroy()

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Header (shrunk)
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=X, pady=(0, 10), ipady=10)
        if os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 1.0), int(Image.open(LOGO_PATH).height * 1.0)), Image.Resampling.LANCZOS)
                logo = ImageTk.PhotoImage(img)
                ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
                header_frame.image = logo  # Keep reference
            except Exception as e:
                logger.error(f"Dashboard logo load failed: {e}")
        ttk.Label(header_frame, text=f"Welcome, {self.username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
        ttk.Label(header_frame, text="Pump Originator Dashboard", font=("Roboto", 12)).pack(anchor=W, padx=10)
        # Add instruction under the heading
        ttk.Label(header_frame, text="This dashboard helps you create and manage pump assemblies. Enter details to view recommended pumps and submit new assemblies.",
                  font=("Roboto", 10), wraplength=600).pack(anchor=W, padx=10)

        # Notebook (Tabs)
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill=BOTH, expand=True, pady=5)

        # Tab 1: Create New Pump Assembly
        create_tab = ttk.Frame(notebook)
        notebook.add(create_tab, text="Create New Pump Assembly")

        # Use a Frame with grid to control panel widths
        create_frame = ttk.Frame(create_tab)
        create_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        create_frame.grid_rowconfigure(0, weight=1)
        create_frame.grid_columnconfigure(0, weight=1)  # Left panel
        create_frame.grid_columnconfigure(1, weight=1)  # Right panel

        # Left frame with scrollbar for fields (shrunk to ~50%)
        left_container = ttk.Frame(create_frame)
        left_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        canvas_left = ttk.Canvas(left_container, width=400)
        canvas_left.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar_left = ttk.Scrollbar(left_container, orient=VERTICAL, command=canvas_left.yview)
        scrollbar_left.pack(side=RIGHT, fill=Y)
        self.fields_frame = ttk.Frame(canvas_left)
        canvas_left.configure(yscrollcommand=scrollbar_left.set)
        canvas_left.create_window((0, 0), window=self.fields_frame, anchor="nw")
        self.fields_frame.bind("<Configure>", lambda e: canvas_left.configure(scrollregion=canvas_left.bbox("all")))

        # Mouse wheel binding for left frame (fields)
        def _on_mousewheel_left(event):
            logger.debug("Mouse wheel event on left canvas (fields)")
            canvas_left.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas_left.bind("<MouseWheel>", _on_mousewheel_left)

        # Right frame for recommended pumps (expanded to ~50%)
        right_container = ttk.Frame(create_frame)
        right_container.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.right_frame = ttk.Frame(right_container)
        self.right_frame.pack(fill=BOTH, expand=True)

        # Top frame for Customer Details and Product Details (side by side)
        top_frame = ttk.Frame(self.fields_frame)
        top_frame.pack(fill=X, pady=5)
        top_frame.grid_rowconfigure(0, weight=1)
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_columnconfigure(1, weight=1)

        # Customer Details (left)
        customer_frame = ttk.LabelFrame(top_frame, text="Customer Details", padding=10)
        customer_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        customer_fields = [
            ("Invoice Number", "entry", None, False, "Enter the invoice number (optional)"),
            ("Customer", "entry", None, True, "Enter the customer name"),
            ("Job Number", "entry", None, True, "Enter the job number"),
            ("Sage Reference Number", "entry", None, True, "Enter the Sage reference number"),
            ("Branch", "combobox", self.options.get("branch", []), True, "Select the branch"),
            ("Send to Stock", "checkbutton", None, False, "Check to send this pump directly to stock"),
        ]
        self.customer_entries = {}
        for i, (label, wtype, opts, req, tooltip) in enumerate(customer_fields):
            ttk.Label(customer_frame, text=f"{label}{' *' if req else ''}:", font=("Roboto", 10)).grid(row=i, column=0, pady=3, sticky=W)
            if wtype == "entry":
                entry = ttk.Entry(customer_frame, font=("Roboto", 10), width=20)
            elif wtype == "combobox":
                entry = ttk.Combobox(customer_frame, values=opts, font=("Roboto", 10), state="readonly", width=20)
                entry.set(opts[0] if opts else "")
            elif wtype == "checkbutton":
                entry = ttk.Checkbutton(customer_frame, text="", bootstyle="success-round-toggle")
            entry.grid(row=i, column=1, pady=3, sticky=EW)
            self.customer_entries[label.lower().replace(" ", "_")] = entry
            CustomTooltip(entry, tooltip)

        # Product Details (right)
        details_frame = ttk.LabelFrame(top_frame, text="Product Details", padding=10)
        details_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        details_fields = [
            ("Pressure Required", "entry", None, True, "Enter the required pressure (e.g., 5 bar)"),
            ("Flow Rate Required", "entry", None, True, "Enter the required flow rate (e.g., 10 L/min)"),
            ("Temperature", "entry", None, True, "Enter the operating temperature (e.g., 50°C)"),
            ("Product", "entry", None, True, "Enter the product (e.g., Water)"),
        ]
        self.details_entries = {}
        for i, (label, wtype, _, req, tooltip) in enumerate(details_fields):
            # Use bold font for "Pressure Required" and "Flow Rate Required"
            if label in ["Pressure Required", "Flow Rate Required"]:
                ttk.Label(details_frame, text=f"{label} *:", font=("Roboto", 10, "bold")).grid(row=i, column=0, pady=3, sticky=W)
            else:
                ttk.Label(details_frame, text=f"{label} *:", font=("Roboto", 10)).grid(row=i, column=0, pady=3, sticky=W)
            entry = ttk.Entry(details_frame, font=("Roboto", 10), width=20)
            entry.grid(row=i, column=1, pady=3, sticky=EW)
            self.details_entries[label.lower().replace(" ", "_")] = entry
            CustomTooltip(entry, tooltip)

        # Fabrication (below, two columns)
        fab_frame = ttk.LabelFrame(self.fields_frame, text="Fabrication", padding=10)
        fab_frame.pack(fill=BOTH, expand=True, pady=5)
        fab_fields_left = [
            ("Pump Model", "combobox", [pump["id"] for pump in self.pump_sizing], True, "Select the pump model (populated after selection)"),
            ("Configuration", "combobox", self.options.get("configuration", []), True, "Select the configuration"),
            ("Impeller Size", "combobox", [], True, "Select impeller size (populated after selection)"),
        ]
        fab_fields_right = [
            ("O ring Material", "combobox", ["EPDM", "Viton", "Nitril"], True, "Select O-ring material"),
            ("Mechanical Seals", "combobox", self.options.get("mechanical_seals", ["C/SS", "TC/TC", "SC/SC", "Ceramic", "Other"]), True, "Select mechanical seal type or 'Other'"),
            ("Flush Seal Housing", "checkbutton", None, False, "Check if flush seal housing is required"),
            ("Custom Motor", "entry", None, False, "Enter custom motor details (optional)"),
        ]
        self.fab_entries = {}
        self.custom_seal_entry = ttk.Entry(fab_frame, font=("Roboto", 10), width=20)
        self.custom_seal_entry.grid(row=1, column=3, pady=3, padx=5, sticky=EW)
        self.custom_seal_entry.grid_remove()

        # Left column
        for i, (label, wtype, opts, req, tooltip) in enumerate(fab_fields_left):
            ttk.Label(fab_frame, text=f"{label}{' *' if req else ''}:", font=("Roboto", 10)).grid(row=i, column=0, pady=3, sticky=W)
            if wtype == "entry":
                entry = ttk.Entry(fab_frame, font=("Roboto", 10), width=20)
            elif wtype == "combobox":
                entry = ttk.Combobox(fab_frame, values=opts, font=("Roboto", 10), width=20)
                if label == "Pump Model":
                    self.fab_entries["pump_model"] = entry
                    entry.set("")  # Default to blank
                elif label == "Configuration":
                    entry.set(self.options["configuration"][0] if "configuration" in self.options else "")
                elif label == "Impeller Size":
                    self.fab_entries["impeller_size"] = entry
                    entry.set("")  # Default to blank
                else:
                    entry.set(opts[0] if opts else "")
            elif wtype == "checkbutton":
                entry = ttk.Checkbutton(fab_frame, text="", bootstyle="success-round-toggle")
            entry.grid(row=i, column=1, pady=3, sticky=EW)
            self.fab_entries[label.lower().replace(" ", "_")] = entry
            CustomTooltip(entry, tooltip)

        # Right column with padding
        for i, (label, wtype, opts, req, tooltip) in enumerate(fab_fields_right):
            ttk.Label(fab_frame, text=f"{label}{' *' if req else ''}:", font=("Roboto", 10)).grid(row=i, column=2, pady=3, padx=(5, 0), sticky=W)
            if wtype == "entry":
                entry = ttk.Entry(fab_frame, font=("Roboto", 10), width=20)
            elif wtype == "combobox":
                entry = ttk.Combobox(fab_frame, values=opts, font=("Roboto", 10), state="readonly", width=20)
                entry.set(opts[0] if opts else "")
            elif wtype == "checkbutton":
                entry = ttk.Checkbutton(fab_frame, text="", bootstyle="success-round-toggle")
            entry.grid(row=i, column=3, pady=3, sticky=EW)
            self.fab_entries[label.lower().replace(" ", "_")] = entry
            CustomTooltip(entry, tooltip)

        # Error Label
        self.error_label = ttk.Label(self.fields_frame, text="", font=("Roboto", 10), bootstyle="danger")
        self.error_label.pack(pady=5)

        # Submit Button
        ttk.Button(self.fields_frame, text="Submit", command=self.submit_pump, bootstyle="success", style="large.TButton").pack(pady=10)

        # Bind events
        self.fab_entries["pump_model"].bind("<<ComboboxSelected>>", self.update_impeller)
        self.fab_entries["mechanical_seals"].bind("<<ComboboxSelected>>", self.update_seal)

        # Bind pressure and flow rate entries to update recommended pumps
        self.details_entries["pressure_required"].bind("<KeyRelease>", self.update_recommended_pumps)
        self.details_entries["flow_rate_required"].bind("<KeyRelease>", self.update_recommended_pumps)

        customer_entry = self.customer_entries["customer"]
        send_to_stock_check = self.customer_entries["send_to_stock"]
        send_to_stock_check.configure(command=lambda: (customer_entry.configure(state="disabled"), customer_entry.delete(0, END), customer_entry.insert(0, "Stock")) if send_to_stock_check.instate(['selected']) else (customer_entry.configure(state="normal"), customer_entry.delete(0, END)))

        # Tab 2: All Pumps
        pumps_tab = ttk.Frame(notebook)
        notebook.add(pumps_tab, text="All Pumps")
        sub_notebook = ttk.Notebook(pumps_tab)
        sub_notebook.pack(fill=BOTH, expand=True, pady=10)

        # Sub-Tab 1: All Pumps
        all_pumps_tab = ttk.Frame(sub_notebook)
        sub_notebook.add(all_pumps_tab, text="All Pumps")
        all_pumps_frame = ttk.LabelFrame(all_pumps_tab, text="All Pumps", padding=10)
        all_pumps_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Search and filter frame for All Pumps
        search_filter_frame_all = ttk.Frame(all_pumps_frame)
        search_filter_frame_all.pack(fill=X, pady=(0, 5))
        ttk.Label(search_filter_frame_all, text="Search by:", font=("Roboto", 10)).pack(side=LEFT, padx=5)
        self.search_type_all = ttk.Combobox(search_filter_frame_all, values=["Serial Number", "Customer", "Branch", "Pump Model"], font=("Roboto", 10), state="readonly", width=15)
        self.search_type_all.set("Serial Number")
        self.search_type_all.pack(side=LEFT, padx=5)
        CustomTooltip(self.search_type_all, "Select the field to search by")

        self.search_entry_all = ttk.Entry(search_filter_frame_all, font=("Roboto", 10), width=20)
        self.search_entry_all.pack(side=LEFT, padx=5)
        CustomTooltip(self.search_entry_all, "Enter a value to search (partial matches allowed)")

        ttk.Label(search_filter_frame_all, text="Filter by Status:", font=("Roboto", 10)).pack(side=LEFT, padx=5)
        self.filter_combobox_all = ttk.Combobox(search_filter_frame_all, values=["All", "Stores", "Assembler", "Testing", "Pending Approval", "Completed"], font=("Roboto", 10), state="readonly")
        self.filter_combobox_all.set("All")
        self.filter_combobox_all.pack(side=LEFT, padx=5)
        CustomTooltip(self.filter_combobox_all, "Filter pumps by their current status")

        columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration", "Impeller Size", "Connection Type",
                   "Pressure Required", "Flow Rate Required", "Custom Motor", "Flush Seal Housing", "Status")
        self.all_pumps_tree = ttk.Treeview(all_pumps_frame, columns=columns, show="headings", height=12)
        for col in columns:
            self.all_pumps_tree.heading(col, text=col, anchor=W)
            self.all_pumps_tree.column(col, width=120, anchor=W)
        self.all_pumps_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar_all = ttk.Scrollbar(all_pumps_frame, orient=VERTICAL, command=self.all_pumps_tree.yview)
        scrollbar_all.pack(side=RIGHT, fill=Y)
        self.all_pumps_tree.configure(yscrollcommand=scrollbar_all.set)

        self.search_type_all.bind("<<ComboboxSelected>>", lambda event: self.refresh_all_pumps())
        self.search_entry_all.bind("<KeyRelease>", lambda event: self.refresh_all_pumps())
        self.filter_combobox_all.bind("<<ComboboxSelected>>", lambda event: self.refresh_all_pumps())
        self.all_pumps_tree.bind("<Double-1>", lambda event: self.edit_pump_window(self.all_pumps_tree))
        self.refresh_all_pumps()

        # Sub-Tab 2: Pumps in Stock
        stock_tab = ttk.Frame(sub_notebook)
        sub_notebook.add(stock_tab, text="Pumps in Stock")
        stock_frame = ttk.LabelFrame(stock_tab, text="Pumps in Stock", padding=10)
        stock_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Search and filter frame for Pumps in Stock
        search_filter_frame_stock = ttk.Frame(stock_frame)
        search_filter_frame_stock.pack(fill=X, pady=(0, 5))
        ttk.Label(search_filter_frame_stock, text="Search by:", font=("Roboto", 10)).pack(side=LEFT, padx=5)
        self.search_type_stock = ttk.Combobox(search_filter_frame_stock, values=["Serial Number", "Customer", "Branch", "Pump Model"], font=("Roboto", 10), state="readonly", width=15)
        self.search_type_stock.set("Serial Number")
        self.search_type_stock.pack(side=LEFT, padx=5)
        CustomTooltip(self.search_type_stock, "Select the field to search by")

        self.search_entry_stock = ttk.Entry(search_filter_frame_stock, font=("Roboto", 10), width=20)
        self.search_entry_stock.pack(side=LEFT, padx=5)
        CustomTooltip(self.search_entry_stock, "Enter a value to search (partial matches allowed)")

        ttk.Label(search_filter_frame_stock, text="Filter by Branch:", font=("Roboto", 10)).pack(side=LEFT, padx=5)
        self.filter_combobox_stock = ttk.Combobox(search_filter_frame_stock, values=["All"] + self.options.get("branch", []), font=("Roboto", 10), state="readonly")
        self.filter_combobox_stock.set("All")
        self.filter_combobox_stock.pack(side=LEFT, padx=5)
        CustomTooltip(self.filter_combobox_stock, "Filter pumps by branch")

        self.stock_tree = ttk.Treeview(stock_frame, columns=columns, show="headings", height=12)
        for col in columns:
            self.stock_tree.heading(col, text=col, anchor=W)
            self.stock_tree.column(col, width=120, anchor=W)
        self.stock_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar_stock = ttk.Scrollbar(stock_frame, orient=VERTICAL, command=self.stock_tree.yview)
        scrollbar_stock.pack(side=RIGHT, fill=Y)
        self.stock_tree.configure(yscrollcommand=scrollbar_stock.set)

        self.search_type_stock.bind("<<ComboboxSelected>>", lambda event: self.refresh_stock_pumps())
        self.search_entry_stock.bind("<KeyRelease>", lambda event: self.refresh_stock_pumps())
        self.filter_combobox_stock.bind("<<ComboboxSelected>>", lambda event: self.refresh_stock_pumps())
        self.stock_tree.bind("<Double-1>", lambda event: self.edit_pump_window(self.stock_tree))
        self.refresh_stock_pumps()

        # Footer Frame (below notebook, always visible)
        footer_frame = ttk.Frame(self.main_frame)
        footer_frame.pack(side=BOTTOM, fill=X, pady=5)
        ttk.Button(footer_frame, text="Logoff", command=lambda: self.logout_callback(), bootstyle="warning", style="large.TButton").pack(pady=5)
        ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
        ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

        style = Style()
        style.configure("Custom.TNotebook", tabposition="n", background="#f0f0f0")
        style.configure("Custom.TNotebook.Tab", font=("Roboto", 12), padding=[10, 5], background="#d3d3d3", foreground="black")
        style.map("Custom.TNotebook.Tab",
                  background=[("selected", "#007bff"), ("!selected", "#d3d3d3")],
                  foreground=[("selected", "white"), ("!selected", "black")],
                  relief=[("selected", "raised"), ("!selected", "flat")])

    def update_seal(self, event):
        """Show/hide custom seal entry."""
        if self.fab_entries["mechanical_seals"].get() == "Other":
            self.custom_seal_entry.grid()
        else:
            self.custom_seal_entry.grid_remove()

    def submit_pump(self):
        """Submit a new pump assembly."""
        data = {**{k: e.get() if isinstance(e, (ttk.Entry, ttk.Combobox)) else "Yes" if e.instate(['selected']) else "No" for k, e in self.customer_entries.items()},
                **{k: e.get() if isinstance(e, (ttk.Entry, ttk.Combobox)) else "Yes" if e.instate(['selected']) else "No" for k, e in self.fab_entries.items()},
                **{k: e.get() for k, e in self.details_entries.items()}}
        data["mechanical_seals"] = self.custom_seal_entry.get() if data["mechanical_seals"] == "Other" else data["mechanical_seals"]

        assembly_key = f"{data['pump_model']}_{data['configuration']}"
        data["assembly_part_number"] = self.options.get("assembly_part_mapping", {}).get(assembly_key, f"APN-{data['pump_model'].replace(' ', '')}")

        if data["send_to_stock"] == "Yes":
            data["customer"] = "Stock"
            data["status"] = "Stores"
        else:
            data["status"] = "Stores"

        required = ["customer", "job_number", "sage_reference_number", "branch", "pump_model", "configuration", "impeller_size", "o_ring_material", "mechanical_seals", "temperature", "product", "pressure_required", "flow_rate_required"]
        missing = [f.replace("_", " ").title() for f in required if not data[f].strip()]
        if missing:
            self.error_label.config(text=f"Missing: {', '.join(missing)}")
            return

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                serial = create_pump(cursor, data["pump_model"], data["configuration"], data["customer"], self.username, data["branch"],
                                     data["impeller_size"], "", 0.0, 0.0, data["custom_motor"], data["flush_seal_housing"],
                                     data["assembly_part_number"], insert_bom=True)
                cursor.execute("""
                    UPDATE pumps 
                    SET invoice_number=?, job_number_1=?, sage_reference_number=?, o_ring_material=?, 
                        mechanical_seals=?, temperature=?, medium=?, pressure_required=?, flow_rate_required=?, status=?
                    WHERE serial_number=?
                """, (data["invoice_number"], data["job_number"], data["sage_reference_number"], data["o_ring_material"],
                      data["mechanical_seals"], data["temperature"], data["product"], data["pressure_required"], data["flow_rate_required"], data["status"], serial))
                conn.commit()

            pump_data = {k: data[k] for k in ["serial_number", "assembly_part_number", "customer", "branch", "pump_model", "configuration",
                                              "impeller_size", "custom_motor", "flush_seal_housing", "o_ring_material",
                                              "mechanical_seals", "temperature", "product", "pressure_required", "flow_rate_required"] if k in data}
            pump_data["serial_number"] = serial
            pump_data["requested_by"] = self.username

            config = load_config()
            notifications_dir = os.path.join(BASE_DIR, "docs", "Notifications")
            os.makedirs(notifications_dir, exist_ok=True)
            for dir_key in ["confirmation", "bom"]:
                dir_path = config["document_dirs"][dir_key]
                os.makedirs(dir_path, exist_ok=True)

            pdf_path = os.path.join(notifications_dir, f"new_pump_notification_{serial}.pdf")
            bom_pdf_path = os.path.join(config["document_dirs"]["bom"], f"bom_checklist_{serial}.pdf")
            confirmation_path = os.path.join(config["document_dirs"]["confirmation"], f"confirmation_pump_created_{serial}.pdf")

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT part_code, part_name, quantity FROM bom_items WHERE serial_number = ?", (serial,))
                bom_items = [{"part_code": row[0], "part_name": row[1], "quantity": row[2]} for row in cursor.fetchall()]

            generate_pdf_notification(serial, pump_data, title="New Pump Assembly Notification", output_path=pdf_path)
            os.startfile(pdf_path, "print")
            generate_bom_checklist(serial, bom_items, output_path=bom_pdf_path)
            os.startfile(bom_pdf_path, "print")
            confirmation_data = {"serial_number": serial, "assembly_part_number": data["assembly_part_number"], "status": data["status"], "created_by": self.username, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            generate_pdf_notification(serial, confirmation_data, title=f"Confirmation - Pump Created {serial}", output_path=confirmation_path)

            subject = f"New Pump Assembly Created: {serial}"
            body_content = f"""
                <p>A new pump assembly has been created and requires stock to be booked out of Sage and pulled.</p>
                <h3 style="color: #34495e;">Pump Details</h3>
                {generate_pump_details_table(pump_data)}
                <p>The BOM checklist is attached.</p>
            """
            threading.Thread(target=send_email, args=(STORES_EMAIL, subject, "Dear Stores Team,", body_content, "Regards,<br>Guth Pump Registry", pdf_path, confirmation_path, bom_pdf_path), daemon=True).start()

            self.error_label.config(text=f"Pump created: {serial}", bootstyle="success")
            self.refresh_all_pumps()
            self.refresh_stock_pumps()
        except Exception as e:
            logger.error(f"Failed to create pump: {e}", exc_info=True)
            self.error_label.config(text=f"Error: {e}", bootstyle="danger")

    def edit_pump_window(self, tree):
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
            logger.error(f"Failed to load pump data: {e}")
            Messagebox.show_error("Error", f"Failed to load pump: {e}")
            return

        edit_window = ttk.Toplevel(self.root)
        edit_window.title(f"Edit Pump {serial_number}")
        edit_window.geometry("702x810")

        header_frame = ttk.Frame(edit_window)
        header_frame.pack(fill=X, pady=(0, 10), ipady=10)
        if os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.65), int(Image.open(LOGO_PATH).height * 0.65)), Image.Resampling.LANCZOS)
                logo = ImageTk.PhotoImage(img)
                ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
                header_frame.image = logo
            except Exception as e:
                logger.error(f"Edit pump logo load failed: {e}")
        ttk.Label(header_frame, text="View or edit pump details.", font=("Roboto", 12)).pack(anchor=W, padx=10)

        frame = ttk.Frame(edit_window, padding=20)
        frame.pack(fill=BOTH, expand=True)

        fields = [
            ("serial_number", "entry", None),
            ("customer", "entry", None),
            ("branch", "combobox", self.options.get("branch", [])),
            ("assembly_part_number", "entry", None),
            ("pump_model", "entry", None),
            ("configuration", "combobox", self.options.get("configuration", [])),
            ("impeller_size", "entry", None),
            ("connection_type", "combobox", self.options.get("connection_type", []) + ["SMS", "DR", "BSP"]),
            ("o_ring_material", "combobox", ["EPDM", "Viton", "Nitril"]),
            ("mechanical_seals", "combobox", self.options.get("mechanical_seals", ["C/SS", "TC/TC", "SC/SC", "Ceramic", "Other"])),
            ("temperature", "entry", None),
            ("medium", "entry", None),
            ("custom_motor", "entry", None),
            ("flush_seal_housing", "checkbutton", None)
        ]
        entries = {}
        custom_connection_entry = ttk.Entry(frame, font=("Roboto", 12))
        custom_connection_entry.grid(row=7, column=2, pady=5, padx=5, sticky=EW)
        if pump.get("connection_type") and pump["connection_type"] not in self.options.get("connection_type", []) + ["SMS", "DR", "BSP"]:
            custom_connection_entry.insert(0, pump["connection_type"])
        custom_connection_entry.grid_remove()
        custom_seal_entry = ttk.Entry(frame, font=("Roboto", 12))
        custom_seal_entry.grid(row=9, column=2, pady=5, padx=5, sticky=EW)
        if pump.get("mechanical_seals") and pump["mechanical_seals"] not in self.options.get("mechanical_seals", ["C/SS", "TC/TC", "SC/SC", "Ceramic", "Other"]):
            custom_seal_entry.insert(0, pump["mechanical_seals"])
        custom_seal_entry.grid_remove()

        for i, (field, widget_type, opts) in enumerate(fields):
            ttk.Label(frame, text=f"{field.replace('_', ' ').title()}:", font=("Roboto", 14)).grid(row=i, column=0, pady=5, sticky=W)
            value = pump.get(field, "")
            if widget_type == "entry":
                entry = ttk.Entry(frame, font=("Roboto", 12))
                entry.insert(0, value if value else "")
                if field == "serial_number":
                    entry.configure(state="readonly")
            elif widget_type == "combobox":
                entry = ttk.Combobox(frame, values=opts, font=("Roboto", 12), state="readonly")
                if field == "connection_type":
                    connection_combobox = entry
                    entry.set(value if value in opts else "Other" if value else opts[0] if opts else "")
                    if entry.get() == "Other":
                        custom_connection_entry.grid()

                    def on_connection_select(event):
                        if connection_combobox.get() == "Other":
                            custom_connection_entry.grid()
                        else:
                            custom_connection_entry.grid_remove()

                    connection_combobox.bind("<<ComboboxSelected>>", on_connection_select)
                elif field == "mechanical_seals":
                    seal_combobox = entry
                    entry.set(value if value in opts else "Other" if value else opts[0] if opts else "")
                    if entry.get() == "Other":
                        custom_seal_entry.grid()

                    def on_seal_select(event):
                        if seal_combobox.get() == "Other":
                            custom_seal_entry.grid()
                        else:
                            custom_seal_entry.grid_remove()

                    seal_combobox.bind("<<ComboboxSelected>>", on_seal_select)
                else:
                    entry.set(value if value in opts else opts[0] if opts else "")
            elif widget_type == "checkbutton":
                entry = ttk.Checkbutton(frame, text="", bootstyle="success-round-toggle")
                entry.state(['selected'] if value == "Yes" else ['!selected'])
            elif widget_type == "label":
                entry = ttk.Label(frame, text=value if value else "", font=("Roboto", 12))
            entry.grid(row=i, column=1, pady=5, sticky=EW)
            entries[field] = entry

        frame.grid_columnconfigure(1, weight=1)

        def save_changes():
            data = {key: entry.get() if isinstance(entry, (ttk.Entry, ttk.Combobox)) else "Yes" if entry.instate(['selected']) else "No" if isinstance(entry, ttk.Checkbutton) else entry.cget("text") for key, entry in entries.items()}
            data["connection_type"] = custom_connection_entry.get() if data["connection_type"] == "Other" else data["connection_type"]
            data["mechanical_seals"] = custom_seal_entry.get() if data["mechanical_seals"] == "Other" else data["mechanical_seals"]
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE pumps 
                        SET pump_model = ?, configuration = ?, customer = ?, branch = ?, impeller_size = ?, 
                            connection_type = ?, o_ring_material = ?, mechanical_seals = ?, 
                            temperature = ?, medium = ?, custom_motor = ?, flush_seal_housing = ?, 
                            assembly_part_number = ?
                        WHERE serial_number = ?
                    """, (data["pump_model"], data["configuration"], data["customer"], data["branch"], data["impeller_size"],
                          data["connection_type"], data["o_ring_material"], data["mechanical_seals"],
                          data["temperature"], data["medium"], data["custom_motor"], data["flush_seal_housing"],
                          data["assembly_part_number"], serial_number))
                    conn.commit()
                logger.info(f"Pump {serial_number} updated by {self.username}")
                self.refresh_all_pumps()
                self.refresh_stock_pumps()
                edit_window.destroy()
            except Exception as e:
                logger.error(f"Failed to save pump changes: {e}")
                Messagebox.show_error("Error", f"Failed to save changes: {e}")

        def retest_pump():
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE pumps SET status = 'Testing' WHERE serial_number = ?", (serial_number,))
                    conn.commit()

                    config = load_config()
                    confirmation_dir = config["document_dirs"]["confirmation"]
                    os.makedirs(confirmation_dir, exist_ok=True)
                    confirmation_path = os.path.join(confirmation_dir, f"confirmation_retest_{serial_number}.pdf")
                    confirmation_data = {
                        "serial_number": serial_number,
                        "assembly_part_number": pump.get("assembly_part_number", "N/A"),
                        "status": "Sent for Retest",
                        "action_by": self.username,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    generate_pdf_notification(serial_number, confirmation_data, title=f"Confirmation - Retest {serial_number}", output_path=confirmation_path)

                    subject = f"Pump {serial_number} Sent for Retest"
                    body_content = f"""
                        <p>Pump {serial_number} has been sent for retesting.</p>
                        <h3 style="color: #34495e;">Pump Details</h3>
                        {generate_pump_details_table(pump)}
                    """
                    threading.Thread(target=send_email, args=(STORES_EMAIL, subject, "Dear Stores Team,", body_content, "Regards,<br>Guth Pump Registry", confirmation_path), daemon=True).start()

                self.refresh_all_pumps()
                self.refresh_stock_pumps()
                edit_window.destroy()
            except Exception as e:
                logger.error(f"Failed to retest pump: {e}")
                Messagebox.show_error("Error", f"Failed to retest pump: {e}")

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Save", command=save_changes, bootstyle="success", style="large.TButton").pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Retest", command=retest_pump, bootstyle="warning", style="large.TButton").pack(side=LEFT, padx=5)

def show_dashboard(root, username, role, logout_callback):
    """Wrapper function to instantiate the dashboard class."""
    dashboard = PumpOriginatorDashboard(root, username, role, logout_callback)
    return dashboard.main_frame

# Simulated login screen for testing
def show_login_screen(root):
    """Display a simple login screen for testing."""
    for widget in root.winfo_children():
        widget.destroy()
    ttk.Label(root, text="Login Screen", font=("Roboto", 18, "bold")).pack(pady=20)
    ttk.Label(root, text="Username:").pack()
    username_entry = ttk.Entry(root)
    username_entry.pack(pady=5)
    ttk.Label(root, text="Password:").pack()
    password_entry = ttk.Entry(root, show="*")
    password_entry.pack(pady=5)
    ttk.Button(root, text="Login", command=lambda: show_dashboard(root, username_entry.get(), "Pump Originator", test_logout)).pack(pady=10)

def logout_callback(root):
    """Callback to return to login screen."""
    logger.info("Logging off and returning to login screen")
    show_login_screen(root)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    def test_logout():
        logout_callback(root)  # Use the simulated logout callback
    show_dashboard(root, "testuser", "Pump Originator", test_logout)
    root.mainloop()