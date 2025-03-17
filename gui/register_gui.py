import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from PIL import Image, ImageTk
from utils.config import get_logger
import os

logger = get_logger("register_gui")
LOGO_PATH = r"C:\Users\travism\source\repos\GuthPumpRegistry\assets\logo.png"
BUILD_NUMBER = "1.0.0"

def show_register_window(root, register_callback):
    register_window = ttk.Toplevel(root)
    register_window.title("Register as Pump Originator")
    
    # Original size
    original_width = 400
    original_height = 400
    
    # Increase size by 35% (1.35x)
    new_width = int(original_width * 1.35)
    new_height = int(original_height * 1.35)
    register_window.geometry(f"{new_width}x{new_height}")

    # Header with logo and title
    header_frame = ttk.Frame(register_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20))
    header_frame.grid_columnconfigure(0, weight=1)  # Center content
    header_frame.grid_columnconfigure(1, weight=1)  # Allow right alignment for logo

    if os.path.exists(LOGO_PATH):
        logger.info(f"Logo file exists at: {LOGO_PATH}")
        try:
            # Open with PIL for high-quality resizing
            img = Image.open(LOGO_PATH)
            original_width, original_height = img.size
            logger.info(f"Logo loaded: {original_width}x{original_height}")
            # Scale to 1.5x original size, then reduce by 30% (1.5 * 0.7 = 1.05x original)
            logo_width = int(original_width * 1.05)  # 1.5 * 0.7 = 1.05
            logo_height = int(original_height * 1.05)
            img_resized = img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            logger.info(f"Logo scaled: {logo.width()}x{logo.height()}")
            logo_label = ttk.Label(header_frame, image=logo)
            logo_label.image = logo  # Keep reference
            logo_label.grid(row=0, column=1, pady=10, padx=(0, 20), sticky=E)  # Top right corner
        except Exception as e:
            logger.error(f"Logo load failed: {str(e)}")
            ttk.Label(header_frame, text="Logo Load Failed", font=("Roboto", 18, "bold")).grid(row=0, column=1, pady=10, padx=(0, 20), sticky=E)
    else:
        logger.warning(f"Logo not found at: {LOGO_PATH}")
        ttk.Label(header_frame, text="Logo Missing", font=("Roboto", 18, "bold")).grid(row=0, column=1, pady=10, padx=(0, 20), sticky=E)
    
    ttk.Label(header_frame, text="Register as Pump Originator", font=("Roboto", 18, "bold"), bootstyle="primary").grid(row=1, column=0, columnspan=2)
    ttk.Label(header_frame, text="Create a new account", font=("Roboto", 14)).grid(row=2, column=0, columnspan=2)

    # Main frame for inputs
    frame = ttk.Frame(register_window)
    frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

    # Input fields with tooltips
    fields = [
        ("Username", ttk.Entry(frame, font=("Roboto", 12)), "Enter your username"),
        ("Name", ttk.Entry(frame, font=("Roboto", 12)), "Enter your first name"),
        ("Surname", ttk.Entry(frame, font=("Roboto", 12)), "Enter your surname"),
        ("Email", ttk.Entry(frame, font=("Roboto", 12)), "Enter your email address"),
        ("Password", ttk.Entry(frame, show="*", font=("Roboto", 12)), "Enter your password"),
    ]
    for label_text, entry, tooltip_text in fields:
        ttk.Label(frame, text=label_text + ":", font=("Roboto", 14)).pack(anchor=W, pady=(5, 0))
        entry.pack(fill=X, pady=5)
        ToolTip(entry, text=tooltip_text, bootstyle="info")

    # Error label
    error_label = ttk.Label(frame, text="", font=("Roboto", 12, "bold"), bootstyle="danger")
    error_label.pack(pady=10)

    # Submit button
    def submit():
        register_callback(
            fields[0][1].get(),
            fields[4][1].get(),  # Password is at index 4
            fields[1][1].get(),
            fields[2][1].get(),
            fields[3][1].get(),
            error_label
        )

    submit_button = ttk.Button(frame, text="Submit", command=submit, bootstyle="success", style="large.TButton")
    submit_button.pack(pady=20)
    ToolTip(submit_button, text="Register your account", bootstyle="success")

    # Bind Enter key
    register_window.bind("<Return>", lambda event: submit())

    # Copyright and Build Number
    footer_frame = ttk.Frame(register_window)
    footer_frame.pack(side=BOTTOM, pady=10)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return register_window