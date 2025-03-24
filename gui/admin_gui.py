import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageTk
from database import connect_db, DB_PATH
import sqlite3
import os
from datetime import datetime, timedelta
import shutil
import bcrypt
import re
import pandas as pd
import tkinter.filedialog as filedialog
from utils.config import get_logger
import json
from export_utils import generate_pdf_notification
import smtplib
from email.mime.text import MIMEText

logger = get_logger("admin_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
BUILD_NUMBER = "1.0.0"

# Default directories if not specified in config
DEFAULT_DIRS = {
    "certificate": os.path.join(BASE_DIR, "certificates"),
    "bom": os.path.join(BASE_DIR, "boms"),
    "confirmation": os.path.join(BASE_DIR, "confirmations"),
    "reports": os.path.join(BASE_DIR, "reports"),
    "excel_exports": os.path.join(BASE_DIR, "exports")
}

# Default email settings (updated for Gmail)
DEFAULT_EMAIL_SETTINGS = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": "587",
    "smtp_username": "",
    "smtp_password": "",
    "sender_email": "",
    "use_tls": True
}

def load_config():
    """Load configuration from config.json, or create it with defaults if it doesn't exist."""
    if not os.path.exists(CONFIG_PATH):
        # Create default config
        config = {
            "document_dirs": DEFAULT_DIRS,
            "email_settings": DEFAULT_EMAIL_SETTINGS
        }
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
    if "email_settings" not in config:
        config["email_settings"] = DEFAULT_EMAIL_SETTINGS
    for key, default_value in DEFAULT_EMAIL_SETTINGS.items():
        if key not in config["email_settings"]:
            config["email_settings"][key] = default_value
    return config

def save_config(config):
    """Save configuration to config.json."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
    logger.info(f"Saved config to {CONFIG_PATH}")

def show_admin_gui(root, username, logout_callback):
    # Set the window size to better utilize screen space
    root.geometry("1200x800")  # Increased window size
    root.minsize(1000, 600)    # Set a minimum size to ensure content is visible

    for widget in root.winfo_children():
        widget.destroy()

    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

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
            logger.error(f"Admin logo load failed: {str(e)}")

    ttk.Label(header_frame, text=f"Welcome, {username} (Admin)", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Manage pumps, users, and backups efficiently.", font=("Roboto", 12)).pack(anchor=W, padx=10)

    # Custom tab style for main notebook
    style = ttk.Style()
    style.configure("Custom.TNotebook", tabposition="nw")
    style.configure("Custom.TNotebook.Tab", 
                    background="#2c3e50", 
                    foreground="white", 
                    font=("Roboto", 12), 
                    padding=[12, 6])
    style.map("Custom.TNotebook.Tab", 
              background=[("selected", "#ECECEC"), ("!selected", "#2c3e50")], 
              foreground=[("selected", "black"), ("!selected", "white")])

    notebook = ttk.Notebook(main_frame, style="Custom.TNotebook")
    notebook.pack(fill=BOTH, expand=True, pady=10)

    pumps_frame = ttk.Frame(notebook)
    notebook.add(pumps_frame, text="Pumps")
    show_pumps_tab(pumps_frame)

    user_frame = ttk.Frame(notebook)
    notebook.add(user_frame, text="Users")
    show_user_tab(user_frame)

    reports_frame = ttk.Frame(notebook)
    notebook.add(reports_frame, text="Reports")
    show_reports_tab(reports_frame)

    activity_frame = ttk.Frame(notebook)
    notebook.add(activity_frame, text="Activity Log")
    show_activity_log_tab(activity_frame)

    backup_frame = ttk.Frame(notebook)
    notebook.add(backup_frame, text="Backup")
    show_backup_tab(backup_frame)

    config_frame = ttk.Frame(notebook)
    notebook.add(config_frame, text="Configuration")
    show_config_tab(config_frame)

    email_frame = ttk.Frame(notebook)
    notebook.add(email_frame, text="Email")
    show_email_tab(email_frame)

    ttk.Button(main_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=10)
    ttk.Label(main_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(main_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

def show_pumps_tab(frame):
    if not hasattr(frame, 'tree'):
        frame.tree = ttk.Treeview(frame, columns=("Serial Number", "Pump Model", "Configuration", "Status", "Customer", "Created At"), show="headings", height=20)
        for col in frame.tree["columns"]:
            frame.tree.heading(col, text=col, anchor=W)
            frame.tree.column(col, anchor=W)
        frame.tree.column("Serial Number", width=150)
        frame.tree.column("Pump Model", width=150)
        frame.tree.column("Configuration", width=150)
        frame.tree.column("Status", width=100)
        frame.tree.column("Customer", width=150)
        frame.tree.column("Created At", width=120)
        frame.tree.pack(fill=BOTH, expand=True, padx=10, pady=10)
        frame.tree.bind("<Double-1>", lambda event: edit_pump_window(frame, frame.tree))

        # Add button frame for actions
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=5)

        def export_to_excel():
            config = load_config()
            export_dir = config["document_dirs"]["excel_exports"]
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
                logger.info(f"Created directory {export_dir} for Excel exports")

            # Fetch all pump details from the database
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT serial_number, pump_model, configuration, status, customer, requested_by,
                           branch, impeller_size, connection_type, pressure_required, flow_rate_required,
                           custom_motor, flush_seal_housing, created_at
                    FROM pumps
                """)
                pumps = cursor.fetchall()

            # Convert to DataFrame
            columns = [
                "Serial Number", "Pump Model", "Configuration", "Status", "Customer", "Requested By",
                "Branch", "Impeller Size", "Connection Type", "Pressure Required", "Flow Rate Required",
                "Custom Motor", "Flush Seal Housing", "Created At"
            ]
            # Convert each sqlite3.Row to a tuple directly
            data = [tuple(pump) for pump in pumps]
            df = pd.DataFrame(data, columns=columns)

            # Export to Excel
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(export_dir, f"pumps_export_{timestamp}.xlsx")
            try:
                df.to_excel(filename, index=False)
                logger.info(f"Exported pumps to {filename}")
                Messagebox.show_info("Export Successful", f"Pumps exported to {filename}")
            except Exception as e:
                logger.error(f"Failed to export pumps to Excel: {str(e)}")
                Messagebox.show_error("Export Failed", f"Error: {str(e)}")

        ttk.Button(button_frame, text="Export to Excel", command=export_to_excel, bootstyle="primary", style="large.TButton").pack(side=LEFT, padx=5)

    for item in frame.tree.get_children():
        frame.tree.delete(item)
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT serial_number, pump_model, configuration, status, customer, created_at FROM pumps")
        pumps = cursor.fetchall()
        for pump in pumps:
            frame.tree.insert("", END, values=(pump["serial_number"], pump["pump_model"], pump["configuration"], pump["status"], pump["customer"], pump["created_at"]))

def edit_pump_window(parent_frame, tree):
    logger.debug("Entering edit_pump_window")
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    item = tree.item(selected[0])
    values = item["values"]
    serial_number = values[0]
    logger.debug(f"Selected serial_number from Treeview: {serial_number}")

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pumps WHERE serial_number = ?", (serial_number,))
        pump = cursor.fetchone()
        if pump:
            pump_dict = dict(pump)
            logger.debug(f"Pump data fetched from DB: {pump_dict}")
        else:
            logger.warning(f"No pump found in DB for serial_number: {serial_number}")
            pump_dict = {"serial_number": serial_number}

    edit_window = ttk.Toplevel(parent_frame)
    edit_window.title(f"Edit Pump {serial_number}")
    edit_window.geometry("520x500")

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
    ttk.Label(header_frame, text="Edit pump details or delete.", font=("Roboto", 12)).pack(anchor=W, padx=10)

    frame = ttk.Frame(edit_window, padding=20)
    frame.pack(fill=BOTH, expand=True)

    fields = [
        "serial_number", "pump_model", "configuration", "customer", "requested_by",
        "branch", "impeller_size", "connection_type", "pressure_required",
        "flow_rate_required", "custom_motor", "flush_seal_housing", "created_at"
    ]
    options = {
        "pump_model": ["P1 3.0kW", "P2 5.0kW", "P3 7.5kW"],
        "configuration": ["Standard", "High Flow", "Custom"],
        "customer": ["Guth Pinetown", "Guth Durban", "Guth Cape Town"],
        "branch": ["Guth Pinetown", "Guth Durban", "Guth Cape Town"],
        "impeller_size": ["Small", "Medium", "Large"],
        "connection_type": ["Flange", "Threaded", "Welded"],
        "custom_motor": ["Yes", "No"],
        "flush_seal_housing": ["Yes", "No"]
    }
    entries = {}
    for i, field in enumerate(fields):
        ttk.Label(frame, text=f"{field.replace('_', ' ').title()}:", font=("Roboto", 14)).grid(row=i, column=0, pady=5, sticky=W)
        if field in ["serial_number", "created_at", "requested_by"]:
            entry = ttk.Entry(frame, font=("Roboto", 12))
            entry.insert(0, pump_dict.get(field, "") or "")
            entry.configure(state="readonly")
        elif field in options:
            entry = ttk.Combobox(frame, values=options[field], font=("Roboto", 12), state="readonly")
            value = pump_dict.get(field, options[field][0])
            if value not in options[field]:
                logger.warning(f"Invalid value '{value}' for field '{field}'. Falling back to default: {options[field][0]}")
                value = options[field][0]
            entry.set(value)
        else:
            entry = ttk.Entry(frame, font=("Roboto", 12))
            entry.insert(0, pump_dict.get(field, "") or "")
        entry.grid(row=i, column=1, pady=5, sticky=EW)
        entries[field] = entry

    frame.grid_columnconfigure(1, weight=1)

    def save_changes():
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pumps 
                SET pump_model = ?, configuration = ?, customer = ?, requested_by = ?, 
                    branch = ?, impeller_size = ?, connection_type = ?, pressure_required = ?, 
                    flow_rate_required = ?, custom_motor = ?, flush_seal_housing = ?
                WHERE serial_number = ?
            """, (entries["pump_model"].get(), entries["configuration"].get(), entries["customer"].get(),
                  entries["requested_by"].get(), entries["branch"].get(), entries["impeller_size"].get(),
                  entries["connection_type"].get(), entries["pressure_required"].get(),
                  entries["flow_rate_required"].get(), entries["custom_motor"].get(),
                  entries["flush_seal_housing"].get(), serial_number))
            conn.commit()
            logger.info(f"Updated pump {serial_number}")
            show_pumps_tab(parent_frame)
            edit_window.destroy()

    def delete_pump():
        if Messagebox.yesno("Confirm Delete", f"Are you sure you want to delete pump {serial_number}?") == "Yes":
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM pumps WHERE serial_number = ?", (serial_number,))
                conn.commit()
                logger.info(f"Deleted pump {serial_number}")
                show_pumps_tab(parent_frame)
                edit_window.destroy()

    ttk.Button(frame, text="Save", command=save_changes, bootstyle="success", style="large.TButton").grid(row=len(fields), column=0, pady=10)
    ttk.Button(frame, text="Delete", command=delete_pump, bootstyle="danger", style="large.TButton").grid(row=len(fields), column=1, pady=10)

def show_user_tab(frame):
    if not hasattr(frame, 'input_frame'):
        input_frame = ttk.LabelFrame(frame, text="Add/Edit User", padding=20, bootstyle="default")
        input_frame.pack(fill=X, padx=10, pady=10)
        frame.input_frame = input_frame

        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT role FROM users")
            roles = [row["role"] for row in cursor.fetchall()] or ["Admin", "Stores", "Testing", "Pump Originator", "Approval"]

        fields = ["Username", "Password", "Role", "Name", "Surname", "Email"]
        frame.entries = {}
        for i, field in enumerate(fields):
            ttk.Label(input_frame, text=f"{field}:", font=("Roboto", 14)).grid(row=i, column=0, pady=5, sticky=W)
            if field == "Role":
                entry = ttk.Combobox(input_frame, values=roles, font=("Roboto", 12), state="readonly")
                entry.set("Pump Originator")
            else:
                entry = ttk.Entry(input_frame, font=("Roboto", 12), width=30)
            entry.grid(row=i, column=1, pady=5, padx=5, sticky=EW)
            frame.entries[field.lower()] = entry

        input_frame.grid_columnconfigure(1, weight=1)

        frame.error_label = ttk.Label(input_frame, text="", font=("Roboto", 12), bootstyle="danger")
        frame.error_label.grid(row=len(fields), column=0, columnspan=2, pady=5)

        def validate_email(email):
            pattern = r"^[a-zA-Z0.9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            return re.match(pattern, email) is not None

        def add_user():
            email = frame.entries["email"].get()
            if not validate_email(email):
                frame.error_label.config(text="Invalid email address")
                return
            with connect_db() as conn:
                cursor = conn.cursor()
                try:
                    password_hash = bcrypt.hashpw(frame.entries["password"].get().encode('utf-8'), bcrypt.gensalt())
                    cursor.execute("INSERT INTO users (username, password_hash, role, name, surname, email) VALUES (?, ?, ?, ?, ?, ?)",
                                  (frame.entries["username"].get(), password_hash, frame.entries["role"].get(),
                                   frame.entries["name"].get(), frame.entries["surname"].get(), email))
                    conn.commit()
                    logger.info(f"Added user {frame.entries['username'].get()}")
                    for entry in frame.entries.values():
                        entry.delete(0, END)
                    frame.error_label.config(text="")
                    refresh_user_list()
                except sqlite3.IntegrityError:
                    frame.error_label.config(text=f"User {frame.entries['username'].get()} already exists")
                    logger.warning(f"User {frame.entries['username'].get()} already exists")

        def edit_user():
            selected = frame.user_tree.selection()
            if not selected:
                return
            username = frame.user_tree.item(selected[0])["values"][0]
            edit_user_window(frame, username)

        def delete_user():
            selected = frame.user_tree.selection()
            if not selected:
                return
            username = frame.user_tree.item(selected[0])["values"][0]
            if Messagebox.yesno("Confirm Delete", f"Are you sure you want to delete user {username}?") == "Yes":
                with connect_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                    conn.commit()
                    logger.info(f"Deleted user {username}")
                    refresh_user_list()

        def export_to_excel():
            config = load_config()
            export_dir = config["document_dirs"]["excel_exports"]
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
                logger.info(f"Created directory {export_dir} for Excel exports")
            data = []
            for item in frame.user_tree.get_children():
                data.append(frame.user_tree.item(item)["values"])
            df = pd.DataFrame(data, columns=["Username", "Role"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(export_dir, f"users_export_{timestamp}.xlsx")
            try:
                df.to_excel(filename, index=False)
                logger.info(f"Exported users to {filename}")
                Messagebox.show_info("Export Successful", f"Users exported to {filename}")
            except Exception as e:
                logger.error(f"Failed to export users to Excel: {str(e)}")
                Messagebox.show_error("Export Failed", f"Error: {str(e)}")

        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=len(fields) + 1, column=0, columnspan=2, sticky=W, pady=10)
        ttk.Button(button_frame, text="Add User", command=add_user, bootstyle="success", style="large.TButton").pack(side=LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Edit User", command=edit_user, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Delete User", command=delete_user, bootstyle="danger", style="large.TButton").pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Export to Excel", command=export_to_excel, bootstyle="primary", style="large.TButton").pack(side=LEFT, padx=5)

    if not hasattr(frame, 'user_list_frame'):
        user_list_frame = ttk.LabelFrame(frame, text="Registered Users", padding=10)
        user_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        frame.user_list_frame = user_list_frame

        frame.user_tree = ttk.Treeview(user_list_frame, columns=("Username", "Role"), show="headings", height=15)
        frame.user_tree.heading("Username", text="Username", anchor=W)
        frame.user_tree.heading("Role", text="Role", anchor=W)
        frame.user_tree.column("Username", width=200, anchor=W)
        frame.user_tree.column("Role", width=150, anchor=W)
        frame.user_tree.pack(fill=BOTH, expand=True)

        def refresh_user_list():
            for item in frame.user_tree.get_children():
                frame.user_tree.delete(item)
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT username, role FROM users")
                for user in cursor.fetchall():
                    frame.user_tree.insert("", END, values=(user["username"], user["role"]))

        refresh_user_list()

        def on_right_click(event):
            item = frame.user_tree.identify_row(event.y)
            if item:
                frame.user_tree.selection_set(item)
                menu = ttk.Menu(frame, tearoff=0)
                menu.add_command(label="Edit", command=lambda: edit_user_window(frame, frame.user_tree.item(item)["values"][0]))
                menu.add_command(label="Delete", command=delete_user)
                menu.post(event.x_root, event.y_root)

        frame.user_tree.bind("<Button-3>", on_right_click)

def show_reports_tab(frame):
    if not hasattr(frame, 'report_frame'):
        report_frame = ttk.Frame(frame)
        report_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Title
        ttk.Label(report_frame, text="Reports", font=("Roboto", 16, "bold")).pack(pady=(0, 10))

        # Create a frame for the notebook with a scrollbar
        notebook_frame = ttk.Frame(report_frame)
        notebook_frame.pack(fill=BOTH, expand=True)

        # Canvas and scrollbar for scrollable tabs
        canvas = ttk.Canvas(notebook_frame)
        scrollbar = ttk.Scrollbar(notebook_frame, orient=HORIZONTAL, command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)

        # Configure the canvas
        canvas.configure(xscrollcommand=scrollbar.set)
        scrollbar.pack(side=BOTTOM, fill=X)
        canvas.pack(side=TOP, fill=BOTH, expand=True)
        canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Update scroll region when the frame size changes
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", on_frame_configure)

        # Custom style for the report notebook
        style = ttk.Style()
        style.configure("Report.TNotebook", tabposition="wn")  # Tabs on the left
        style.configure("Report.TNotebook.Tab", 
                        background="#2c3e50", 
                        foreground="white", 
                        font=("Roboto", 10), 
                        padding=[10, 5], 
                        width=150)
        style.map("Report.TNotebook.Tab", 
                  background=[("selected", "#ECECEC"), ("!selected", "#2c3e50")], 
                  foreground=[("selected", "black"), ("!selected", "white")])

        # Notebook for report tabs
        report_notebook = ttk.Notebook(scrollable_frame, style="Report.TNotebook")
        report_notebook.pack(fill=BOTH, expand=True, pady=5)

        # Dictionary to store Treeviews and data for each report
        frame.report_treeviews = {}
        frame.report_data = {}

        # Define reports and their configurations
        reports = [
            ("Pumps by Month", ("Month", "Count")),
            ("Pumps by Status", ("Status", "Count")),
            ("Pumps by Branch", ("Branch", "Count")),
            ("Pumps Over 2 Days in Assembly", ("Detail", "Days in Assembly")),
            ("Pumps Assembled This Week", ("Detail", "Assembled On")),
            ("Pumps Assembled This Month", ("Detail", "Assembled On")),
            ("Pumps Assembled This Year", ("Detail", "Assembled On")),
            ("Pump Model Distribution", ("Detail", "Percentage"))
        ]

        # Create a tab for each report
        for report_name, columns in reports:
            tab_frame = ttk.Frame(report_notebook)
            report_notebook.add(tab_frame, text=report_name)

            # Treeview for the report
            tree = ttk.Treeview(tab_frame, columns=columns, show="headings", height=30)
            for col in columns:
                tree.heading(col, text=col, anchor=W)
                # Adjust column widths to utilize the increased space
                if col == "Detail":
                    tree.column(col, anchor=W, width=900)  # Increased width for detailed reports
                else:
                    tree.column(col, anchor=W, width=300)  # Increased width for other columns
            tree.pack(fill=BOTH, expand=True, padx=5, pady=5)

            # Add scrollbars to the Treeview
            yscroll = ttk.Scrollbar(tab_frame, orient=VERTICAL, command=tree.yview)
            xscroll = ttk.Scrollbar(tab_frame, orient=HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
            yscroll.pack(side=RIGHT, fill=Y)
            xscroll.pack(side=BOTTOM, fill=X)

            # Store the Treeview
            frame.report_treeviews[report_name] = tree
            frame.report_data[report_name] = []

            # Export button for this report
            def create_export_function(report_name, columns):
                def export_report():
                    config = load_config()
                    export_dir = config["document_dirs"]["excel_exports"]
                    if not os.path.exists(export_dir):
                        os.makedirs(export_dir)
                        logger.info(f"Created directory {export_dir} for Excel exports")
                    df = pd.DataFrame(frame.report_data[report_name], columns=["Report", *columns])
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join(export_dir, f"{report_name.lower().replace(' ', '_')}_export_{timestamp}.xlsx")
                    try:
                        df.to_excel(filename, index=False)
                        logger.info(f"Exported {report_name} report to {filename}")
                        Messagebox.show_info("Export Successful", f"{report_name} report exported to {filename}")
                    except Exception as e:
                        logger.error(f"Failed to export {report_name} report: {str(e)}")
                        Messagebox.show_error("Export Failed", f"Error: {str(e)}")
                return export_report

            button_frame = ttk.Frame(tab_frame)
            button_frame.pack(pady=5)  # Removed fill=X to prevent stretching
            ttk.Button(button_frame, text="Export to Excel", command=create_export_function(report_name, columns), 
                       bootstyle="primary", style="large.TButton", width=15).pack(side=LEFT, padx=5)  # Set fixed width

        # Define refresh_reports
        def refresh_reports():
            today = datetime.now()

            # Clear all Treeviews and data
            for report_name, tree in frame.report_treeviews.items():
                for item in tree.get_children():
                    tree.delete(item)
                frame.report_data[report_name] = []

            with connect_db() as conn:
                cursor = conn.cursor()

                # Report 1: Pumps Created by Month (Last 6 Months)
                six_months_ago = today - timedelta(days=180)
                cursor.execute("""
                    SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
                    FROM pumps
                    WHERE created_at >= ?
                    GROUP BY month
                    ORDER BY month DESC
                """, (six_months_ago,))
                monthly_counts = cursor.fetchall()
                tree = frame.report_treeviews["Pumps by Month"]
                for month_data in monthly_counts:
                    frame.report_data["Pumps by Month"].append(("Pumps by Month", month_data["month"], month_data["count"]))
                    tree.insert("", END, values=(month_data["month"], month_data["count"]))

                # Report 2: Pumps by Status
                cursor.execute("SELECT status, COUNT(*) as count FROM pumps GROUP BY status")
                status_counts = cursor.fetchall()
                tree = frame.report_treeviews["Pumps by Status"]
                for status_data in status_counts:
                    frame.report_data["Pumps by Status"].append(("Pumps by Status", status_data["status"], status_data["count"]))
                    tree.insert("", END, values=(status_data["status"], status_data["count"]))

                # Report 3: Pumps by Branch
                cursor.execute("SELECT branch, COUNT(*) as count FROM pumps GROUP BY branch")
                branch_counts = cursor.fetchall()
                tree = frame.report_treeviews["Pumps by Branch"]
                for branch_data in branch_counts:
                    frame.report_data["Pumps by Branch"].append(("Pumps by Branch", branch_data["branch"], branch_data["count"]))
                    tree.insert("", END, values=(branch_data["branch"], branch_data["count"]))

                # Report 4: Pumps Taking Longer Than 2 Days to Assemble
                two_days_ago = today - timedelta(days=2)
                cursor.execute("""
                    SELECT p.serial_number, p.customer, p.branch, p.pump_model, p.configuration,
                           ROUND((julianday('now') - julianday(a.timestamp)), 1) as days_in_assembly,
                           SUBSTR(a.action, 6, INSTR(a.action, ' moved to') - 6) as extracted_serial
                    FROM pumps p
                    JOIN audit_log a ON p.serial_number = SUBSTR(a.action, 6, INSTR(a.action, ' moved to') - 6)
                    WHERE p.status = 'Assembler'
                    AND a.action LIKE 'Pump % moved to Assembler by %'
                    AND a.timestamp <= ?
                """, (two_days_ago,))
                long_assembly_pumps = cursor.fetchall()
                tree = frame.report_treeviews["Pumps Over 2 Days in Assembly"]
                for pump in long_assembly_pumps:
                    detail = f"{pump['serial_number']} | {pump['customer']} | {pump['branch']} | {pump['pump_model']} | {pump['configuration']}"
                    frame.report_data["Pumps Over 2 Days in Assembly"].append(("Pumps Over 2 Days in Assembly", detail, pump["days_in_assembly"]))
                    tree.insert("", END, values=(detail, f"{pump['days_in_assembly']} days"))

                # Report 5: Pumps Assembled This Week
                week_start = today - timedelta(days=today.weekday())  # Start of the week (Monday)
                cursor.execute("""
                    SELECT p.serial_number, p.customer, p.branch, p.pump_model, p.configuration, a.timestamp,
                           SUBSTR(a.action, 6, INSTR(a.action, ' moved to') - 6) as extracted_serial
                    FROM pumps p
                    JOIN audit_log a ON p.serial_number = SUBSTR(a.action, 6, INSTR(a.action, ' moved to') - 6)
                    WHERE a.action LIKE 'Pump % moved to Testing by %'
                    AND a.timestamp >= ?
                """, (week_start,))
                weekly_assembled = cursor.fetchall()
                tree = frame.report_treeviews["Pumps Assembled This Week"]
                for pump in weekly_assembled:
                    detail = f"{pump['serial_number']} | {pump['customer']} | {pump['branch']} | {pump['pump_model']} | {pump['configuration']}"
                    frame.report_data["Pumps Assembled This Week"].append(("Pumps Assembled This Week", detail, pump["timestamp"]))
                    tree.insert("", END, values=(detail, pump["timestamp"]))

                # Report 6: Pumps Assembled This Month
                month_start = today.replace(day=1)
                cursor.execute("""
                    SELECT p.serial_number, p.customer, p.branch, p.pump_model, p.configuration, a.timestamp,
                           SUBSTR(a.action, 6, INSTR(a.action, ' moved to') - 6) as extracted_serial
                    FROM pumps p
                    JOIN audit_log a ON p.serial_number = SUBSTR(a.action, 6, INSTR(a.action, ' moved to') - 6)
                    WHERE a.action LIKE 'Pump % moved to Testing by %'
                    AND a.timestamp >= ?
                """, (month_start,))
                monthly_assembled = cursor.fetchall()
                tree = frame.report_treeviews["Pumps Assembled This Month"]
                for pump in monthly_assembled:
                    detail = f"{pump['serial_number']} | {pump['customer']} | {pump['branch']} | {pump['pump_model']} | {pump['configuration']}"
                    frame.report_data["Pumps Assembled This Month"].append(("Pumps Assembled This Month", detail, pump["timestamp"]))
                    tree.insert("", END, values=(detail, pump["timestamp"]))

                # Report 7: Pumps Assembled This Year
                year_start = today.replace(month=1, day=1)
                cursor.execute("""
                    SELECT p.serial_number, p.customer, p.branch, p.pump_model, p.configuration, a.timestamp,
                           SUBSTR(a.action, 6, INSTR(a.action, ' moved to') - 6) as extracted_serial
                    FROM pumps p
                    JOIN audit_log a ON p.serial_number = SUBSTR(a.action, 6, INSTR(a.action, ' moved to') - 6)
                    WHERE a.action LIKE 'Pump % moved to Testing by %'
                    AND a.timestamp >= ?
                """, (year_start,))
                yearly_assembled = cursor.fetchall()
                tree = frame.report_treeviews["Pumps Assembled This Year"]
                for pump in yearly_assembled:
                    detail = f"{pump['serial_number']} | {pump['customer']} | {pump['branch']} | {pump['pump_model']} | {pump['configuration']}"
                    frame.report_data["Pumps Assembled This Year"].append(("Pumps Assembled This Year", detail, pump["timestamp"]))
                    tree.insert("", END, values=(detail, pump["timestamp"]))

                # Report 8: Percentage of Pumps by Model
                cursor.execute("SELECT pump_model, COUNT(*) as count FROM pumps GROUP BY pump_model")
                model_counts = cursor.fetchall()
                total_pumps = sum(model["count"] for model in model_counts)
                tree = frame.report_treeviews["Pump Model Distribution"]
                for model in model_counts:
                    percentage = (model["count"] / total_pumps * 100) if total_pumps > 0 else 0
                    detail = f"{model['pump_model']}: {model['count']} pumps"
                    frame.report_data["Pump Model Distribution"].append(("Pump Model Distribution", detail, f"{percentage:.2f}%"))
                    tree.insert("", END, values=(detail, f"{percentage:.2f}%"))

        def generate_pdf_report():
            config = load_config()
            report_dir = config["document_dirs"]["reports"]
            if not os.path.exists(report_dir):
                os.makedirs(report_dir)
                logger.info(f"Created directory {report_dir} for reports")

            # Collect report data from each Treeview
            report_data = {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pumps_by_month": [],
                "pumps_by_status": [],
                "pumps_by_branch": [],
                "pumps_over_2_days": [],
                "pumps_assembled_weekly": [],
                "pumps_assembled_monthly": [],
                "pumps_assembled_yearly": [],
                "pump_model_distribution": []
            }

            for report_name, tree in frame.report_treeviews.items():
                for item in tree.get_children():
                    values = tree.item(item)["values"]
                    if report_name == "Pumps by Month":
                        report_data["pumps_by_month"].append(f"{values[0]}: {values[1]}")
                    elif report_name == "Pumps by Status":
                        report_data["pumps_by_status"].append(f"{values[0]}: {values[1]}")
                    elif report_name == "Pumps by Branch":
                        report_data["pumps_by_branch"].append(f"{values[0]}: {values[1]}")
                    elif report_name == "Pumps Over 2 Days in Assembly":
                        report_data["pumps_over_2_days"].append(f"{values[0]}: {values[1]}")
                    elif report_name == "Pumps Assembled This Week":
                        report_data["pumps_assembled_weekly"].append(f"{values[0]}: {values[1]}")
                    elif report_name == "Pumps Assembled This Month":
                        report_data["pumps_assembled_monthly"].append(f"{values[0]}: {values[1]}")
                    elif report_name == "Pumps Assembled This Year":
                        report_data["pumps_assembled_yearly"].append(f"{values[0]}: {values[1]}")
                    elif report_name == "Pump Model Distribution":
                        report_data["pump_model_distribution"].append(f"{values[0]}: {values[1]}")

            # Format the data for the PDF
            formatted_data = {
                "Generated At": report_data["generated_at"],
                "Pumps by Month": "\n".join(report_data["pumps_by_month"]),
                "Pumps by Status": "\n".join(report_data["pumps_by_status"]),
                "Pumps by Branch": "\n".join(report_data["pumps_by_branch"]),
                "Pumps Over 2 Days in Assembly": "\n".join(report_data["pumps_over_2_days"]),
                "Pumps Assembled This Week": "\n".join(report_data["pumps_assembled_weekly"]),
                "Pumps Assembled This Month": "\n".join(report_data["pumps_assembled_monthly"]),
                "Pumps Assembled This Year": "\n".join(report_data["pumps_assembled_yearly"]),
                "Pump Model Distribution": "\n".join(report_data["pump_model_distribution"])
            }

            # Generate PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = os.path.join(report_dir, f"summary_report_{timestamp}.pdf")
            try:
                generate_pdf_notification("SummaryReport", formatted_data, title=f"Summary Report - {timestamp}", output_path=pdf_filename)
                logger.info(f"Generated PDF report at {pdf_filename}")
                os.startfile(pdf_filename, "print")
                Messagebox.show_info("PDF Generated", f"PDF report generated at {pdf_filename} and opened for printing.")
            except Exception as e:
                logger.error(f"Failed to generate PDF report: {str(e)}")
                Messagebox.show_error("PDF Generation Failed", f"Error: {str(e)}")

        # Button frame for global actions
        button_frame = ttk.Frame(report_frame)
        button_frame.pack(pady=5)  # Removed fill=X to prevent stretching
        ttk.Button(button_frame, text="Refresh Reports", command=refresh_reports, 
                   bootstyle="info", style="large.TButton", width=15).pack(side=LEFT, padx=5)  # Set fixed width
        ttk.Button(button_frame, text="Generate PDF Report", command=generate_pdf_report, 
                   bootstyle="success", style="large.TButton", width=18).pack(side=LEFT, padx=5)  # Set fixed width

        # Initial population of the reports
        refresh_reports()

def show_activity_log_tab(frame):
    if not hasattr(frame, 'log_tree'):
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        def refresh_activity_log():
            for item in frame.log_tree.get_children():
                frame.log_tree.delete(item)
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT timestamp, username, action FROM audit_log ORDER BY timestamp DESC")
                logs = cursor.fetchall()
                for log in logs:
                    frame.log_tree.insert("", END, values=(log["timestamp"], log["username"], log["action"]))

        def export_to_excel():
            config = load_config()
            export_dir = config["document_dirs"]["excel_exports"]
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
                logger.info(f"Created directory {export_dir} for Excel exports")
            data = []
            for item in frame.log_tree.get_children():
                data.append(frame.log_tree.item(item)["values"])
            df = pd.DataFrame(data, columns=["Timestamp", "Username", "Action"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(export_dir, f"activity_log_export_{timestamp}.xlsx")
            try:
                df.to_excel(filename, index=False)
                logger.info(f"Exported activity log to {filename}")
                Messagebox.show_info("Export Successful", f"Activity log exported to {filename}")
            except Exception as e:
                logger.error(f"Failed to export activity log to Excel: {str(e)}")
                Messagebox.show_error("Export Failed", f"Error: {str(e)}")

        frame.log_tree = ttk.Treeview(log_frame, columns=("Timestamp", "Username", "Action"), show="headings", height=20)
        frame.log_tree.heading("Timestamp", text="Timestamp", anchor=W)
        frame.log_tree.heading("Username", text="Username", anchor=W)
        frame.log_tree.heading("Action", text="Action", anchor=W)
        frame.log_tree.column("Timestamp", width=150, anchor=W)
        frame.log_tree.column("Username", width=150, anchor=W)
        frame.log_tree.column("Action", width=400, anchor=W)
        frame.log_tree.pack(fill=BOTH, expand=True)

        button_frame = ttk.Frame(log_frame)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="Refresh Log", command=refresh_activity_log, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Export to Excel", command=export_to_excel, bootstyle="primary", style="large.TButton").pack(side=LEFT, padx=5)

        refresh_activity_log()

def show_backup_tab(frame):
    backup_frame = ttk.Frame(frame, padding=20)
    backup_frame.pack(fill=BOTH, expand=True)

    ttk.Label(backup_frame, text="Database Backup & Restore", font=("Roboto", 14)).pack(pady=10)

    def backup_db():
        try:
            if os.path.exists(DB_PATH):
                backup_path = f"{DB_PATH}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                shutil.copy2(DB_PATH, backup_path)  # Use copy2 to preserve metadata
                logger.info(f"Database backed up to {backup_path}")
                Messagebox.show_info("Backup Successful", f"Backup saved to {backup_path}")
            else:
                raise FileNotFoundError("Database file not found")
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            Messagebox.show_error("Backup Failed", f"Error: {str(e)}")

    def restore_db():
        try:
            # Open native file explorer dialog
            file_path = filedialog.askopenfilename(
                title="Select Backup File",
                filetypes=[("Backup Files", "*.bak")],
                initialdir=os.path.dirname(DB_PATH)  # Start in the data directory
            )
            if file_path and os.path.exists(file_path):
                if Messagebox.yesno("Confirm Restore", "This will overwrite the current database. Proceed?") == "Yes":
                    shutil.copy2(file_path, DB_PATH)
                    logger.info(f"Database restored from {file_path}")
                    Messagebox.show_info("Restore Successful", f"Database restored from {file_path}")
            else:
                raise FileNotFoundError("No valid backup file selected")
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            Messagebox.show_error("Restore Failed", f"Error: {str(e)}")

    ttk.Button(backup_frame, text="Backup Database", command=backup_db, bootstyle="info", style="large.TButton").pack(pady=5)
    ttk.Button(backup_frame, text="Restore Database", command=restore_db, bootstyle="warning", style="large.TButton").pack(pady=5)

def show_config_tab(frame):
    config_frame = ttk.Frame(frame, padding=20)
    config_frame.pack(fill=BOTH, expand=True)

    # Use grid for all widgets in config_frame
    ttk.Label(config_frame, text="Document Save Locations", font=("Roboto", 14)).grid(row=0, column=0, columnspan=3, pady=10)

    # Load current configuration
    config = load_config()
    doc_dirs = config["document_dirs"]

    # Document types and their labels
    doc_types = [
        ("certificate", "Certificates (PDFs)"),
        ("bom", "BOM Documents"),
        ("confirmation", "Confirmation Documents"),
        ("reports", "Reports"),
        ("excel_exports", "Excel Exports")
    ]

    entries = {}
    for i, (doc_type, label) in enumerate(doc_types, start=1):  # Start at row 1 to leave row 0 for the title
        ttk.Label(config_frame, text=f"{label}:", font=("Roboto", 12)).grid(row=i, column=0, pady=5, sticky=W)
        entry = ttk.Entry(config_frame, font=("Roboto", 12), width=50)
        entry.insert(0, doc_dirs[doc_type])
        entry.grid(row=i, column=1, pady=5, padx=5, sticky=EW)
        entries[doc_type] = entry

        def browse_dir(doc_type=doc_type):
            dir_path = filedialog.askdirectory(title=f"Select Directory for {label}")
            if dir_path:
                entries[doc_type].delete(0, END)
                entries[doc_type].insert(0, dir_path)

        ttk.Button(config_frame, text="Browse", command=browse_dir, bootstyle="secondary").grid(row=i, column=2, padx=5)

    config_frame.grid_columnconfigure(1, weight=1)

    def save_config_changes():
        config = load_config()
        for doc_type, entry in entries.items():
            path = entry.get().strip()
            if not path:
                path = DEFAULT_DIRS[doc_type]
            if not os.path.exists(path):
                os.makedirs(path)
                logger.info(f"Created directory {path} for {doc_type}")
            config["document_dirs"][doc_type] = path
        save_config(config)
        Messagebox.show_info("Success", "Configuration saved successfully")

    ttk.Button(config_frame, text="Save Configuration", command=save_config_changes, bootstyle="success", style="large.TButton").grid(row=len(doc_types) + 1, column=0, columnspan=3, pady=10)

def show_email_tab(frame):
    email_frame = ttk.Frame(frame, padding=20)
    email_frame.pack(fill=BOTH, expand=True)

    # Title
    ttk.Label(email_frame, text="Email Configuration (Gmail)", font=("Roboto", 14)).grid(row=0, column=0, columnspan=2, pady=10)

    # Note about Gmail App Password
    note = (
        "Note: This application uses Gmail for sending emails. To authenticate:\n"
        "1. Enable 2-Step Verification on your Gmail account.\n"
        "2. Generate an App Password in your Google Account settings (Security > App Passwords).\n"
        "3. Use your Gmail address as the SMTP Username and Sender Email, and the App Password as the SMTP Password."
    )
    ttk.Label(email_frame, text=note, font=("Roboto", 12), wraplength=600, justify=LEFT, bootstyle="info").grid(row=1, column=0, columnspan=2, pady=10)

    # Load current email settings
    config = load_config()
    email_settings = config["email_settings"]

    # Email settings fields
    fields = [
        ("smtp_host", "SMTP Host"),
        ("smtp_port", "SMTP Port"),
        ("smtp_username", "SMTP Username"),
        ("smtp_password", "SMTP Password"),
        ("sender_email", "Sender Email")
    ]
    entries = {}
    for i, (key, label) in enumerate(fields, start=2):  # Start at row 2 to leave space for title and note
        ttk.Label(email_frame, text=f"{label}:", font=("Roboto", 12)).grid(row=i, column=0, pady=5, sticky=W)
        if key == "smtp_password":
            entry = ttk.Entry(email_frame, font=("Roboto", 12), show="*")  # Mask password
        else:
            entry = ttk.Entry(email_frame, font=("Roboto", 12))
        entry.insert(0, email_settings.get(key, ""))
        entry.grid(row=i, column=1, pady=5, padx=5, sticky=EW)
        entries[key] = entry

    # SSL/TLS Toggle
    use_tls_var = ttk.BooleanVar(value=email_settings.get("use_tls", True))
    ttk.Checkbutton(email_frame, text="Use TLS", variable=use_tls_var, bootstyle="success").grid(row=len(fields) + 2, column=0, columnspan=2, pady=5)

    # Test email recipient field
    ttk.Label(email_frame, text="Test Email Recipient:", font=("Roboto", 12)).grid(row=len(fields) + 3, column=0, pady=5, sticky=W)
    test_recipient_entry = ttk.Entry(email_frame, font=("Roboto", 12))
    test_recipient_entry.grid(row=len(fields) + 3, column=1, pady=5, padx=5, sticky=EW)

    email_frame.grid_columnconfigure(1, weight=1)

    # Error/Success message label
    message_label = ttk.Label(email_frame, text="", font=("Roboto", 12), bootstyle="danger")
    message_label.grid(row=len(fields) + 4, column=0, columnspan=2, pady=5)

    def save_email_settings():
        config = load_config()
        for key, entry in entries.items():
            config["email_settings"][key] = entry.get().strip()
        config["email_settings"]["use_tls"] = use_tls_var.get()
        save_config(config)
        message_label.config(text="Email settings saved successfully", bootstyle="success")
        logger.info("Email settings saved")

    def test_email():
        recipient = test_recipient_entry.get().strip()
        if not recipient:
            message_label.config(text="Please enter a recipient email address", bootstyle="danger")
            return

        # Load the current settings from the entries
        smtp_host = entries["smtp_host"].get().strip()
        smtp_port = entries["smtp_port"].get().strip()
        smtp_username = entries["smtp_username"].get().strip()
        smtp_password = entries["smtp_password"].get().strip()
        sender_email = entries["sender_email"].get().strip()
        use_tls = use_tls_var.get()

        # Validate required fields
        if not all([smtp_host, smtp_port, sender_email]):
            message_label.config(text="SMTP Host, Port, and Sender Email are required", bootstyle="danger")
            return

        # Create the test email
        msg = MIMEText("This is a test email from Guth Pump Registry.")
        msg["Subject"] = "Test Email - Guth Pump Registry"
        msg["From"] = sender_email
        msg["To"] = recipient

        try:
            # Connect to the SMTP server
            server = smtplib.SMTP(smtp_host, int(smtp_port))
            if use_tls:
                server.starttls()
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, recipient, msg.as_string())
            server.quit()
            message_label.config(text="Test email sent successfully", bootstyle="success")
            logger.info(f"Test email sent to {recipient}")
        except Exception as e:
            message_label.config(text=f"Failed to send test email: {str(e)}", bootstyle="danger")
            logger.error(f"Failed to send test email to {recipient}: {str(e)}")

    # Buttons
    button_frame = ttk.Frame(email_frame)
    button_frame.grid(row=len(fields) + 5, column=0, columnspan=2, pady=10)
    ttk.Button(button_frame, text="Save Email Settings", command=save_email_settings, bootstyle="success", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Button(button_frame, text="Test Email", command=test_email, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=5)

def edit_user_window(parent_frame, username):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        logger.debug(f"User data: {dict(user)}")
        cursor.execute("SELECT DISTINCT role FROM users")
        roles = [row["role"] for row in cursor.fetchall()] or ["Admin", "Stores", "Testing", "Pump Originator", "Approval"]

    edit_window = ttk.Toplevel(parent_frame)
    edit_window.title(f"Edit User {username}")
    edit_window.geometry("520x500")

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
            logger.error(f"Edit user logo load failed: {str(e)}")
    ttk.Label(header_frame, text="Edit user details.", font=("Roboto", 12)).pack(anchor=W, padx=10)

    frame = ttk.Frame(edit_window, padding=20)
    frame.pack(fill=BOTH, expand=True)

    fields = ["username", "password", "role", "name", "surname", "email"]
    entries = {}
    for i, field in enumerate(fields):
        ttk.Label(frame, text=f"{field.replace('_', ' ').title()}:", font=("Roboto", 14)).grid(row=i, column=0, pady=5, sticky=W)
        if field == "role":
            entry = ttk.Combobox(frame, values=roles, font=("Roboto", 12), state="readonly")
            # If the user's role is "Assembler", change it to "Testing"
            user_role = user["role"]
            if user_role == "Assembler":
                user_role = "Testing"
            entry.set(user_role)
        else:
            entry = ttk.Entry(frame, font=("Roboto", 12))
            if field != "password":
                entry.insert(0, user[field])
        entry.grid(row=i, column=1, pady=5, sticky=EW)
        entries[field] = entry

    frame.grid_columnconfigure(1, weight=1)

    def save_changes():
        with connect_db() as conn:
            cursor = conn.cursor()
            password = entries["password"].get()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()) if password else user["password_hash"]
            cursor.execute("UPDATE users SET password_hash = ?, role = ?, name = ?, surname = ?, email = ? WHERE username = ?",
                          (password_hash, entries["role"].get(), entries["name"].get(),
                           entries["surname"].get(), entries["email"].get(), username))
            conn.commit()
            logger.info(f"Updated user {username}")
            selected_item = parent_frame.user_tree.selection()
            if selected_item:
                parent_frame.user_tree.item(selected_item[0], values=(entries["username"].get(), entries["role"].get()))
            edit_window.destroy()

    ttk.Button(frame, text="Save", command=save_changes, bootstyle="success", style="large.TButton").grid(row=len(fields), column=0, columnspan=2, pady=10)