import ttkbootstrap as ttk
from ttkbootstrap.constants import *

def show_admin_gui(root, username):
    frame = ttk.Frame(root)
    frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
    ttk.Label(frame, text="Admin Panel (Coming Soon)", font=("Helvetica", 16, "bold")).pack(pady=10)