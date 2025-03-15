import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sqlite3
import os
from gui.pump_originator_gui import show_pump_originator_gui
from gui.stores_gui import show_stores_gui
from gui.assembler_gui import show_assembler_gui
from gui.testing_gui import show_testing_gui
from gui.admin_gui import show_admin_gui

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "guth_pump_registry.db")

def connect_db(timeout=20):
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    return conn

class GuthPumpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Guth Pump Assembly Registry")
        self.root.geometry("800x600")
        self.username = None
        self.role = None
        self.show_login()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear_window()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)

        ttk.Label(frame, text="Login", font=("Helvetica", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        ttk.Label(frame, text="Username:").grid(row=1, column=0, padx=5, pady=5, sticky=E)
        self.username_entry = ttk.Entry(frame)
        self.username_entry.grid(row=1, column=1, padx=5, pady=5)
        self.username_entry.insert(0, "user1")

        ttk.Label(frame, text="Password:").grid(row=2, column=0, padx=5, pady=5, sticky=E)
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)
        self.password_entry.insert(0, "password")

        ttk.Label(frame, text="Role:").grid(row=3, column=0, padx=5, pady=5, sticky=E)
        self.role_combo = ttk.Combobox(frame, values=["Pump Originator", "Stores", "Assembler", "Testing", "Admin"])
        self.role_combo.grid(row=3, column=1, padx=5, pady=5)
        self.role_combo.set("Pump Originator")

        ttk.Button(frame, text="Login", command=self.login, bootstyle=SUCCESS).grid(row=4, column=0, columnspan=2, pady=20)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        role = self.role_combo.get()
        if username == "user1" and password == "password":  # Stub check
            self.username = username
            self.role = role
            self.show_dashboard()
        else:
            ttk.Label(self.root, text="Invalid credentials", bootstyle=DANGER).pack(pady=10)

    def show_dashboard(self):
        self.clear_window()
        sidebar = ttk.Frame(self.root, width=200, relief=RAISED, borderwidth=1)
        sidebar.pack(side=LEFT, fill=Y)

        ttk.Label(sidebar, text=f"Guth Pump Registry\nRole: {self.role}", font=("Helvetica", 14, "bold")).pack(pady=10)

        role_actions = {
            "Pump Originator": [("Create Pump", lambda: show_pump_originator_gui(self.main_frame, self.username))],
            "Stores": [("Pull Parts", lambda: show_stores_gui(self.main_frame, self.username))],
            "Assembler": [("Verify BOM", lambda: show_assembler_gui(self.main_frame, self.username))],
            "Testing": [("Test Pumps", lambda: show_testing_gui(self.main_frame, self.username))],
            "Admin": [("Admin Panel", lambda: show_admin_gui(self.main_frame, self.username))]
        }

        # Show all actions for testing (remove role restriction temporarily)
        for role, actions in role_actions.items():
            for text, cmd in actions:
                btn = ttk.Button(sidebar, text=f"{role}: {text}", command=cmd, bootstyle=INFO)
                btn.pack(fill=X, padx=10, pady=5)

        ttk.Button(sidebar, text="Logout", command=self.show_login, bootstyle=WARNING).pack(fill=X, padx=10, pady=5, side=BOTTOM)

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=20, pady=20)
        self.show_pump_list()

    def show_pump_list(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        ttk.Label(self.main_frame, text="Dashboard", font=("Helvetica", 16, "bold")).pack(pady=10)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT serial_number, status FROM pumps ORDER BY serial_number")
            pumps = cursor.fetchall()
        ttk.Label(self.main_frame, text=f"Total Pumps: {len(pumps)}").pack(pady=5)
        for pump in pumps:
            ttk.Label(self.main_frame, text=f"S/N: {pump['serial_number']} - Status: {pump['status']}").pack(pady=2)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    app = GuthPumpApp(root)
    root.mainloop()