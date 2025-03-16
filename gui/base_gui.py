import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sqlite3
from database import connect_db, check_user, insert_user
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
        self.error_label = None
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

        button_frame = ttk.Frame(self.login_frame)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="Login", command=self.login, bootstyle=SUCCESS).pack(side=LEFT, padx=10)
        ttk.Button(button_frame, text="Register", command=self.show_register_window, bootstyle=INFO).pack(side=LEFT, padx=10)

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
            if self.error_label:
                self.error_label.destroy()
            self.error_label = ttk.Label(self.login_frame, text="Invalid credentials", bootstyle=DANGER)
            self.error_label.pack(pady=10)
            self.username_entry.delete(0, END)
            self.password_entry.delete(0, END)
            logger.warning(f"Failed login attempt for {username}")

    def show_register_window(self):
        register_window = ttk.Toplevel(self.root)
        register_window.title("Register as Pump Originator")
        register_window.geometry("400x400")

        frame = ttk.Frame(register_window)
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        ttk.Label(frame, text="Register", font=("Helvetica", 16, "bold")).pack(pady=10)

        ttk.Label(frame, text="Username:").pack()
        username_entry = ttk.Entry(frame)
        username_entry.pack(pady=5)

        ttk.Label(frame, text="Name:").pack()
        name_entry = ttk.Entry(frame)
        name_entry.pack(pady=5)

        ttk.Label(frame, text="Surname:").pack()
        surname_entry = ttk.Entry(frame)
        surname_entry.pack(pady=5)

        ttk.Label(frame, text="Email:").pack()
        email_entry = ttk.Entry(frame)
        email_entry.pack(pady=5)

        ttk.Label(frame, text="Password:").pack()
        password_entry = ttk.Entry(frame, show="*")
        password_entry.pack(pady=5)

        error_label = ttk.Label(frame, text="")
        error_label.pack(pady=10)

        def register_user():
            username = username_entry.get()
            name = name_entry.get()
            surname = surname_entry.get()
            email = email_entry.get()
            password = password_entry.get()

            if not all([username, name, surname, email, password]):
                error_label.config(text="All fields are required", bootstyle=DANGER)
                return

            with connect_db() as conn:
                cursor = conn.cursor()
                try:
                    insert_user(cursor, username, password, "Pump Originator", name, surname, email)
                    conn.commit()
                    error_label.config(text="Registration successful! You can now login.", bootstyle=SUCCESS)
                    logger.info(f"Registered new Pump Originator: {username}")
                    username_entry.delete(0, END)
                    name_entry.delete(0, END)
                    surname_entry.delete(0, END)
                    email_entry.delete(0, END)
                    password_entry.delete(0, END)
                except sqlite3.IntegrityError:
                    error_label.config(text="Username already exists", bootstyle=DANGER)
                    logger.warning(f"Failed registration: {username} already exists")

        ttk.Button(frame, text="Submit", command=register_user, bootstyle=SUCCESS).pack(pady=20)

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

        if self.role in role_actions:
            for label, command in role_actions[self.role]:
                ttk.Button(sidebar, text=label, command=command, bootstyle=INFO).pack(pady=5, fill=X)

        ttk.Button(sidebar, text="Logout", command=self.logout, bootstyle=WARNING).pack(pady=20, fill=X)

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
        logger.info(f"User {self.username} logged out")

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    app = BaseGUI(root)
    logger.info("Application started")
    root.mainloop()