import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sqlite3
import os

# Database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "guth_pump_registry.db")

def connect_db(timeout=20):
    """Connect to the database."""
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    return conn

class GuthPumpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Guth Pump Assembly Registry")
        self.root.geometry("800x600")
        self.show_login()

    def clear_window(self):
        """Clear all widgets from the window."""
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login(self):
        """Display the login window."""
        self.clear_window()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)

        ttk.Label(frame, text="Login", font=("Helvetica", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        ttk.Label(frame, text="Username:").grid(row=1, column=0, padx=5, pady=5, sticky=E)
        self.username_entry = ttk.Entry(frame)
        self.username_entry.grid(row=1, column=1, padx=5, pady=5)
        self.username_entry.insert(0, "user1")  # Default for testing

        ttk.Label(frame, text="Password:").grid(row=2, column=0, padx=5, pady=5, sticky=E)
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)
        self.password_entry.insert(0, "password")  # Stub for testing

        ttk.Button(frame, text="Login", command=self.login, bootstyle=SUCCESS).grid(row=3, column=0, columnspan=2, pady=20)

    def login(self):
        """Stub login validation (full auth in Sub-phase 2.2)."""
        username = self.username_entry.get()
        password = self.password_entry.get()
        if username == "user1" and password == "password":
            self.show_dashboard()
        else:
            ttk.Label(self.root, text="Invalid credentials", bootstyle=DANGER).pack(pady=10)

    def show_dashboard(self):
        """Display the main dashboard."""
        self.clear_window()

        # Sidebar
        sidebar = ttk.Frame(self.root, width=200, relief=RAISED, borderwidth=1)
        sidebar.pack(side=LEFT, fill=Y)

        ttk.Label(sidebar, text="Guth Pump Registry", font=("Helvetica", 14, "bold")).pack(pady=10)
        ttk.Button(sidebar, text="Pumps", command=self.show_pump_list, bootstyle=INFO).pack(fill=X, padx=10, pady=5)
        ttk.Button(sidebar, text="BOM", command=lambda: print("BOM placeholder"), bootstyle=INFO).pack(fill=X, padx=10, pady=5)
        ttk.Button(sidebar, text="Logout", command=self.show_login, bootstyle=WARNING).pack(fill=X, padx=10, pady=5, side=BOTTOM)

        # Main content
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=20, pady=20)

        self.show_pump_list()

    def show_pump_list(self):
        """Show a simple pump count from the database."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.main_frame, text="Dashboard", font=("Helvetica", 16, "bold")).pack(pady=10)

        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as pump_count FROM pumps")
            pump_count = cursor.fetchone()["pump_count"]

        ttk.Label(self.main_frame, text=f"Total Pumps Registered: {pump_count}").pack(pady=10)
        ttk.Label(self.main_frame, text="Pump list placeholder - Full view in later phase").pack(pady=10)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")  # Modern theme
    app = GuthPumpApp(root)
    root.mainloop()
