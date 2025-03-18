import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox  # For error messages
from PIL import Image, ImageTk
from database import connect_db, create_pump
import os
import json
import smtplib
from email.mime.text import MIMEText
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import threading
from utils.config import get_logger

logger = get_logger("dashboard_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
OPTIONS_PATH = os.path.join(BASE_DIR, "assets", "pump_options.json")
BUILD_NUMBER = "1.0.0"
STORES_EMAIL = "stores@guth.co.za"  # Update as needed

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
        ("Pressure Required", "entry", None, False),
        ("Flow Rate Required", "entry", None, False),
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
                data[key] = entry.get()
            elif isinstance(entry, ttk.Checkbutton):
                data[key] = "Yes" if entry.instate(['selected']) else "No"
        if data["connection_type"] == "Other":
            data["connection_type"] = other_entry.get()
        if data["impeller_size"] == "Other":
            data["impeller_size"] = custom_impeller_entry.get().strip()
            if not data["impeller_size"]:
                error_label.config(text="Please enter a custom impeller size.")
                return

        required_fields = [f[0].lower().replace(" ", "_") for f in fields if f[3]]
        missing = [field.replace("_", " ").title() for field in required_fields if not data[field]]
        if missing:
            error_label.config(text=f"Missing required fields: {', '.join(missing)}")
            return

        with connect_db() as conn:
            cursor = conn.cursor()
            serial = create_pump(cursor, data["pump_model"], data["configuration"], data["customer"], username,
                                data["branch"], data["impeller_size"], data["connection_type"], data["pressure_required"],
                                data["flow_rate_required"], data["custom_motor"], data["flush_seal_housing"], insert_bom=True)
            conn.commit()
            logger.info(f"New pump created by {username}: {serial} with BOM")

        threading.Thread(target=send_email, args=(serial, data), daemon=True).start()
        threading.Thread(target=print_confirmation, args=(serial, data), daemon=True).start()

        error_label.config(text="Pump created successfully!", bootstyle="success")
        refresh_pump_list()

    # Place Submit and Logoff buttons side by side
    ttk.Button(form_frame, text="Submit", command=submit_pump, bootstyle="success", style="large.TButton").grid(row=len(fields) + 1, column=0, pady=5, padx=5, sticky=W)
    ttk.Button(form_frame, text="Logoff", command=logout_callback, bootstyle="secondary", style="large.TButton").grid(row=len(fields) + 1, column=1, pady=5, padx=5, sticky=W)

    # Footer
    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=5, fill=X)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(expand=True)
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack(expand=True)

    # Pump List with Search and Filter
    pump_list_frame = ttk.LabelFrame(main_frame, text="All Pumps", padding=10)
    pump_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

    # Search and Filter Section
    search_filter_frame = ttk.Frame(pump_list_frame)
    search_filter_frame.pack(fill=X, pady=(0, 5))

    ttk.Label(search_filter_frame, text="Search by Serial Number:", font=("Roboto", 10)).pack(side=LEFT, padx=5)
    search_entry = ttk.Entry(search_filter_frame, font=("Roboto", 10), width=20)
    search_entry.pack(side=LEFT, padx=5)
    CustomTooltip(search_entry, "Enter a serial number to search (partial matches allowed)")

    ttk.Label(search_filter_frame, text="Filter by Status:", font=("Roboto", 10)).pack(side=LEFT, padx=5)
    filter_combobox = ttk.Combobox(search_filter_frame, values=["All", "Pending", "Testing", "Completed"], font=("Roboto", 10), state="readonly")
    filter_combobox.set("All")
    filter_combobox.pack(side=LEFT, padx=5)
    CustomTooltip(filter_combobox, "Filter pumps by their current status")

    # Pump List Treeview
    columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration", "Impeller Size", "Connection Type", 
               "Pressure Required", "Flow Rate Required", "Custom Motor", "Flush Seal Housing", "Status")
    tree = ttk.Treeview(pump_list_frame, columns=columns, show="headings", height=12)  # Increased height for more rows
    for col in columns:
        tree.heading(col, text=col, anchor=W)
        tree.column(col, width=120, anchor=W)
    tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar = ttk.Scrollbar(pump_list_frame, orient=VERTICAL, command=tree.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    tree.configure(yscrollcommand=scrollbar.set)

    def refresh_pump_list():
        for item in tree.get_children():
            tree.delete(item)
        search_term = search_entry.get().lower()
        filter_status = filter_combobox.get()

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
                # Apply search filter on serial number
                if search_term in pump["serial_number"].lower():
                    tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"], pump["pump_model"], 
                                                pump["configuration"], pump["impeller_size"], pump["connection_type"], 
                                                pump["pressure_required"], pump["flow_rate_required"], pump["custom_motor"], 
                                                pump["flush_seal_housing"], pump["status"]))

    # Bind search and filter updates
    search_entry.bind("<KeyRelease>", lambda event: refresh_pump_list())
    filter_combobox.bind("<<ComboboxSelected>>", lambda event: refresh_pump_list())

    refresh_pump_list()
    tree.bind("<Double-1>", lambda event: edit_pump_window(main_frame, tree, root, username, role, logout_callback))

    return main_frame

def send_email(serial, data):
    try:
        msg = MIMEText(f"New pump {serial} is ready for stock pull.\nDetails:\n{json.dumps(data, indent=2)}")
        msg["Subject"] = f"New Pump Assembly: {serial}"
        msg["From"] = "noreply@guth.co.za"
        msg["To"] = STORES_EMAIL
        with smtplib.SMTP("smtp.guth.co.za") as server:
            server.login("username", "password")  # Update credentials
            server.send_message(msg)
        logger.info(f"Email sent for pump {serial}")
    except Exception as e:
        logger.error(f"Email send failed for {serial}: {str(e)}")

def print_confirmation(serial, data):
    try:
        pdf_path = os.path.join(BASE_DIR, "data", f"pump_{serial}_confirmation.pdf")
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, f"New Pump Assembly Confirmation: {serial}")
        c.drawString(100, 730, "Instructions: Please pull stock for the following pump:")
        y = 710
        for key, value in data.items():
            c.drawString(100, y, f"{key.replace('_', ' ').title()}: {value}")
            y -= 20
        c.showPage()
        c.save()
        os.startfile(pdf_path, "print")
        logger.info(f"Confirmation printed for pump {serial}")
    except Exception as e:
        logger.error(f"Print failed for {serial}: {str(e)}")

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
    if pump_dict.get("impeller_size") not in options["impeller_size"][pump_dict.get("pump_model", "PT 0.55KW")]:
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
                initial_pump_model = pump_dict.get("pump_model", "PT 0.55KW")
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