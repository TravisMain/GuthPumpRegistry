import os
import json
import sys
import pyodbc
import tkinter as tk
from tkinter import ttk, messagebox
from database import initialize_database, insert_test_data  # Assuming database.py is updated

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DEFAULT_DIRS = {
    "certificate": os.path.join(BASE_DIR, "docs", "certificates"),
    "bom": os.path.join(BASE_DIR, "docs", "boms"),
    "confirmation": os.path.join(BASE_DIR, "docs", "confirmations"),
    "reports": os.path.join(BASE_DIR, "reports"),
    "excel_exports": os.path.join(BASE_DIR, "exports")
}

def test_connection(conn_str):
    """Test if the connection string works."""
    try:
        with pyodbc.connect(conn_str) as conn:
            print("Connection successful!")
        return True
    except pyodbc.Error as e:
        print(f"Connection failed: {e}")
        return False

def configure_sql_server():
    """GUI to prompt for SQL Server details and configure config.json."""
    root = tk.Tk()
    root.title("Guth Pump Registry Setup")
    root.geometry("400x500")

    ttk.Label(root, text="Configure SQL Server Connection", font=("Helvetica", 14, "bold")).pack(pady=10)

    # Server Name
    ttk.Label(root, text="Server Name (e.g., SERVERNAME or SERVERNAME\\INSTANCE):").pack(pady=5)
    server_entry = ttk.Entry(root, width=40)
    server_entry.pack(pady=5)
    server_entry.insert(0, "SERVERNAME\\SQLEXPRESS")  # Example default

    # Database Name
    ttk.Label(root, text="Database Name:").pack(pady=5)
    db_entry = ttk.Entry(root, width=40)
    db_entry.pack(pady=5)
    db_entry.insert(0, "GuthPumpRegistry")

    # Authentication Mode
    auth_var = tk.StringVar(value="Windows")
    ttk.Label(root, text="Authentication Mode:").pack(pady=5)
    ttk.Radiobutton(root, text="Windows Authentication", variable=auth_var, value="Windows").pack()
    ttk.Radiobutton(root, text="SQL Server Authentication", variable=auth_var, value="SQL").pack()

    # SQL Auth Fields (hidden unless SQL mode selected)
    sql_frame = ttk.Frame(root)
    sql_frame.pack(pady=5)
    ttk.Label(sql_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
    user_entry = ttk.Entry(sql_frame, width=30)
    user_entry.grid(row=0, column=1, padx=5, pady=5)
    user_entry.insert(0, "sa")
    ttk.Label(sql_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5)
    pwd_entry = ttk.Entry(sql_frame, width=30, show="*")
    pwd_entry.grid(row=1, column=1, padx=5, pady=5)

    def toggle_sql_fields():
        state = "normal" if auth_var.get() == "SQL" else "disabled"
        user_entry.config(state=state)
        pwd_entry.config(state=state)

    auth_var.trace("w", lambda *args: toggle_sql_fields())
    toggle_sql_fields()  # Initial state

    # Status Label
    status_label = ttk.Label(root, text="")
    status_label.pack(pady=10)

    def save_config():
        """Save the configuration and test the connection."""
        server = server_entry.get().strip()
        db_name = db_entry.get().strip()
        auth_mode = auth_var.get()

        if not server or not db_name:
            messagebox.showerror("Error", "Server Name and Database Name are required.")
            return

        if auth_mode == "Windows":
            conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={db_name};Trusted_Connection=yes;"
        else:
            username = user_entry.get().strip()
            password = pwd_entry.get().strip()
            if not username or not password:
                messagebox.showerror("Error", "Username and Password are required for SQL Authentication.")
                return
            conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={db_name};UID={username};PWD={password}"

        # Test connection
        if test_connection(conn_str):
            config = {
                "connection_string": conn_str,
                "document_dirs": DEFAULT_DIRS,
                "email_settings": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": "587",
                    "smtp_username": "guthsouthafrica@gmail.com",
                    "smtp_password": "baar tgsr fjvp ktgw",
                    "sender_email": "guth@guth.co.za",
                    "use_tls": True
                }
            }
            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=4)
            status_label.config(text="Configuration saved successfully!", foreground="green")

            # Initialize database if admin agrees
            if messagebox.askyesno("Initialize Database", "Would you like to initialize the GuthPumpRegistry database now? (Requires sufficient permissions)"):
                try:
                    initialize_database()
                    insert_test_data()
                    status_label.config(text="Database initialized and test data inserted!", foreground="green")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to initialize database: {e}")
            root.quit()
        else:
            messagebox.showerror("Error", "Connection failed. Please check the server details and try again.")

    ttk.Button(root, text="Save and Test Connection", command=save_config).pack(pady=20)
    ttk.Button(root, text="Exit", command=root.quit).pack(pady=5)

    root.mainloop()

def install_dependencies():
    """Install required Python packages."""
    required = ["pyodbc", "ttkbootstrap", "pillow", "reportlab", "bcrypt"]
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

if __name__ == "__main__":
    print("Starting Guth Pump Registry installation...")
    install_dependencies()
    if not os.path.exists(CONFIG_PATH):
        configure_sql_server()
    else:
        print("Config already exists. Skipping setup.")
    print("Installation complete. Launching GuthPumpRegistry...")
    subprocess.Popen([sys.executable, "gui/base_gui.py"])
