import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from PIL import Image, ImageTk  # Added PIL imports
from utils.config import get_logger
import os

logger = get_logger("login_gui")
LOGO_PATH = r"C:\Users\travism\source\repos\GuthPumpRegistry\assets\logo.png"
BUILD_NUMBER = "1.0.0"

def show_login_screen(root, login_callback, register_callback):
    login_frame = ttk.Frame(root, padding=20)
    login_frame.place(relx=0.5, rely=0.5, anchor=CENTER)

    # Logo and title with grid for precise alignment
    header_frame = ttk.Frame(login_frame, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20))
    header_frame.grid_columnconfigure(0, weight=1)  # Center content

    if os.path.exists(LOGO_PATH):
        logger.info(f"Logo file exists at: {LOGO_PATH}")
        try:
            # Open with PIL for high-quality resizing
            img = Image.open(LOGO_PATH)
            original_width, original_height = img.size
            logger.info(f"Logo loaded: {original_width}x{original_height}")
            # Scale to 1.5x original size
            new_width = int(original_width * 1.5)
            new_height = int(original_height * 1.5)
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            logger.info(f"Logo scaled: {logo.width()}x{logo.height()}")
            logo_label = ttk.Label(header_frame, image=logo)
            logo_label.image = logo  # Keep reference
            logo_label.grid(row=0, column=0, pady=10, padx=(0, 20))  # Nudge right
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

    # Copyright and Build Number
    ttk.Label(login_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(login_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    # Bind Enter key
    root.bind("<Return>", lambda event: login_callback(username_entry.get(), password_entry.get()))
    return login_frame, ttk.Label(input_frame, text="", font=("Roboto", 12))  # Return frame and error label