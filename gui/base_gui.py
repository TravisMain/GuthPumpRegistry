import ttkbootstrap as ttk
import pyodbc
from gui.styles import configure_styles
from gui.login_gui import show_login_screen
from gui.register_gui import show_register_window
from gui.dashboard_gui import show_dashboard
from gui.admin_gui import show_admin_gui
from gui.stores_gui import show_stores_dashboard
from gui.combined_assembler_tester_gui import show_combined_assembler_tester_dashboard
from gui.approval_gui import show_approval_dashboard
from database import get_db_connection, check_user, insert_user
from utils.config import get_logger

logger = get_logger("base_gui")

class BaseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Guth Pump Registry")
        self.root.geometry("800x900")
        self.username = None
        self.role = None
        self.login_frame = None
        self.error_label = None
        self.main_frame = None
        self.show_login()

    def show_login(self):
        """Display the login screen, clearing any existing main frame."""
        if self.main_frame:
            self.main_frame.destroy()
            self.main_frame = None
        # Clear any previous login frame to avoid overlap
        if self.login_frame:
            self.login_frame.destroy()
        self.login_frame, self.error_label = show_login_screen(self.root, self.login, self.show_register)

    def login(self, username, password):
        """Handle login attempt and route to appropriate dashboard."""
        if self.error_label:
            self.error_label.config(text="")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                role = check_user(cursor, username, password)
            if role:
                self.username = username
                self.role = role
                self.login_frame.destroy()
                self.root.unbind("<Return>")
                self.root.state("zoomed")
                if role == "Admin":
                    show_admin_gui(self.root, self.username, self.logout)
                elif role == "Stores":
                    self.main_frame = show_stores_dashboard(self.root, self.username, self.role, self.logout)
                elif role in ["Assembler", "Testing"]:
                    self.main_frame = show_combined_assembler_tester_dashboard(self.root, self.username, self.role, self.logout)
                elif role == "Approval":
                    self.main_frame = show_approval_dashboard(self.root, self.username, self.role, self.logout)
                else:  # Pump Originator or others
                    self.main_frame = show_dashboard(self.root, self.username, self.role, self.logout)
                logger.info(f"User {username} logged in with role {role}")
            else:
                if self.error_label:
                    self.error_label.config(text="Incorrect username or password", bootstyle="danger")
                logger.warning(f"Failed login attempt for {username}")
        except Exception as e:
            if self.error_label:
                self.error_label.config(text=f"Login failed: {str(e)}", bootstyle="danger")
            logger.error(f"Login error for {username}: {str(e)}")

    def show_register(self):
        """Show the registration window."""
        show_register_window(self.root, self.register)

    def register(self, username, password, name, surname, email, error_label):
        """Handle user registration."""
        if not all([username, password, name, surname, email]):
            error_label.config(text="All fields are required", bootstyle="danger")
            return
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                insert_user(cursor, username, password, "Pump Originator", name, surname, email)
                conn.commit()
                error_label.config(text="Registration successful! You can now login.", bootstyle="success")
                logger.info(f"Registered new Pump Originator: {username}")
        except pyodbc.IntegrityError:
            error_label.config(text="Username already exists", bootstyle="danger")
            logger.warning(f"Failed registration: {username} already exists")
        except Exception as e:
            error_label.config(text=f"Registration failed: {str(e)}", bootstyle="danger")
            logger.error(f"Registration error for {username}: {str(e)}")

    def logout(self):
        """Handle logout and return to login screen."""
        if self.role == "Admin":
            for widget in self.root.winfo_children():
                widget.destroy()
        elif self.main_frame:
            self.main_frame.destroy()
            self.main_frame = None
        self.username = None
        self.role = None
        self.root.state("normal")
        self.root.geometry("800x900")
        self.show_login()
        logger.info("User logged out")

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    configure_styles()
    app = BaseGUI(root)
    logger.info("Application started")
    root.mainloop()