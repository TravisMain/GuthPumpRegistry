import sys
import os
import traceback
import logging

# Print immediately to confirm execution starts
print("BaseGUI: Execution started")

# Path handling for PyInstaller
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

BASE_DIR = resource_path("")
print(f"BaseGUI: BASE_DIR set to {BASE_DIR}")

# Define config paths
if getattr(sys, 'frozen', False):
    CONFIG_DIR = os.path.join(os.getenv('APPDATA'), "GuthPumpRegistry")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
    DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
else:
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
    DEFAULT_CONFIG_PATH = CONFIG_PATH

# Logging setup with persistent config directory
LOG_DIR = os.path.join(BASE_DIR if not getattr(sys, 'frozen', False) else CONFIG_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "app.log")

try:
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    from utils.config import get_logger
    logger = get_logger("base_gui")
    logger.info("Logger initialized")
    print(f"BaseGUI: Logger initialized at {log_file}")

    # Import all modules
    logger.info("Attempting to load all imports")
    print("BaseGUI: Attempting to load all imports")
    import ttkbootstrap as ttk
    import pyodbc
    from gui.styles import configure_styles
    from gui.login_gui import show_login_screen, save_login_details  # Added save_login_details import
    from gui.register_gui import show_register_window
    from gui.dashboard_gui import show_dashboard
    from gui.admin_gui import show_admin_gui
    from gui.stores_gui import show_stores_dashboard
    from gui.combined_assembler_tester_gui import show_combined_assembler_tester_dashboard
    from gui.approval_gui import show_approval_dashboard
    from database import get_db_connection, check_user, insert_user
except Exception as e:
    error_msg = f"BaseGUI: Import error: {str(e)}\n{traceback.format_exc()}"
    print(error_msg)  # Print to console for .exe
    try:
        logging.basicConfig(filename="app.log", level=logging.DEBUG)  # Fallback logging
        logger = logging.getLogger("base_gui")
        logger.error(error_msg)
    except:
        print("BaseGUI: Failed to initialize logging")
    if not getattr(sys, 'frozen', False):  # Only pause in development mode
        input("Press Enter to continue . . .")
    sys.exit(1)

class BaseGUI:
    def __init__(self, root):
        logger.info("Initializing BaseGUI")
        print("BaseGUI: Initializing BaseGUI")
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
        logger.info("Showing login screen")
        print("BaseGUI: Showing login screen")
        if self.main_frame:
            self.main_frame.destroy()
            self.main_frame = None
        if self.login_frame:
            self.login_frame.destroy()
        self.login_frame, self.error_label = show_login_screen(self.root, self.login, self.show_register)

    def login(self, username, password):
        """Handle login attempt, save login details if Remember Me is checked, and route to appropriate dashboard."""
        logger.info(f"Login attempt for {username}")
        print(f"BaseGUI: Login attempt for {username}")
        if not self.error_label:
            self.error_label = ttk.Label(self.login_frame, text="", bootstyle="danger")
            self.error_label.pack(pady=5)
        self.error_label.config(text="")

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                role = check_user(cursor, username, password)
            if role:
                # Save login details if Remember Me is checked
                if hasattr(self.login_frame, 'remember_me'):  # Check if login_frame has remember_me attribute
                    remember_me = self.login_frame.remember_me.get()
                    if remember_me:
                        save_login_details(username, password, True)
                        logger.info(f"Saved login details for {username} due to Remember Me")
                        print(f"BaseGUI: Saved login details for {username} due to Remember Me")
                    else:
                        save_login_details("", "", False)  # Clear saved details if unchecked
                        logger.info("Cleared saved login details as Remember Me was unchecked")
                        print("BaseGUI: Cleared saved login details as Remember Me was unchecked")

                self.username = username
                self.role = role
                self.login_frame.destroy()
                self.login_frame = None
                self.error_label = None
                self.root.unbind("<Return>")
                self.root.state("zoomed")
                if role == "Admin":
                    show_admin_gui(self.root, self.username, self.logout)
                elif role == "Stores":
                    self.main_frame = show_stores_dashboard(self.root, self.username, self.role, self.logout)
                elif role == "Assembler_Tester":
                    self.main_frame = show_combined_assembler_tester_dashboard(self.root, self.username, self.role, self.logout)
                elif role == "Approval":
                    self.main_frame = show_approval_dashboard(self.root, self.username, self.role, self.logout)
                else:
                    self.main_frame = show_dashboard(self.root, self.username, self.role, self.logout)
                logger.info(f"User {username} logged in with role {role}")
                print(f"BaseGUI: User {username} logged in with role {role}")
            else:
                self.error_label.config(text="Incorrect username or password", bootstyle="danger")
                logger.warning(f"Failed login attempt for {username}")
                print(f"BaseGUI: Failed login attempt for {username}")
        except Exception as e:
            error_msg = f"BaseGUI: Login failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            print(error_msg)
            self.error_label.config(text=f"Login failed: {str(e)}", bootstyle="danger")

    def show_register(self):
        """Show the registration window."""
        logger.info("Showing register window")
        print("BaseGUI: Showing register window")
        show_register_window(self.root, self.register)

    def register(self, username, password, name, surname, email, error_label):
        """Handle user registration (default to Pump Originator)."""
        logger.info(f"Register attempt for {username}")
        print(f"BaseGUI: Register attempt for {username}")
        if not all([username, password, name, surname, email]):
            error_label.config(text="All fields are required", bootstyle="danger")
            logger.warning(f"Registration failed for {username}: Missing fields")
            print(f"BaseGUI: Registration failed for {username}: Missing fields")
            return
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                insert_user(cursor, username, password, "Pump Originator", name, surname, email)
                conn.commit()
                error_label.config(text="Registration successful! You can now login.", bootstyle="success")
                logger.info(f"Registered new Pump Originator: {username}")
                print(f"BaseGUI: Registered new Pump Originator: {username}")
        except pyodbc.IntegrityError:
            error_label.config(text="Username already exists", bootstyle="danger")
            logger.warning(f"Failed registration: {username} already exists")
            print(f"BaseGUI: Failed registration: {username} already exists")
        except Exception as e:
            error_msg = f"BaseGUI: Registration failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            print(error_msg)
            error_label.config(text=f"Registration failed: {str(e)}", bootstyle="danger")

    def logout(self):
        """Handle logout and return to login screen."""
        logger.info(f"Logging out user {self.username}")
        print(f"BaseGUI: Logging out user {self.username}")
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
        print("BaseGUI: User logged out")

if __name__ == "__main__":
    try:
        logger.info("Application starting")
        print("BaseGUI: Application starting")
        root = ttk.Window(themename="flatly")
        configure_styles()
        app = BaseGUI(root)
        logger.info("Main loop starting")
        print("BaseGUI: Main loop starting")
        root.mainloop()
    except Exception as e:
        error_msg = f"BaseGUI: Main error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        print(error_msg)
        if not getattr(sys, 'frozen', False):  # Only pause in development mode
            input("Press Enter to continue . . .")
        sys.exit(1)