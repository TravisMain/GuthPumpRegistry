import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from PIL import Image, ImageTk
from utils.config import get_logger
import os

logger = get_logger("login_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
BUILD_NUMBER = "1.0.0"

def show_login_screen(root, login_callback, register_callback):
    # Use Frame instead of placing directly for better cleanup
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
            logger.info(f"Logo loaded and scaled to {logo.width()}x{logo.height()}")
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

    # Username
    ttk.Label(input_frame, text="Username:", font=("Roboto", 14)).pack(anchor=W, pady=(5, 0))
    username_entry = ttk.Entry(input_frame, width=30, font=("Roboto", 12))
    username_entry.pack(fill=X, pady=5)
    username_entry.focus_set()
    ToolTip(username_entry, text="Enter your username", bootstyle="info")

    # Password
    ttk.Label(input_frame, text="Password:", font=("Roboto", 14)).pack(anchor=W, pady=(5, 0))
    password_entry = ttk.Entry(input_frame, width=30, show="*", font=("Roboto", 12))
    password_entry.pack(fill=X, pady=5)
    ToolTip(password_entry, text="Enter your password", bootstyle="info")
    show_password = ttk.BooleanVar(value=False)
    show_password_check = ttk.Checkbutton(input_frame, text="Show Password", variable=show_password,
                                          command=lambda: password_entry.config(show="" if show_password.get() else "*"),
                                          style="TCheckbutton")
    show_password_check.pack(anchor=W, pady=5)
    ToolTip(show_password_check, text="Toggle password visibility", bootstyle="info")

    # Error label
    error_label = ttk.Label(input_frame, text="", font=("Roboto", 12), bootstyle="danger")
    error_label.pack(fill=X, pady=(5, 0))

    # Buttons
    button_frame = ttk.Frame(login_frame)
    button_frame.pack(pady=20)
    login_button = ttk.Button(button_frame, text="Login",
                              command=lambda: login_callback(username_entry.get(), password_entry.get()),
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
    root.bind("<Return>", lambda event: login_callback(username_entry.get(), password_entry.get()))

    return login_frame, error_label

def forgot_password_window(root, username):
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
            return
        try:
            logger.info(f"Password reset requested for: {reset_value}")
            # Placeholder for actual reset logic
            result_label.config(text=f"Reset link sent to {reset_value} (simulated). Check your email.", bootstyle="success")
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