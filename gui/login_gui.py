import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from PIL import Image, ImageTk
from utils.config import get_logger
import os
import sys
import json
import smtplib
from email.mime.text import MIMEText
from database import get_db_connection

logger = get_logger("login_gui")

# Determine the base directory for bundled resources
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    CONFIG_DIR = os.path.join(os.getenv('APPDATA'), "GuthPumpRegistry")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
    DETAILS_PATH = os.path.join(CONFIG_DIR, "login_details.json")
else:
    BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
    DETAILS_PATH = os.path.join(BASE_DIR, "login_details.json")

LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
BUILD_NUMBER = "1.0.0"

def load_config():
    """Load configuration from config.json."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
            logger.debug(f"Loaded config from {CONFIG_PATH}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {CONFIG_PATH}: {str(e)}")
    return {
        "email_settings": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": "587",
            "smtp_username": "",
            "smtp_password": "",
            "sender_email": "",
            "use_tls": True
        }
    }

def load_login_details():
    """Load saved login details if they exist."""
    if os.path.exists(DETAILS_PATH):
        try:
            with open(DETAILS_PATH, "r") as f:
                details = json.load(f)
            logger.debug(f"Loaded login details from {DETAILS_PATH}")
            return details
        except Exception as e:
            logger.error(f"Failed to load login details from {DETAILS_PATH}: {str(e)}")
    return {"username": "", "password": "", "remember": False}

def save_login_details(username, password, remember):
    """Save login details if Remember Me is checked."""
    details = {"username": username, "password": password, "remember": remember}
    try:
        with open(DETAILS_PATH, "w") as f:
            json.dump(details, f, indent=4)
        logger.debug(f"Saved login details to {DETAILS_PATH}")
    except Exception as e:
        logger.error(f"Failed to save login details to {DETAILS_PATH}: {str(e)}")

def show_login_screen(root, login_callback, register_callback):
    """Display the login screen and return frame and error label for external control."""
    logger.info("Showing login screen")
    login_frame = ttk.Frame(root, padding=20)
    login_frame.pack(expand=True)

    # Header with logo and title
    header_frame = ttk.Frame(login_frame, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20))
    header_frame.grid_columnconfigure(0, weight=1)

    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH)
            new_width = int(img.width * 1.5)
            new_height = int(img.height * 1.5)
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            logo_label = ttk.Label(header_frame, image=logo)
            logo_label.image = logo  # Prevent garbage collection
            logo_label.grid(row=0, column=0, pady=10, padx=(0, 20))
            logger.debug(f"Logo loaded and scaled to {logo.width()}x{logo.height()} from {LOGO_PATH}")
        except Exception as e:
            logger.error(f"Logo load failed: {str(e)}")
            ttk.Label(header_frame, text="Logo Load Failed", font=("Roboto", 18, "bold")).grid(row=0, column=0, pady=10, padx=(0, 20))
    else:
        logger.warning(f"Logo not found at: {LOGO_PATH}")
        ttk.Label(header_frame, text="Logo Missing", font=("Roboto", 18, "bold")).grid(row=0, column=0, pady=10, padx=(0, 20))

    ttk.Label(header_frame, text="Pump Registry", font=("Roboto", 18, "bold"), bootstyle="primary").grid(row=1, column=0)
    ttk.Label(header_frame, text="Login to your account", font=("Roboto", 14)).grid(row=2, column=0)

    # Input frame
    input_frame = ttk.LabelFrame(login_frame, text="Credentials", padding=20, bootstyle="default")
    input_frame.pack(fill=X, padx=20, pady=10)

    # Load saved login details
    saved_details = load_login_details()

    # Username
    ttk.Label(input_frame, text="Username:", font=("Roboto", 14)).pack(anchor=W, pady=(5, 0))
    username_entry = ttk.Entry(input_frame, width=30, font=("Roboto", 12))
    username_entry.insert(0, saved_details["username"])
    username_entry.pack(fill=X, pady=5)
    username_entry.focus_set()
    ToolTip(username_entry, text="Enter your username", bootstyle="info")

    # Password
    ttk.Label(input_frame, text="Password:", font=("Roboto", 14)).pack(anchor=W, pady=(5, 0))
    password_entry = ttk.Entry(input_frame, width=30, show="*", font=("Roboto", 12))
    password_entry.insert(0, saved_details["password"])
    password_entry.pack(fill=X, pady=5)
    ToolTip(password_entry, text="Enter your password", bootstyle="info")
    show_password = ttk.BooleanVar(value=False)
    show_password_check = ttk.Checkbutton(input_frame, text="Show Password", variable=show_password,
                                          command=lambda: password_entry.config(show="" if show_password.get() else "*"),
                                          style="TCheckbutton")
    show_password_check.pack(anchor=W, pady=5)
    ToolTip(show_password_check, text="Toggle password visibility", bootstyle="info")

    # Remember Me
    remember_me = ttk.BooleanVar(value=saved_details["remember"])
    remember_check = ttk.Checkbutton(input_frame, text="Remember Me", variable=remember_me, style="TCheckbutton")
    remember_check.pack(anchor=W, pady=5)
    ToolTip(remember_check, text="Save login details for next time", bootstyle="info")

    # Error label
    error_label = ttk.Label(input_frame, text="", font=("Roboto", 12), bootstyle="danger")
    error_label.pack(fill=X, pady=(5, 0))

    # Buttons
    button_frame = ttk.Frame(login_frame)
    button_frame.pack(pady=20)
    login_button = ttk.Button(button_frame, text="Login",
                              command=lambda: [login_callback(username_entry.get(), password_entry.get()), save_login_details(username_entry.get(), password_entry.get(), remember_me.get()) if remember_me.get() else None],
                              bootstyle="success", style="large.TButton")
    login_button.pack(side=LEFT, padx=10)
    ToolTip(login_button, text="Log in to your account", bootstyle="success")
    register_button = ttk.Button(button_frame, text="Register", command=register_callback,
                                 bootstyle="danger", style="large.TButton")
    register_button.pack(side=LEFT, padx=10)
    ToolTip(register_button, text="Register a new account", bootstyle="danger")

    # Forgot Password Button
    forgot_button = ttk.Button(login_frame, text="Forgot Password?",
                               command=lambda: forgot_password_window(root, username_entry.get()),
                               bootstyle="info", style="large.TButton")
    forgot_button.pack(pady=(5, 10))
    ToolTip(forgot_button, text="Request a password reset link", bootstyle="info")

    # Footer
    ttk.Label(login_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(login_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    # Bind Enter key
    root.bind("<Return>", lambda event: [login_callback(username_entry.get(), password_entry.get()), save_login_details(username_entry.get(), password_entry.get(), remember_me.get()) if remember_me.get() else None])

    return login_frame, error_label

def forgot_password_window(root, username):
    """Display a window for requesting a password reset with email functionality."""
    logger.info(f"Opening forgot password window for username: {username}")
    forgot_window = ttk.Toplevel(root)
    forgot_window.title("Forgot Password")
    forgot_window.geometry("300x200")
    forgot_window.transient(root)
    forgot_window.grab_set()

    forgot_frame = ttk.Frame(forgot_window, padding=10)
    forgot_frame.pack(fill=BOTH, expand=True)

    ttk.Label(forgot_frame, text="Enter your username or email to reset your password:", font=("Roboto", 12)).pack(pady=10)
    reset_entry = ttk.Entry(forgot_frame, width=30, font=("Roboto", 12))
    reset_entry.insert(0, username)
    reset_entry.pack(pady=5)
    ToolTip(reset_entry, text="Enter your username or registered email", bootstyle="info")

    result_label = ttk.Label(forgot_frame, text="", font=("Roboto", 10), bootstyle="danger")
    result_label.pack(pady=5)

    def submit_reset():
        reset_value = reset_entry.get().strip()
        if not reset_value:
            result_label.config(text="Please enter a username or email.", bootstyle="danger")
            logger.warning("Password reset attempted with empty input")
            return
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT email FROM users WHERE username = ? OR email = ?", (reset_value, reset_value))
                user = cursor.fetchone()
                if not user:
                    result_label.config(text="User not found.", bootstyle="danger")
                    logger.warning(f"Password reset failed: {reset_value} not found")
                    return
                email = user[0]

            config = load_config()
            email_settings = config.get("email_settings", {})
            smtp_host = email_settings.get("smtp_host", "smtp.gmail.com")
            smtp_port = int(email_settings.get("smtp_port", 587))
            smtp_username = email_settings.get("smtp_username", "")
            smtp_password = email_settings.get("smtp_password", "")
            sender_email = email_settings.get("sender_email", "")
            use_tls = email_settings.get("use_tls", True)

            if not all([smtp_host, smtp_port, sender_email, smtp_username, smtp_password]):
                result_label.config(text="Email settings incomplete. Contact admin.", bootstyle="danger")
                logger.error("Incomplete SMTP settings for password reset")
                return

            # Simulated reset token (in production, generate a unique token and store it)
            reset_token = "RESET123"  # Placeholder; replace with secure token generation
            reset_link = f"http://example.com/reset?token={reset_token}"  # Replace with actual reset URL

            msg = MIMEText(f"Click the link to reset your password: {reset_link}\nThis link expires in 24 hours.")
            msg["Subject"] = "Password Reset Request - Guth Pump Registry"
            msg["From"] = sender_email
            msg["To"] = email

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if use_tls:
                    server.starttls()
                server.login(smtp_username, smtp_password)
                server.sendmail(sender_email, email, msg.as_string())
                logger.info(f"Password reset email sent to {email}")

            result_label.config(text=f"Reset link sent to {email}. Check your email.", bootstyle="success")
            forgot_window.after(2000, forgot_window.destroy)
        except Exception as e:
            logger.error(f"Password reset failed: {str(e)}")
            result_label.config(text="Error sending reset link. Try again.", bootstyle="danger")

    ttk.Button(forgot_frame, text="Submit", command=submit_reset, bootstyle="success", style="large.TButton").pack(pady=10)
    ToolTip(forgot_frame, text="Submit your request to receive a password reset link", bootstyle="success")

    forgot_window.wait_window()

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    def mock_login(username, password):
        print(f"Login attempted with {username}, {password}")
    def mock_register():
        print("Register clicked")
    show_login_screen(root, mock_login, mock_register)
    root.mainloop()