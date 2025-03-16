import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from database import connect_db, check_user
from gui.pump_originator_gui import show_pump_originator_gui
from gui.stores_gui import show_stores_gui
from gui.assembler_gui import show_assembler_gui
from gui.testing_gui import show_testing_gui
from gui.admin_gui import show_admin_gui
from utils.config import get_logger

logger = get_logger("base_gui")

class BaseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Guth Pump Registry")
        self.root.geometry("800x600")
        self.username = None
        self.role = None
        self.show_login_screen()

    def show_login_screen(self):
        self.login_frame = ttk.Frame(self.root)
        self.login_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        ttk.Label(self.login_frame, text="Login", font=("Helvetica", 16, "bold")).pack(pady=10)
        ttk.Label(self.login_frame, text="Username:").pack()
        self.username_entry = ttk.Entry(self.login_frame)
        self.username_entry.pack(pady=5)
        ttk.Label(self.login_frame, text="Password:").pack()
        self.password_entry = ttk.Entry(self.login_frame, show="*")
        self.password_entry.pack(pady=5)

        ttk.Button(self.login_frame, text="Login", command=self.login, bootstyle=SUCCESS).pack(pady=20)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        with connect_db() as conn:
            cursor = conn.cursor()
            role = check_user(cursor, username, password)
        if role:
            self.username = username
            self.role = role
            self.login_frame.destroy()
            self.show_dashboard()
            logger.info(f"User {username} logged in with role {role}")
        else:
            ttk.Label(self.login_frame, text="Invalid credentials", bootstyle=DANGER).pack(pady=10)
            logger.warning(f"Failed login attempt for {username}")

    def show_dashboard(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=True)

        sidebar = ttk.Frame(self.main_frame)
        sidebar.pack(side=LEFT, fill=Y, padx=10, pady=10)

        role_actions = {
            "Pump Originator": [("Create Pump", lambda: show_pump_originator_gui(self.main_frame, self.username))],
            "Stores": [("Pull Parts", lambda: show_stores_gui(self.main_frame, self.username))],
            "Assembler": [("Verify BOM", lambda: show_assembler_gui(self.main_frame, self.username))],
            "Testing": [("Test Pumps", lambda: show_testing_gui(self.main_frame, self.username))],
            "Admin": [("Admin Panel", lambda: show_admin_gui(self.main_frame, self.username))]
        }

        # Show only actions for the user's role
        if self.role in role_actions:
            for label, command in role_actions[self.role]:
                ttk.Button(sidebar, text=label, command=command, bootstyle=INFO).pack(pady=5, fill=X)

        ttk.Button(sidebar, text="Logout", command=self.logout, bootstyle=WARNING).pack(pady=20, fill=X)

        # Dashboard content (pump list)
        content = ttk.Frame(self.main_frame)
        content.pack(side=RIGHT, fill=BOTH, expand=True, padx=10, pady=10)
        ttk.Label(content, text=f"Welcome, {self.username} ({self.role})", font=("Helvetica", 14)).pack(pady=10)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT serial_number, status FROM pumps")
            pumps = cursor.fetchall()
            for pump in pumps:
                ttk.Label(content, text=f"S/N: {pump['serial_number']} - Status: {pump['status']}").pack()

    def logout(self):
        self.main_frame.destroy()
        self.username = None
        self.role = None
        self.show_login_screen()
        logger.info("User logged out")

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    app = BaseGUI(root)
    root.mainloop()