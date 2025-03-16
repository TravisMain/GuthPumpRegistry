import ttkbootstrap as ttk
import sqlite3
from gui.styles import configure_styles
from gui.login_gui import show_login_screen
from gui.register_gui import show_register_window
from gui.dashboard_gui import show_dashboard
from database import connect_db, check_user, insert_user
from utils.config import get_logger

logger = get_logger("base_gui")

class BaseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Guth Pump Registry")
        self.root.geometry("800x900")  # Increased from 700 to 900
        self.username = None
        self.role = None
        self.login_frame = None
        self.error_label = None
        self.main_frame = None
        self.show_login()

    def show_login(self):
        if self.main_frame:
            self.main_frame.destroy()
        self.login_frame, self.error_label = show_login_screen(self.root, self.login, self.show_register)

    def login(self, username, password):
        with connect_db() as conn:
            cursor = conn.cursor()
            role = check_user(cursor, username, password)
        if role:
            self.username = username
            self.role = role
            self.login_frame.destroy()
            self.root.unbind("<Return>")
            self.main_frame = show_dashboard(self.root, self.username, self.role, self.logout)
            logger.info(f"User {username} logged in with role {role}")
        else:
            if self.error_label:
                self.error_label.config(text="Invalid credentials - try again", bootstyle="danger")
            logger.warning(f"Failed login attempt for {username}")

    def show_register(self):
        show_register_window(self.root, self.register)

    def register(self, username, password, name, surname, email, error_label):
        if not all([username, password, name, surname, email]):
            error_label.config(text="All fields are required", bootstyle="danger")
            return
        with connect_db() as conn:
            cursor = conn.cursor()
            try:
                insert_user(cursor, username, password, "Pump Originator", name, surname, email)
                conn.commit()
                error_label.config(text="Registration successful! You can now login.", bootstyle="success")
                logger.info(f"Registered new Pump Originator: {username}")
            except sqlite3.IntegrityError:
                error_label.config(text="Username already exists", bootstyle="danger")
                logger.warning(f"Failed registration: {username} already exists")

    def logout(self):
        self.main_frame.destroy()
        self.username = None
        self.role = None
        self.show_login()
        logger.info("User logged out")

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    configure_styles()
    app = BaseGUI(root)
    logger.info("Application started")
    root.mainloop()