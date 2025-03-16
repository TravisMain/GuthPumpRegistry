import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
from database import connect_db, create_pump
import os
from utils.config import get_logger

logger = get_logger("dashboard_gui")
LOGO_PATH = r"C:\Users\travism\source\repos\GuthPumpRegistry\assets\logo.png"
BUILD_NUMBER = "1.0.0"

def show_dashboard(root, username, role, logout_callback):
    for widget in root.winfo_children():
        widget.destroy()

    root.state('zoomed')  # Full-screen mode

    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Header with logo and intro
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
            logger.error(f"Dashboard logo load failed: {str(e)}")

    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Create new pump assemblies and view all pumps in the database.", font=("Roboto", 12)).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Create New Pump Assembly", font=("Roboto", 16, "bold")).pack(pady=10)

    # Create Pump Form
    form_frame = ttk.LabelFrame(main_frame, text="New Pump Details", padding=20, bootstyle="default")
    form_frame.pack(fill=X, padx=10, pady=10)

    fields = [
        ("Customer", "entry", None, True),
        ("Branch", "combobox", ["Guth Pinetown", "Guth Durban", "Guth Cape Town"], True),
        ("Pump Model", "combobox", ["P1 3.0kW", "P2 5.0kW", "P3 7.5kW"], True),
        ("Configuration", "combobox", ["Standard", "High Flow", "Custom"], True),
        ("Impeller Size", "combobox", ["Small", "Medium", "Large"], True),
        ("Connection Type", "combobox", ["Flange", "Threaded", "Welded"], True),
        ("Pressure Required", "entry", None, False),
        ("Flow Rate Required", "entry", None, False),
        ("Custom Motor", "entry", None, False),
        ("Flush Seal Housing", "checkbutton", None, False)
    ]
    entries = {}
    for i, (label, widget_type, options, required) in enumerate(fields):
        ttk.Label(form_frame, text=f"{label}{' *' if required else ''}:", font=("Roboto", 12)).grid(row=i, column=0, pady=5, sticky=W)
        if widget_type == "entry":
            entry = ttk.Entry(form_frame, font=("Roboto", 12))
        elif widget_type == "combobox":
            entry = ttk.Combobox(form_frame, values=options, font=("Roboto", 12), state="readonly")
            entry.set(options[0])
        elif widget_type == "checkbutton":
            entry = ttk.Checkbutton(form_frame, text="", bootstyle="success-round-toggle")
        entry.grid(row=i, column=1, pady=5, sticky=EW)
        entries[label.lower().replace(" ", "_")] = entry

    form_frame.grid_columnconfigure(1, weight=1)
    error_label = ttk.Label(form_frame, text="", font=("Roboto", 12), bootstyle="danger")
    error_label.grid(row=len(fields), column=0, columnspan=2, pady=5)

    def submit_pump():
        data = {key: (entry.get() if isinstance(entry, (ttk.Entry, ttk.Combobox)) else "Yes" if entry.instate(['selected']) else "No")
                for key, entry in entries.items()}
        required_fields = [f[0].lower().replace(" ", "_") for f in fields if f[3]]
        missing = [field.replace("_", " ").title() for field in required_fields if not data[field]]
        if missing:
            error_label.config(text=f"Missing required fields: {', '.join(missing)}")
            return

        with connect_db() as conn:
            cursor = conn.cursor()
            serial = create_pump(cursor, data["pump_model"], data["configuration"], data["customer"], username,
                                data["branch"], data["impeller_size"], data["connection_type"], data["pressure_required"],
                                data["flow_rate_required"], data["custom_motor"], data["flush_seal_housing"])
            conn.commit()
            logger.info(f"New pump created by {username}: {serial}")
            error_label.config(text="Pump created successfully!", bootstyle="success")
            refresh_pump_list()

    ttk.Button(form_frame, text="Submit", command=submit_pump, bootstyle="success", style="large.TButton").grid(row=len(fields) + 1, column=0, columnspan=2, pady=10)

    # Pump List
    pump_list_frame = ttk.LabelFrame(main_frame, text="All Pumps", padding=10)
    pump_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration", "Impeller Size", "Connection Type", 
               "Pressure Required", "Flow Rate Required", "Custom Motor", "Flush Seal Housing", "Status")
    tree = ttk.Treeview(pump_list_frame, columns=columns, show="headings", height=10)
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
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT serial_number, customer, branch, pump_model, configuration, impeller_size, connection_type, 
                       pressure_required, flow_rate_required, custom_motor, flush_seal_housing, status 
                FROM pumps
            """)
            for pump in cursor.fetchall():
                tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"], pump["pump_model"], 
                                            pump["configuration"], pump["impeller_size"], pump["connection_type"], 
                                            pump["pressure_required"], pump["flow_rate_required"], pump["custom_motor"], 
                                            pump["flush_seal_housing"], pump["status"]))

    refresh_pump_list()
    tree.bind("<Double-1>", lambda event: edit_pump_window(main_frame, tree, root, username, role, logout_callback))

    # Logoff, Copyright, and Build
    ttk.Button(main_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=10)
    ttk.Label(main_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(main_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

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
    edit_window.geometry("520x600")

    header_frame = ttk.Frame(edit_window, style="white.TFrame")
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
            logger.error(f"Edit pump logo load failed: {str(e)}")
    ttk.Label(header_frame, text="View or edit pump details.", font=("Roboto", 12)).pack(anchor=W, padx=10)

    frame = ttk.Frame(edit_window, padding=20)
    frame.pack(fill=BOTH, expand=True)

    fields = [
        ("serial_number", "entry", None),
        ("customer", "entry", None),
        ("branch", "combobox", ["Guth Pinetown", "Guth Durban", "Guth Cape Town"]),
        ("pump_model", "combobox", ["P1 3.0kW", "P2 5.0kW", "P3 7.5 TextW"]),
        ("configuration", "combobox", ["Standard", "High Flow", "Custom"]),
        ("impeller_size", "combobox", ["Small", "Medium", "Large"]),
        ("connection_type", "combobox", ["Flange", "Threaded", "Welded"]),
        ("pressure_required", "entry", None),
        ("flow_rate_required", "entry", None),
        ("custom_motor", "entry", None),
        ("flush_seal_housing", "checkbutton", None)
    ]
    entries = {}
    for i, (field, widget_type, options) in enumerate(fields):
        ttk.Label(frame, text=f"{field.replace('_', ' ').title()}:", font=("Roboto", 14)).grid(row=i, column=0, pady=5, sticky=W)
        if widget_type == "entry":
            entry = ttk.Entry(frame, font=("Roboto", 12))
            entry.insert(0, pump_dict.get(field, ""))
            if field == "serial_number":
                entry.configure(state="readonly")
        elif widget_type == "combobox":
            entry = ttk.Combobox(frame, values=options, font=("Roboto", 12), state="readonly")
            entry.set(pump_dict.get(field, options[0]))
        elif widget_type == "checkbutton":
            entry = ttk.Checkbutton(frame, text="", bootstyle="success-round-toggle")
            entry.state(['selected'] if pump_dict.get(field) == "Yes" else ['!selected'])
        entry.grid(row=i, column=1, pady=5, sticky=EW)
        entries[field] = entry

    frame.grid_columnconfigure(1, weight=1)

    def save_changes():
        data = {key: (entry.get() if isinstance(entry, (ttk.Entry, ttk.Combobox)) else "Yes" if entry.instate(['selected']) else "No")
                for key, entry in entries.items()}
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
            show_dashboard(root, username, role, logout_callback)  # Refresh dashboard
            edit_window.destroy()

    ttk.Button(frame, text="Save", command=save_changes, bootstyle="success", style="large.TButton").grid(row=len(fields), column=0, columnspan=2, pady=10)