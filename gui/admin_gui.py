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

logger = get_logger("admin_gui")
LOGO_PATH = r"C:\Users\travism\source\repos\GuthPumpRegistry\assets\logo.png"
BUILD_NUMBER = "1.0.0"

def show_admin_gui(root, username, logout_callback):
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

    # Custom tab style
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

    ttk.Button(main_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=10)
    ttk.Label(main_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(main_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

def show_pumps_tab(frame):
    if not hasattr(frame, 'tree'):
        frame.tree = ttk.Treeview(frame, columns=("Serial Number", "Pump Model", "Configuration", "Status", "Customer", "Created At"), show="headings", height=15)
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
            roles = [row["role"] for row in cursor.fetchall()] or ["Admin", "Stores", "Assembler", "Testing", "Pump Originator", "Approval"]

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
            pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
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
            data = []
            for item in frame.user_tree.get_children():
                data.append(frame.user_tree.item(item)["values"])
            df = pd.DataFrame(data, columns=["Username", "Role"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"users_export_{timestamp}.xlsx"
            df.to_excel(filename, index=False)
            logger.info(f"Exported users to {filename}")
            Messagebox.show_info("Export Successful", f"Users exported to {filename}")

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

        frame.user_tree = ttk.Treeview(user_list_frame, columns=("Username", "Role"), show="headings", height=10)
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

        # Treeview for reports
        frame.report_tree = ttk.Treeview(report_frame, columns=("Report", "Detail", "Count"), show="headings", height=10)
        frame.report_tree.heading("Report", text="Report", anchor=W)
        frame.report_tree.heading("Detail", text="Detail", anchor=W)
        frame.report_tree.heading("Count", text="Count", anchor=W)
        frame.report_tree.column("Report", width=200, anchor=W)
        frame.report_tree.column("Detail", width=200, anchor=W)
        frame.report_tree.column("Count", width=100, anchor=W)
        frame.report_tree.pack(fill=BOTH, expand=True, pady=5)

        # Define refresh_reports before the button
        def refresh_reports():
            for item in frame.report_tree.get_children():
                frame.report_tree.delete(item)
            today = datetime.now()

            # Report 1: Pumps Created by Month (Last 6 Months)
            six_months_ago = today - timedelta(days=180)
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
                    FROM pumps
                    WHERE created_at >= ?
                    GROUP BY month
                    ORDER BY month DESC
                """, (six_months_ago,))
                monthly_counts = cursor.fetchall()
                for month_data in monthly_counts:
                    frame.report_tree.insert("", END, values=("Pumps by Month", month_data["month"], month_data["count"]))

            # Report 2: Pumps by Status
            cursor.execute("SELECT status, COUNT(*) as count FROM pumps GROUP BY status")
            status_counts = cursor.fetchall()
            for status_data in status_counts:
                frame.report_tree.insert("", END, values=("Pumps by Status", status_data["status"], status_data["count"]))

            # Report 3: Pumps by Branch
            cursor.execute("SELECT branch, COUNT(*) as count FROM pumps GROUP BY branch")
            branch_counts = cursor.fetchall()
            for branch_data in branch_counts:
                frame.report_tree.insert("", END, values=("Pumps by Branch", branch_data["branch"], branch_data["count"]))

        # Refresh button
        ttk.Button(report_frame, text="Refresh Reports", command=refresh_reports, bootstyle="info", style="large.TButton").pack(pady=5)

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
            data = []
            for item in frame.log_tree.get_children():
                data.append(frame.log_tree.item(item)["values"])
            df = pd.DataFrame(data, columns=["Timestamp", "Username", "Action"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"activity_log_export_{timestamp}.xlsx"
            df.to_excel(filename, index=False)
            logger.info(f"Exported activity log to {filename}")
            Messagebox.show_info("Export Successful", f"Activity log exported to {filename}")

        frame.log_tree = ttk.Treeview(log_frame, columns=("Timestamp", "Username", "Action"), show="headings", height=15)
        frame.log_tree.heading("Timestamp", text="Timestamp", anchor=W)
        frame.log_tree.heading("Username", text="Username", anchor=W)
        frame.log_tree.heading("Action", text="Action", anchor=W)
        frame.log_tree.column("Timestamp", width=150, anchor=W)
        frame.log_tree.column("Username", width=150, anchor=W)
        frame.log_tree.column("Action", width=200, anchor=W)
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

def edit_user_window(parent_frame, username):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        logger.debug(f"User data: {dict(user)}")
        cursor.execute("SELECT DISTINCT role FROM users")
        roles = [row["role"] for row in cursor.fetchall()] or ["Admin", "Stores", "Assembler", "Testing", "Pump Originator", "Approval"]

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
            entry.set(user["role"])
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