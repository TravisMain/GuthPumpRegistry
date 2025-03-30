import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from PIL import Image, ImageTk
from utils.config import get_logger
import os

logger = get_logger("register_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
BUILD_NUMBER = "1.0.0"

def show_register_window(root, register_callback):
    """Display a window for registering as a Pump Originator."""
    register_window = ttk.Toplevel(root)
    register_window.title("Register as Pump Originator")
    
    # Original size increased by 35%
    original_width, original_height = 400, 400
    new_width = int(original_width * 1.35)
    new_height = int(original_height * 1.35)
    register_window.geometry(f"{new_width}x{new_height}")

    header_frame = ttk.Frame(register_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20))
    header_frame.grid_columnconfigure(0, weight=1)  # Center content
    header_frame.grid_columnconfigure(1, weight=1)  # Right-align logo

    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH)
            logo_width = int(img.width * 1.05)  # 1.05x original size
            logo_height = int(img.height * 1.05)
            img_resized = img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            ttk.Label(header_frame, image=logo).grid(row=0, column=1, pady=10, padx=(0, 20), sticky=E)
            header_frame.image = logo  # Keep reference
            logger.debug(f"Logo loaded and scaled to {logo.width()}x{logo.height()}")
        except Exception as e:
            logger.error(f"Logo load failed: {str(e)}")
            ttk.Label(header_frame, text="Logo Load Failed", font=("Roboto", 18, "bold")).grid(row=0, column=1, pady=10, padx=(0, 20), sticky=E)
    else:
        logger.warning(f"Logo not found at: {LOGO_PATH}")
        ttk.Label(header_frame, text="Logo Missing", font=("Roboto", 18, "bold")).grid(row=0, column=1, pady=10, padx=(0, 20), sticky=E)

    ttk.Label(header_frame, text="Register as Pump Originator", font=("Roboto", 18, "bold"), bootstyle="primary").grid(row=1, column=0, columnspan=2)
    ttk.Label(header_frame, text="Create a new account", font=("Roboto", 14)).grid(row=2, column=0, columnspan=2)

    frame = ttk.Frame(register_window)
    frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

    fields = [
        ("Username", "Enter your username"),
        ("Name", "Enter your first name"),
        ("Surname", "Enter your surname"),
        ("Email", "Enter your email address"),
        ("Password", "Enter your password"),
    ]
    entries = {}
    for i, (label_text, tooltip_text) in enumerate(fields):
        ttk.Label(frame, text=f"{label_text}:", font=("Roboto", 14)).grid(row=i, column=0, padx=5, pady=(5, 0), sticky=W)
        entry = ttk.Entry(frame, font=("Roboto", 12), show="*" if label_text == "Password" else "")
        entry.grid(row=i, column=1, padx=5, pady=5, sticky=EW)
        ToolTip(entry, text=tooltip_text, bootstyle="info")
        entries[label_text.lower()] = entry

    frame.grid_columnconfigure(1, weight=1)

    error_label = ttk.Label(frame, text="", font=("Roboto", 12, "bold"), bootstyle="danger")
    error_label.grid(row=len(fields), column=0, columnspan=2, pady=10)

    def submit():
        """Submit registration data via callback."""
        register_callback(
            entries["username"].get(),
            entries["password"].get(),
            entries["name"].get(),
            entries["surname"].get(),
            entries["email"].get(),
            error_label
        )

    submit_button = ttk.Button(frame, text="Submit", command=submit, bootstyle="success", style="large.TButton")
    submit_button.grid(row=len(fields) + 1, column=0, columnspan=2, pady=20)
    ToolTip(submit_button, text="Register your account", bootstyle="success")

    register_window.bind("<Return>", lambda event: submit())

    footer_frame = ttk.Frame(register_window)
    footer_frame.pack(side=BOTTOM, pady=10)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return register_window

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_register_window(root, lambda u, p, n, s, e, el: print(f"Registered: {u}, {n}, {s}, {e}"))
    root.mainloop()