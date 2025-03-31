import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageTk
import pyodbc
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
from database import get_db_connection

logger = get_logger("admin_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
BUILD_NUMBER = "1.0.0"

# Default directories
DEFAULT_DIRS = {
    "certificate": os.path.join(BASE_DIR, "certificates"),
    "bom": os.path.join(BASE_DIR, "boms"),
    "confirmation": os.path.join(BASE_DIR, "confirmations"),
    "reports": os.path.join(BASE_DIR, "reports"),
    "excel_exports": os.path.join(BASE_DIR, "exports")
}

# Default email settings (Gmail)
DEFAULT_EMAIL_SETTINGS = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": "587",
    "smtp_username": "",
    "smtp_password": "",
    "sender_email": "",
    "use_tls": True
}

def load_config():
    """Load configuration from config.json, creating it with defaults if missing."""
    if not os.path.exists(CONFIG_PATH):
        config = {"document_dirs": DEFAULT_DIRS, "email_settings": DEFAULT_EMAIL_SETTINGS}
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        logger.info(f"Created default config file at {CONFIG_PATH}")
        return config
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    config.setdefault("document_dirs", DEFAULT_DIRS)
    config.setdefault("email_settings", DEFAULT_EMAIL_SETTINGS)
    for key, default in DEFAULT_DIRS.items():
        config["document_dirs"].setdefault(key, default)
    for key, default in DEFAULT_EMAIL_SETTINGS.items():
        config["email_settings"].setdefault(key, default)
    return config

def save_config(config):
    """Save configuration to config.json."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
    logger.info(f"Saved config to {CONFIG_PATH}")

def show_admin_gui(root, username, logout_callback):
    """Display the admin GUI with tabbed interface."""
    root.geometry("1200x800")
    root.minsize(1000, 600)

    for widget in root.winfo_children():
        widget.destroy()

    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    header_frame = ttk.Frame(main_frame, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20), ipady=20)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.75), int(Image.open(LOGO_PATH).height * 0.75)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
        except Exception as e:
            logger.error(f"Admin logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username} (Admin)", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Manage pumps, users, and backups.", font=("Roboto", 12)).pack(anchor=W, padx=10)

    style = ttk.Style()
    style.configure("Custom.TNotebook", tabposition="nw")
    style.configure("Custom.TNotebook.Tab", background="#2c3e50", foreground="white", font=("Roboto", 12), padding=[12, 6])
    style.map("Custom.TNotebook.Tab", background=[("selected", "#ECECEC"), ("!selected", "#2c3e50")], foreground=[("selected", "black"), ("!selected", "white")])

    notebook = ttk.Notebook(main_frame, style="Custom.TNotebook")
    notebook.pack(fill=BOTH, expand=True, pady=10)

    for tab, func in [
        ("Pumps", show_pumps_tab),
        ("Users", show_user_tab),
        ("Reports", show_reports_tab),
        ("Activity Log", show_activity_log_tab),
        ("Backup", show_backup_tab),
        ("Configuration", show_config_tab),
        ("Email", show_email_tab)
    ]:
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text=tab)
        func(tab_frame)

    ttk.Button(main_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=10)
    ttk.Label(main_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(main_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

def show_pumps_tab(frame):
    """Display and manage pump records."""
    if not hasattr(frame, 'tree'):
        frame.tree = ttk.Treeview(frame, columns=("Serial Number", "Pump Model", "Configuration", "Status", "Customer", "Created At"), show="headings", height=20)
        for col in frame.tree["columns"]:
            frame.tree.heading(col, text=col, anchor=W)
            frame.tree.column(col, width=150 if col != "Created At" else 120, anchor=W)
        frame.tree.pack(fill=BOTH, expand=True, padx=10, pady=10)
        frame.tree.bind("<Double-1>", lambda event: edit_pump_window(frame, frame.tree))

        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="Export to Excel", command=lambda: export_to_excel(frame.tree), bootstyle="primary", style="large.TButton").pack(side=LEFT, padx=5)

    def export_to_excel(tree):
        config = load_config()
        export_dir = config["document_dirs"]["excel_exports"]
        os.makedirs(export_dir, exist_ok=True)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT serial_number, pump_model, configuration, status, customer, requested_by, branch, impeller_size, connection_type, pressure_required, flow_rate_required, custom_motor, flush_seal_housing, created_at FROM pumps")
            data = [tuple(row) for row in cursor.fetchall()]
        df = pd.DataFrame(data, columns=["Serial Number", "Pump Model", "Configuration", "Status", "Customer", "Requested By", "Branch", "Impeller Size", "Connection Type", "Pressure Required", "Flow Rate Required", "Custom Motor", "Flush Seal Housing", "Created At"])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(export_dir, f"pumps_export_{timestamp}.xlsx")
        try:
            df.to_excel(filename, index=False)
            logger.info(f"Exported pumps to {filename}")
            Messagebox.show_info("Export Successful", f"Pumps exported to {filename}")
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            Messagebox.show_error("Export Failed", f"Error: {str(e)}")

    frame.tree.delete(*frame.tree.get_children())
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT serial_number, pump_model, configuration, status, customer, created_at FROM pumps")
        for pump in cursor.fetchall():
            # pump is a tuple: (serial_number, pump_model, configuration, status, customer, created_at)
            frame.tree.insert("", END, values=(pump[0], pump[1], pump[2], pump[3], pump[4], pump[5]))

def edit_pump_window(parent_frame, tree):
    """Edit or delete a pump record."""
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected")
        return

    serial_number = tree.item(selected[0])["values"][0]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pumps WHERE serial_number = ?", (serial_number,))
        # Convert tuple to dict using column names
        columns = [desc[0] for desc in cursor.description]
        pump = dict(zip(columns, cursor.fetchone() or tuple([serial_number] + [None] * (len(columns) - 1))))

    edit_window = ttk.Toplevel(parent_frame)
    edit_window.title(f"Edit Pump {serial_number}")
    edit_window.geometry("520x500")

    header_frame = ttk.Frame(edit_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.5), int(Image.open(LOGO_PATH).height * 0.5)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
        except Exception as e:
            logger.error(f"Edit pump logo load failed: {str(e)}")
    ttk.Label(header_frame, text="Edit pump details or delete.", font=("Roboto", 12)).pack(anchor=W, padx=10)

    frame = ttk.Frame(edit_window, padding=20)
    frame.pack(fill=BOTH, expand=True)

    fields = ["serial_number", "pump_model", "configuration", "customer", "requested_by", "branch", "impeller_size", "connection_type", "pressure_required", "flow_rate_required", "custom_motor", "flush_seal_housing", "created_at"]
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
            entry = ttk.Entry(frame, font=("Roboto", 12), state="readonly")
            entry.insert(0, pump.get(field, ""))
        elif field in options:
            entry = ttk.Combobox(frame, values=options[field], font=("Roboto", 12), state="readonly")
            entry.set(pump.get(field, options[field][0]))
        else:
            entry = ttk.Entry(frame, font=("Roboto", 12))
            entry.insert(0, pump.get(field, ""))
        entry.grid(row=i, column=1, pady=5, sticky=EW)
        entries[field] = entry

    frame.grid_columnconfigure(1, weight=1)

    def save_changes():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pumps 
                SET pump_model = ?, configuration = ?, customer = ?, requested_by = ?, 
                    branch = ?, impeller_size = ?, connection_type = ?, pressure_required = ?, 
                    flow_rate_required = ?, custom_motor = ?, flush_seal_housing = ?
                WHERE serial_number = ?
            """, (entries["pump_model"].get(), entries["configuration"].get(), entries["customer"].get(),
                  entries["requested_by"].get(), entries["branch"].get(), entries["impeller_size"].get(),
                  entries["connection_type"].get(), float(entries["pressure_required"].get() or 0),
                  float(entries["flow_rate_required"].get() or 0), entries["custom_motor"].get(),
                  entries["flush_seal_housing"].get(), serial_number))
            conn.commit()
            logger.info(f"Updated pump {serial_number}")
            show_pumps_tab(parent_frame)
            edit_window.destroy()

    def delete_pump():
        if Messagebox.yesno("Confirm Delete", f"Are you sure you want to delete pump {serial_number}?") == "Yes":
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM pumps WHERE serial_number = ?", (serial_number,))
                conn.commit()
                logger.info(f"Deleted pump {serial_number}")
                show_pumps_tab(parent_frame)
                edit_window.destroy()

    ttk.Button(frame, text="Save", command=save_changes, bootstyle="success", style="large.TButton").grid(row=len(fields), column=0, pady=10)
    ttk.Button(frame, text="Delete", command=delete_pump, bootstyle="danger", style="large.TButton").grid(row=len(fields), column=1, pady=10)

def show_user_tab(frame):
    """Manage user records."""
    if not hasattr(frame, 'input_frame'):
        input_frame = ttk.LabelFrame(frame, text="Add/Edit User", padding=20, bootstyle="default")
        input_frame.pack(fill=X, padx=10, pady=10)
        frame.input_frame = input_frame

        # Updated roles to include "Assembler_Tester"
        roles = ["Admin", "Stores", "Assembler_Tester", "Pump Originator", "Approval"]

        fields = ["Username", "Password", "Role", "Name", "Surname", "Email"]
        frame.entries = {}
        for i, field in enumerate(fields):
            ttk.Label(input_frame, text=f"{field}:", font=("Roboto", 14)).grid(row=i, column=0, pady=5, sticky=W)
            entry = ttk.Combobox(input_frame, values=roles, font=("Roboto", 12), state="readonly") if field == "Role" else ttk.Entry(input_frame, font=("Roboto", 12), width=30)
            if field == "Role":
                entry.set("Pump Originator")
            entry.grid(row=i, column=1, pady=5, padx=5, sticky=EW)
            frame.entries[field.lower()] = entry

        input_frame.grid_columnconfigure(1, weight=1)
        frame.error_label = ttk.Label(input_frame, text="", font=("Roboto", 12), bootstyle="danger")
        frame.error_label.grid(row=len(fields), column=0, columnspan=2, pady=5)

        def validate_email(email):
            return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) is not None

        def add_user():
            email = frame.entries["email"].get()
            username = frame.entries["username"].get()
            password = frame.entries["password"].get()
            role = frame.entries["role"].get()
            name = frame.entries["name"].get()
            surname = frame.entries["surname"].get()
            if not all([username, password, role]):
                frame.error_label.config(text="Username, Password, and Role are required", bootstyle="danger")
                logger.debug("Missing required fields: username, password, or role")
                return
            if not validate_email(email):
                frame.error_label.config(text="Invalid email address", bootstyle="danger")
                logger.debug(f"Invalid email: {email}")
                return
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Check existing users for debugging
                cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
                existing_user = cursor.fetchone()
                if existing_user:
                    frame.error_label.config(text=f"User {username} already exists", bootstyle="danger")
                    logger.warning(f"Duplicate username detected: {username}")
                    return
                try:
                    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, role, name, surname, email)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (username, password_hash, role, name, surname, email))
                    conn.commit()
                    logger.info(f"Successfully added user {username} with role {role}")
                    # Clear all fields after successful add
                    for field, entry in frame.entries.items():
                        entry.delete(0, END)
                    frame.entries["role"].set("Pump Originator")  # Reset role to default
                    frame.error_label.config(text="User added successfully!", bootstyle="success")
                    refresh_user_list()
                except pyodbc.IntegrityError as ie:
                    frame.error_label.config(text=f"User {username} already exists (IntegrityError)", bootstyle="danger")
                    logger.error(f"IntegrityError adding user {username} with role {role}: {str(ie)}")
                except Exception as e:
                    frame.error_label.config(text=f"Failed to add user: {str(e)}", bootstyle="danger")
                    logger.error(f"Unexpected error adding user {username} with role {role}: {str(e)}")

        def edit_user():
            selected = frame.user_tree.selection()
            if selected:
                edit_user_window(frame, frame.user_tree.item(selected[0])["values"][0])

        def delete_user():
            selected = frame.user_tree.selection()
            if selected and Messagebox.yesno("Confirm Delete", f"Are you sure you want to delete user {frame.user_tree.item(selected[0])['values'][0]}?") == "Yes":
                username = frame.user_tree.item(selected[0])["values"][0]
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                    conn.commit()
                    logger.info(f"Deleted user {username}")
                    refresh_user_list()

        def export_to_excel():
            config = load_config()
            export_dir = config["document_dirs"]["excel_exports"]
            os.makedirs(export_dir, exist_ok=True)
            data = [frame.user_tree.item(item)["values"] for item in frame.user_tree.get_children()]
            df = pd.DataFrame(data, columns=["Username", "Role"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(export_dir, f"users_export_{timestamp}.xlsx")
            try:
                df.to_excel(filename, index=False)
                logger.info(f"Exported users to {filename}")
                Messagebox.show_info("Export Successful", f"Users exported to {filename}")
            except Exception as e:
                logger.error(f"Export failed: {str(e)}")
                Messagebox.show_error("Export Failed", f"Error: {str(e)}")

        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=len(fields) + 1, column=0, columnspan=2, sticky=W, pady=10)
        for text, cmd, style in [("Add User", add_user, "success"), ("Edit User", edit_user, "info"), ("Delete User", delete_user, "danger"), ("Export to Excel", export_to_excel, "primary")]:
            ttk.Button(button_frame, text=text, command=cmd, bootstyle=style, style="large.TButton").pack(side=LEFT, padx=(0, 5))

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
            frame.user_tree.delete(*frame.user_tree.get_children())
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT username, role FROM users")
                for user in cursor.fetchall():
                    # user is a tuple: (username, role)
                    frame.user_tree.insert("", END, values=(user[0], user[1]))

        def on_right_click(event):
            item = frame.user_tree.identify_row(event.y)
            if item:
                frame.user_tree.selection_set(item)
                menu = ttk.Menu(frame, tearoff=0)
                menu.add_command(label="Edit", command=lambda: edit_user_window(frame, frame.user_tree.item(item)["values"][0]))
                menu.add_command(label="Delete", command=delete_user)
                menu.post(event.x_root, event.y_root)

        frame.user_tree.bind("<Button-3>", on_right_click)
        refresh_user_list()

def show_reports_tab(frame):
    """Display various pump reports."""
    if not hasattr(frame, 'report_frame'):
        report_frame = ttk.Frame(frame)
        report_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        ttk.Label(report_frame, text="Reports", font=("Roboto", 16, "bold")).pack(pady=(0, 10))

        notebook_frame = ttk.Frame(report_frame)
        notebook_frame.pack(fill=BOTH, expand=True)
        canvas = ttk.Canvas(notebook_frame)
        scrollbar = ttk.Scrollbar(notebook_frame, orient=HORIZONTAL, command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)
        canvas.configure(xscrollcommand=scrollbar.set)
        scrollbar.pack(side=BOTTOM, fill=X)
        canvas.pack(side=TOP, fill=BOTH, expand=True)
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        style = ttk.Style()
        style.configure("Report.TNotebook", tabposition="wn")
        style.configure("Report.TNotebook.Tab", background="#2c3e50", foreground="white", font=("Roboto", 10), padding=[10, 5], width=150)
        style.map("Report.TNotebook.Tab", background=[("selected", "#ECECEC"), ("!selected", "#2c3e50")], foreground=[("selected", "black"), ("!selected", "white")])

        report_notebook = ttk.Notebook(scrollable_frame, style="Report.TNotebook")
        report_notebook.pack(fill=BOTH, expand=True, pady=5)

        frame.report_treeviews = {}
        frame.report_data = {}
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

        for report_name, columns in reports:
            tab_frame = ttk.Frame(report_notebook)
            report_notebook.add(tab_frame, text=report_name)
            tree = ttk.Treeview(tab_frame, columns=columns, show="headings", height=30)
            for col in columns:
                tree.heading(col, text=col, anchor=W)
                tree.column(col, width=900 if col == "Detail" else 300, anchor=W)
            tree.pack(fill=BOTH, expand=True, padx=5, pady=5)
            yscroll = ttk.Scrollbar(tab_frame, orient=VERTICAL, command=tree.yview)
            xscroll = ttk.Scrollbar(tab_frame, orient=HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
            yscroll.pack(side=RIGHT, fill=Y)
            xscroll.pack(side=BOTTOM, fill=X)
            frame.report_treeviews[report_name] = tree
            frame.report_data[report_name] = []

            def create_export_function(name, cols):
                def export_report():
                    config = load_config()
                    export_dir = config["document_dirs"]["excel_exports"]
                    os.makedirs(export_dir, exist_ok=True)
                    df = pd.DataFrame(frame.report_data[name], columns=["Report", *cols])
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join(export_dir, f"{name.lower().replace(' ', '_')}_export_{timestamp}.xlsx")
                    try:
                        df.to_excel(filename, index=False)
                        logger.info(f"Exported {name} report to {filename}")
                        Messagebox.show_info("Export Successful", f"{name} report exported to {filename}")
                    except Exception as e:
                        logger.error(f"Export failed: {str(e)}")
                        Messagebox.show_error("Export Failed", f"Error: {str(e)}")
                return export_report

            button_frame = ttk.Frame(tab_frame)
            button_frame.pack(pady=5)
            ttk.Button(button_frame, text="Export to Excel", command=create_export_function(report_name, columns), bootstyle="primary", style="large.TButton", width=15).pack(side=LEFT, padx=5)

        def refresh_reports():
            today = datetime.now()
            for report_name, tree in frame.report_treeviews.items():
                tree.delete(*tree.get_children())
                frame.report_data[report_name] = []

            with get_db_connection() as conn:
                cursor = conn.cursor()
                six_months_ago = today - timedelta(days=180)
                cursor.execute("SELECT FORMAT(created_at, 'yyyy-MM') as month, COUNT(*) as count FROM pumps WHERE created_at >= ? GROUP BY FORMAT(created_at, 'yyyy-MM') ORDER BY month DESC", (six_months_ago,))
                for row in cursor.fetchall():
                    frame.report_data["Pumps by Month"].append(("Pumps by Month", row[0], row[1]))
                    frame.report_treeviews["Pumps by Month"].insert("", END, values=(row[0], row[1]))

                cursor.execute("SELECT status, COUNT(*) as count FROM pumps GROUP BY status")
                for row in cursor.fetchall():
                    frame.report_data["Pumps by Status"].append(("Pumps by Status", row[0], row[1]))
                    frame.report_treeviews["Pumps by Status"].insert("", END, values=(row[0], row[1]))

                cursor.execute("SELECT branch, COUNT(*) as count FROM pumps GROUP BY branch")
                for row in cursor.fetchall():
                    frame.report_data["Pumps by Branch"].append(("Pumps by Branch", row[0], row[1]))
                    frame.report_treeviews["Pumps by Branch"].insert("", END, values=(row[0], row[1]))

                two_days_ago = today - timedelta(days=2)
                cursor.execute("""
                    SELECT p.serial_number, p.customer, p.branch, p.pump_model, p.configuration,
                           DATEDIFF(day, a.timestamp, GETDATE()) as days_in_assembly
                    FROM pumps p
                    JOIN audit_log a ON p.serial_number = SUBSTRING(a.action, 6, CHARINDEX(' moved to', a.action) - 6)
                    WHERE p.status = 'Assembler' AND a.action LIKE 'Pump % moved to Assembler by %' AND a.timestamp <= ?
                """, (two_days_ago,))
                for row in cursor.fetchall():
                    detail = f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}"
                    frame.report_data["Pumps Over 2 Days in Assembly"].append(("Pumps Over 2 Days in Assembly", detail, row[5]))
                    frame.report_treeviews["Pumps Over 2 Days in Assembly"].insert("", END, values=(detail, f"{row[5]} days"))

                week_start = today - timedelta(days=today.weekday())
                cursor.execute("""
                    SELECT p.serial_number, p.customer, p.branch, p.pump_model, p.configuration, a.timestamp
                    FROM pumps p
                    JOIN audit_log a ON p.serial_number = SUBSTRING(a.action, 6, CHARINDEX(' moved to', a.action) - 6)
                    WHERE a.action LIKE 'Pump % moved to Testing by %' AND a.timestamp >= ?
                """, (week_start,))
                for row in cursor.fetchall():
                    detail = f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}"
                    frame.report_data["Pumps Assembled This Week"].append(("Pumps Assembled This Week", detail, row[5]))
                    frame.report_treeviews["Pumps Assembled This Week"].insert("", END, values=(detail, row[5]))

                month_start = today.replace(day=1)
                cursor.execute("""
                    SELECT p.serial_number, p.customer, p.branch, p.pump_model, p.configuration, a.timestamp
                    FROM pumps p
                    JOIN audit_log a ON p.serial_number = SUBSTRING(a.action, 6, CHARINDEX(' moved to', a.action) - 6)
                    WHERE a.action LIKE 'Pump % moved to Testing by %' AND a.timestamp >= ?
                """, (month_start,))
                for row in cursor.fetchall():
                    detail = f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}"
                    frame.report_data["Pumps Assembled This Month"].append(("Pumps Assembled This Month", detail, row[5]))
                    frame.report_treeviews["Pumps Assembled This Month"].insert("", END, values=(detail, row[5]))

                year_start = today.replace(month=1, day=1)
                cursor.execute("""
                    SELECT p.serial_number, p.customer, p.branch, p.pump_model, p.configuration, a.timestamp
                    FROM pumps p
                    JOIN audit_log a ON p.serial_number = SUBSTRING(a.action, 6, CHARINDEX(' moved to', a.action) - 6)
                    WHERE a.action LIKE 'Pump % moved to Testing by %' AND a.timestamp >= ?
                """, (year_start,))
                for row in cursor.fetchall():
                    detail = f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}"
                    frame.report_data["Pumps Assembled This Year"].append(("Pumps Assembled This Year", detail, row[5]))
                    frame.report_treeviews["Pumps Assembled This Year"].insert("", END, values=(detail, row[5]))

                cursor.execute("SELECT pump_model, COUNT(*) as count FROM pumps GROUP BY pump_model")
                model_counts = cursor.fetchall()
                total_pumps = sum(row[1] for row in model_counts)
                for row in model_counts:
                    percentage = (row[1] / total_pumps * 100) if total_pumps > 0 else 0
                    detail = f"{row[0]}: {row[1]} pumps"
                    frame.report_data["Pump Model Distribution"].append(("Pump Model Distribution", detail, f"{percentage:.2f}%"))
                    frame.report_treeviews["Pump Model Distribution"].insert("", END, values=(detail, f"{percentage:.2f}%"))

        def generate_pdf_report():
            config = load_config()
            report_dir = config["document_dirs"]["reports"]
            os.makedirs(report_dir, exist_ok=True)
            report_data = {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                **{name.lower().replace(" ", "_"): "\n".join(f"{tree.item(item)['values'][0]}: {tree.item(item)['values'][1]}" for item in tree.get_children()) for name, tree in frame.report_treeviews.items()}
            }
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = os.path.join(report_dir, f"summary_report_{timestamp}.pdf")
            try:
                generate_pdf_notification("SummaryReport", report_data, title=f"Summary Report - {timestamp}", output_path=pdf_filename)
                logger.info(f"Generated PDF report at {pdf_filename}")
                os.startfile(pdf_filename, "print")
                Messagebox.show_info("PDF Generated", f"PDF report generated at {pdf_filename}")
            except Exception as e:
                logger.error(f"PDF generation failed: {str(e)}")
                Messagebox.show_error("PDF Generation Failed", f"Error: {str(e)}")

        button_frame = ttk.Frame(report_frame)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="Refresh Reports", command=refresh_reports, bootstyle="info", style="large.TButton", width=15).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Generate PDF Report", command=generate_pdf_report, bootstyle="success", style="large.TButton", width=18).pack(side=LEFT, padx=5)

        refresh_reports()

def show_activity_log_tab(frame):
    """Display and export activity log."""
    if not hasattr(frame, 'log_tree'):
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        frame.log_tree = ttk.Treeview(log_frame, columns=("Timestamp", "Username", "Action"), show="headings", height=20)
        frame.log_tree.heading("Timestamp", text="Timestamp", anchor=W)
        frame.log_tree.heading("Username", text="Username", anchor=W)
        frame.log_tree.heading("Action", text="Action", anchor=W)
        frame.log_tree.column("Timestamp", width=150, anchor=W)
        frame.log_tree.column("Username", width=150, anchor=W)
        frame.log_tree.column("Action", width=400, anchor=W)
        frame.log_tree.pack(fill=BOTH, expand=True)

        def refresh_activity_log():
            frame.log_tree.delete(*frame.log_tree.get_children())
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT timestamp, username, action FROM audit_log ORDER BY timestamp DESC")
                for log in cursor.fetchall():
                    # log is a tuple: (timestamp, username, action)
                    frame.log_tree.insert("", END, values=(log[0], log[1], log[2]))

        def export_to_excel():
            config = load_config()
            export_dir = config["document_dirs"]["excel_exports"]
            os.makedirs(export_dir, exist_ok=True)
            data = [frame.log_tree.item(item)["values"] for item in frame.log_tree.get_children()]
            df = pd.DataFrame(data, columns=["Timestamp", "Username", "Action"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(export_dir, f"activity_log_export_{timestamp}.xlsx")
            try:
                df.to_excel(filename, index=False)
                logger.info(f"Exported activity log to {filename}")
                Messagebox.show_info("Export Successful", f"Activity log exported to {filename}")
            except Exception as e:
                logger.error(f"Export failed: {str(e)}")
                Messagebox.show_error("Export Failed", f"Error: {str(e)}")

        button_frame = ttk.Frame(log_frame)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="Refresh Log", command=refresh_activity_log, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="Export to Excel", command=export_to_excel, bootstyle="primary", style="large.TButton").pack(side=LEFT, padx=5)

        refresh_activity_log()

def show_backup_tab(frame):
    """Handle database backup and restore (placeholder for SQL Server)."""
    backup_frame = ttk.Frame(frame, padding=20)
    backup_frame.pack(fill=BOTH, expand=True)

    ttk.Label(backup_frame, text="Database Backup & Restore", font=("Roboto", 14)).pack(pady=10)

    def backup_db():
        Messagebox.show_warning("Backup Not Implemented", "SQL Server backup requires server-side scripting (e.g., SQL Agent job). Contact your DBA.")

    def restore_db():
        Messagebox.show_warning("Restore Not Implemented", "SQL Server restore requires server-side scripting (e.g., SQL Agent job). Contact your DBA.")

    ttk.Button(backup_frame, text="Backup Database", command=backup_db, bootstyle="info", style="large.TButton").pack(pady=5)
    ttk.Button(backup_frame, text="Restore Database", command=restore_db, bootstyle="warning", style="large.TButton").pack(pady=5)

def show_config_tab(frame):
    """Configure document save locations."""
    config_frame = ttk.Frame(frame, padding=20)
    config_frame.pack(fill=BOTH, expand=True)

    ttk.Label(config_frame, text="Document Save Locations", font=("Roboto", 14)).grid(row=0, column=0, columnspan=3, pady=10)
    config = load_config()
    doc_dirs = config["document_dirs"]
    doc_types = [
        ("certificate", "Certificates (PDFs)"),
        ("bom", "BOM Documents"),
        ("confirmation", "Confirmation Documents"),
        ("reports", "Reports"),
        ("excel_exports", "Excel Exports")
    ]
    entries = {}
    for i, (doc_type, label) in enumerate(doc_types, start=1):
        ttk.Label(config_frame, text=f"{label}:", font=("Roboto", 12)).grid(row=i, column=0, pady=5, sticky=W)
        entry = ttk.Entry(config_frame, font=("Roboto", 12), width=50)
        entry.insert(0, doc_dirs[doc_type])
        entry.grid(row=i, column=1, pady=5, padx=5, sticky=EW)
        entries[doc_type] = entry
        ttk.Button(config_frame, text="Browse", command=lambda dt=doc_type: entries[dt].delete(0, END) or entries[dt].insert(0, filedialog.askdirectory(title=f"Select Directory for {label}")), bootstyle="secondary").grid(row=i, column=2, padx=5)

    config_frame.grid_columnconfigure(1, weight=1)

    def save_config_changes():
        config = load_config()
        for doc_type, entry in entries.items():
            path = entry.get().strip() or DEFAULT_DIRS[doc_type]
            os.makedirs(path, exist_ok=True)
            config["document_dirs"][doc_type] = path
        save_config(config)
        Messagebox.show_info("Success", "Configuration saved successfully")

    ttk.Button(config_frame, text="Save Configuration", command=save_config_changes, bootstyle="success", style="large.TButton").grid(row=len(doc_types) + 1, column=0, columnspan=3, pady=10)

def show_email_tab(frame):
    """Configure and test email settings."""
    email_frame = ttk.Frame(frame, padding=20)
    email_frame.pack(fill=BOTH, expand=True)

    ttk.Label(email_frame, text="Email Configuration (Gmail)", font=("Roboto", 14)).grid(row=0, column=0, columnspan=2, pady=10)
    ttk.Label(email_frame, text="Note: Use Gmail App Password (Google Account > Security > App Passwords) for authentication.", font=("Roboto", 12), wraplength=600, justify=LEFT, bootstyle="info").grid(row=1, column=0, columnspan=2, pady=10)

    config = load_config()
    email_settings = config["email_settings"]
    fields = [
        ("smtp_host", "SMTP Host"),
        ("smtp_port", "SMTP Port"),
        ("smtp_username", "SMTP Username"),
        ("smtp_password", "SMTP Password"),
        ("sender_email", "Sender Email")
    ]
    entries = {}
    for i, (key, label) in enumerate(fields, start=2):
        ttk.Label(email_frame, text=f"{label}:", font=("Roboto", 12)).grid(row=i, column=0, pady=5, sticky=W)
        entry = ttk.Entry(email_frame, font=("Roboto", 12), show="*" if key == "smtp_password" else "")
        entry.insert(0, email_settings.get(key, ""))
        entry.grid(row=i, column=1, pady=5, padx=5, sticky=EW)
        entries[key] = entry

    use_tls_var = ttk.BooleanVar(value=email_settings.get("use_tls", True))
    ttk.Checkbutton(email_frame, text="Use TLS", variable=use_tls_var, bootstyle="success").grid(row=len(fields) + 2, column=0, columnspan=2, pady=5)

    ttk.Label(email_frame, text="Test Email Recipient:", font=("Roboto", 12)).grid(row=len(fields) + 3, column=0, pady=5, sticky=W)
    test_recipient_entry = ttk.Entry(email_frame, font=("Roboto", 12))
    test_recipient_entry.grid(row=len(fields) + 3, column=1, pady=5, padx=5, sticky=EW)

    email_frame.grid_columnconfigure(1, weight=1)
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
        smtp_host = entries["smtp_host"].get().strip()
        smtp_port = entries["smtp_port"].get().strip()
        smtp_username = entries["smtp_username"].get().strip()
        smtp_password = entries["smtp_password"].get().strip()
        sender_email = entries["sender_email"].get().strip()
        use_tls = use_tls_var.get()
        if not all([smtp_host, smtp_port, sender_email]):
            message_label.config(text="SMTP Host, Port, and Sender Email are required", bootstyle="danger")
            return
        msg = MIMEText("This is a test email from Guth Pump Registry.")
        msg["Subject"] = "Test Email - Guth Pump Registry"
        msg["From"] = sender_email
        msg["To"] = recipient
        try:
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
            logger.error(f"Test email failed: {str(e)}")

    button_frame = ttk.Frame(email_frame)
    button_frame.grid(row=len(fields) + 5, column=0, columnspan=2, pady=10)
    ttk.Button(button_frame, text="Save Email Settings", command=save_email_settings, bootstyle="success", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Button(button_frame, text="Test Email", command=test_email, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=5)

def edit_user_window(parent_frame, username):
    """Edit a user record."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        # Convert tuple to dict using column names
        columns = [desc[0] for desc in cursor.description]
        user = dict(zip(columns, cursor.fetchone()))
        # Updated roles to include "Assembler_Tester"
        roles = ["Admin", "Stores", "Assembler_Tester", "Pump Originator", "Approval"]

    edit_window = ttk.Toplevel(parent_frame)
    edit_window.title(f"Edit User {username}")
    edit_window.geometry("520x500")

    header_frame = ttk.Frame(edit_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.5), int(Image.open(LOGO_PATH).height * 0.5)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
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
            entry.set(user["role"])
        else:
            entry = ttk.Entry(frame, font=("Roboto", 12))
            if field != "password":
                entry.insert(0, user[field])
        entry.grid(row=i, column=1, pady=5, sticky=EW)
        entries[field] = entry

    frame.grid_columnconfigure(1, weight=1)

    def save_changes():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            password = entries["password"].get()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()) if password else user["password_hash"]
            cursor.execute("UPDATE users SET password_hash = ?, role = ?, name = ?, surname = ?, email = ? WHERE username = ?",
                           (password_hash, entries["role"].get(), entries["name"].get(), entries["surname"].get(), entries["email"].get(), username))
            conn.commit()
            logger.info(f"Updated user {username}")
            show_user_tab(parent_frame)
            edit_window.destroy()

    ttk.Button(frame, text="Save", command=save_changes, bootstyle="success", style="large.TButton").grid(row=len(fields), column=0, columnspan=2, pady=10)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_admin_gui(root, "admin1", lambda: print("Logout"))
    root.mainloop()