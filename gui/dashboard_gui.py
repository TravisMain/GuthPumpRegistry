import ttkbootstrap as ttk
from ttkbootstrap.constants import *
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
LOGO_PATH = r"C:\Users\travism\source\repos\GuthPumpRegistry\assets\logo.png"
OPTIONS_PATH = r"C:\Users\travism\source\repos\GuthPumpRegistry\assets\pump_options.json"
BUILD_NUMBER = "1.0.0"
STORES_EMAIL = "stores@guth.co.za"  # Update as needed

def load_options():
    with open(OPTIONS_PATH, "r") as f:
        return json.load(f)

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

    # Form
    form_frame = ttk.LabelFrame(main_frame, text="New Pump Details", padding=20, bootstyle="default")
    form_frame.pack(fill=X, padx=10, pady=10)

    fields = [
        ("Customer", "entry", None, True),
        ("Branch", "combobox", options["branch"], True),
        ("Pump Model", "combobox", options["pump_model"], True),
        ("Configuration", "combobox", options["configuration"], True),
        ("Impeller Size", "combobox", options["impeller_size"]["PT 0.55KW"], True),
        ("Connection Type", "combobox", options["connection_type"], True),
        ("Pressure Required", "entry", None, False),
        ("Flow Rate Required", "entry", None, False),
        ("Custom Motor", "entry", None, False),
        ("Flush Seal Housing", "checkbutton", None, False)
    ]
    entries = {}
    other_entry = ttk.Entry(form_frame, font=("Roboto", 12), state="disabled")
    for i, (label, widget_type, opts, required) in enumerate(fields):
        ttk.Label(form_frame, text=f"{label}{' *' if required else ''}:", font=("Roboto", 12)).grid(row=i, column=0, pady=5, sticky=W)
        if widget_type == "entry":
            entry = ttk.Entry(form_frame, font=("Roboto", 12))
        elif widget_type == "combobox":
            entry = ttk.Combobox(form_frame, values=opts, font=("Roboto", 12), state="readonly")
            entry.set(opts[0])
        elif widget_type == "checkbutton":
            entry = ttk.Checkbutton(form_frame, text="", bootstyle="success-round-toggle")
        entry.grid(row=i, column=1, pady=5, sticky=EW)
        entries[label.lower().replace(" ", "_")] = entry

    # Bind events after entries is populated
    def update_impeller(*args):
        model = entries["pump_model"].get()
        entries["impeller_size"]["values"] = options["impeller_size"][model]
        entries["impeller_size"].set(options["impeller_size"][model][0])

    def toggle_other(*args):
        if entries["connection_type"].get() == "Other":
            other_entry.grid(row=fields.index(("Connection Type", "combobox", options["connection_type"], True)), column=2, pady=5, sticky=EW)
            other_entry.configure(state="normal")
        else:
            other_entry.grid_remove()
            other_entry.configure(state="disabled")

    entries["pump_model"].bind("<<ComboboxSelected>>", update_impeller)
    entries["connection_type"].bind("<<ComboboxSelected>>", toggle_other)

    form_frame.grid_columnconfigure(1, weight=1)
    error_label = ttk.Label(form_frame, text="", font=("Roboto", 12), bootstyle="danger")
    error_label.grid(row=len(fields), column=0, columnspan=2, pady=5)

    def submit_pump():
        data = {}
        for key, entry in entries.items():
            if isinstance(entry, (ttk.Entry, ttk.Combobox)):
                data[key] = entry.get()
            elif isinstance(entry, ttk.Checkbutton):
                data[key] = "Yes" if entry.instate(['selected']) else "No"
        if data["connection_type"] == "Other":
            data["connection_type"] = other_entry.get()
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
            # Generate BOM (assuming bom.json exists)
            with open(r"C:\Users\travism\source\repos\GuthPumpRegistry\assets\bom.json", "r") as f:
                bom_data = json.load(f)
                for part in bom_data.get(data["pump_model"], []):
                    cursor.execute("INSERT INTO bom_items (serial_number, part_name, part_code, quantity) VALUES (?, ?, ?, ?)",
                                  (serial, part["part_name"], part["part_code"], part["quantity"]))
            conn.commit()
            logger.info(f"New pump created by {username}: {serial} with BOM")

        threading.Thread(target=send_email, args=(serial, data), daemon=True).start()
        threading.Thread(target=print_confirmation, args=(serial, data), daemon=True).start()

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

    # Footer
    ttk.Button(main_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=10)
    ttk.Label(main_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(main_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

def send_email(serial, data):
    try:
        msg = MIMEText(f"New pump {serial} is ready for stock pull.\nDetails:\n{json.dumps(data, indent=2)}")
        msg["Subject"] = f"New Pump Assembly: {serial}"
        msg["From"] = "noreply@guth.co.za"
        msg["To"] = STORES_EMAIL
        with smtplib.SMTP("smtp.guth.co.za") as server:
            server.login("username", "password")
            server.send_message(msg)
        logger.info(f"Email sent for pump {serial}")
    except Exception as e:
        logger.error(f"Email send failed for {serial}: {str(e)}")

def print_confirmation(serial, data):
    try:
        pdf_path = f"C:/Users/travism/source/repos/GuthPumpRegistry/data/pump_{serial}_confirmation.pdf"
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
    edit_window.geometry("702x810")  # 35% bigger than 520x600

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

    # Load options for dynamic fields
    options = load_options()
    fields = [
        ("serial_number", "entry", None),
        ("customer", "entry", None),
        ("branch", "combobox", options["branch"]),
        ("pump_model", "combobox", options["pump_model"]),
        ("configuration", "combobox", options["configuration"]),
        ("impeller_size", "combobox", options["impeller_size"][pump_dict.get("pump_model", "PT 0.55KW")]),
        ("connection_type", "combobox", options["connection_type"]),
        ("pressure_required", "entry", None),
        ("flow_rate_required", "entry", None),
        ("custom_motor", "entry", None),
        ("flush_seal_housing", "checkbutton", None)
    ]
    entries = {}
    for i, (field, widget_type, opts) in enumerate(fields):
        ttk.Label(frame, text=f"{field.replace('_', ' ').title()}:", font=("Roboto", 14)).grid(row=i, column=0, pady=5, sticky=W)
        value = pump_dict.get(field, "")
        if widget_type == "entry":
            entry = ttk.Entry(frame, font=("Roboto", 12))
            entry.insert(0, value if value else "")
            if field == "serial_number":
                entry.configure(state="readonly")
        elif widget_type == "combobox":
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

    ttk.Button(frame, text="Save", command=save_changes, bootstyle="success", style="large.TButton").grid(row=len(fields), column=0, columnspan=2, pady=10)