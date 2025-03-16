import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from database import connect_db
from gui.pump_originator_gui import show_pump_originator_gui
from gui.stores_gui import show_stores_gui
from gui.assembler_gui import show_assembler_gui
from gui.testing_gui import show_testing_gui
from gui.admin_gui import show_admin_gui
from utils.config import get_logger

logger = get_logger("dashboard_gui")

def show_dashboard(root, username, role, logout_callback):
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True)

    sidebar = ttk.Frame(main_frame)
    sidebar.pack(side=LEFT, fill=Y, padx=10, pady=10)

    role_actions = {
        "Pump Originator": [("Create Pump", lambda: show_pump_originator_gui(main_frame, username))],
        "Stores": [("Pull Parts", lambda: show_stores_gui(main_frame, username))],
        "Assembler": [("Verify BOM", lambda: show_assembler_gui(main_frame, username))],
        "Testing": [("Test Pumps", lambda: show_testing_gui(main_frame, username))],
        "Admin": [("Admin Panel", lambda: show_admin_gui(main_frame, username))]
    }

    if role in role_actions:
        for label, command in role_actions[role]:
            ttk.Button(sidebar, text=label, command=command, bootstyle="info", 
                       style="large.TButton").pack(pady=5, fill=X)

    ttk.Button(sidebar, text="Logout", command=logout_callback, bootstyle="warning", 
               style="large.TButton").pack(pady=20, fill=X)

    content = ttk.Frame(main_frame)
    content.pack(side=RIGHT, fill=BOTH, expand=True, padx=10, pady=10)
    ttk.Label(content, text=f"Welcome, {username} ({role})", font=("Roboto", 18)).pack(pady=10)
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT serial_number, status FROM pumps")
        pumps = cursor.fetchall()
        for pump in pumps:
            ttk.Label(content, text=f"S/N: {pump['serial_number']} - Status: {pump['status']}", 
                     font=("Roboto", 12)).pack()

    return main_frame