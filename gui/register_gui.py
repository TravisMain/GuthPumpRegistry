import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from utils.config import get_logger

logger = get_logger("register_gui")

def show_register_window(root, register_callback):
    register_window = ttk.Toplevel(root)
    register_window.title("Register as Pump Originator")
    register_window.geometry("400x400")

    frame = ttk.Frame(register_window)
    frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

    ttk.Label(frame, text="Register", font=("Helvetica", 18, "bold")).pack(pady=10)

    ttk.Label(frame, text="Username:", font=("Roboto", 14)).pack()
    username_entry = ttk.Entry(frame, font=("Roboto", 12))
    username_entry.pack(pady=5)

    ttk.Label(frame, text="Name:", font=("Roboto", 14)).pack()
    name_entry = ttk.Entry(frame, font=("Roboto", 12))
    name_entry.pack(pady=5)

    ttk.Label(frame, text="Surname:", font=("Roboto", 14)).pack()
    surname_entry = ttk.Entry(frame, font=("Roboto", 12))
    surname_entry.pack(pady=5)

    ttk.Label(frame, text="Email:", font=("Roboto", 14)).pack()
    email_entry = ttk.Entry(frame, font=("Roboto", 12))
    email_entry.pack(pady=5)

    ttk.Label(frame, text="Password:", font=("Roboto", 14)).pack()
    password_entry = ttk.Entry(frame, show="*", font=("Roboto", 12))
    password_entry.pack(pady=5)

    error_label = ttk.Label(frame, text="", font=("Roboto", 12))
    error_label.pack(pady=10)

    def submit():
        register_callback(
            username_entry.get(),
            password_entry.get(),
            name_entry.get(),
            surname_entry.get(),
            email_entry.get(),
            error_label
        )

    ttk.Button(frame, text="Submit", command=submit, bootstyle="success", 
               style="large.TButton").pack(pady=20)
    register_window.bind("<Return>", lambda event: submit())