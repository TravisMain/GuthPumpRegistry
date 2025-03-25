# pump_originator_gui.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from database import connect_db, create_pump, create_bom_item
from utils.config import get_logger

logger = get_logger("pump_originator")
BUILD_NUMBER = "1.0.0"

def show_pump_originator_gui(root, username, logout_callback):
    # Clear existing widgets
    for widget in root.winfo_children():
        widget.destroy()

    # Set window to maximized state
    root.state('zoomed')

    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

    # Create New Pump Section (Fixed at the top)
    create_frame = ttk.LabelFrame(main_frame, text="Create New Pump", padding=10)
    create_frame.pack(fill=X, padx=10, pady=10)

    ttk.Label(create_frame, text="Create New Pump", font=("Helvetica", 16, "bold")).pack(pady=10)

    ttk.Label(create_frame, text="Pump Model:").pack()
    model_entry = ttk.Entry(create_frame)
    model_entry.insert(0, "P1 3.0kW")
    model_entry.pack(pady=5)

    ttk.Label(create_frame, text="Configuration:").pack()
    config_entry = ttk.Entry(create_frame)
    config_entry.insert(0, "Standard")
    config_entry.pack(pady=5)

    ttk.Label(create_frame, text="Customer:").pack()
    customer_entry = ttk.Entry(create_frame)
    customer_entry.insert(0, "Guth Test")
    customer_entry.pack(pady=5)

    # Add fields for pressure_required and flow_rate_required
    ttk.Label(create_frame, text="Pressure Required (bar):").pack()
    pressure_required_entry = ttk.Entry(create_frame)
    pressure_required_entry.pack(pady=5)

    ttk.Label(create_frame, text="Flow Rate Required (L/h):").pack()
    flow_rate_required_entry = ttk.Entry(create_frame)
    flow_rate_required_entry.pack(pady=5)

    status_label = ttk.Label(create_frame, text="", bootstyle=SUCCESS)
    status_label.pack(pady=10)

    def create():
        # Validate pressure_required and flow_rate_required
        pressure_required = pressure_required_entry.get().strip()
        flow_rate_required = flow_rate_required_entry.get().strip()

        # Check if fields are empty
        if not pressure_required or not flow_rate_required:
            Messagebox.show_error("Pressure Required and Flow Rate Required are mandatory fields.", "Validation Error")
            return

        # Check if fields are numeric
        try:
            pressure_required = float(pressure_required)
            flow_rate_required = float(flow_rate_required)
        except ValueError:
            Messagebox.show_error("Pressure Required and Flow Rate Required must be numeric values.", "Validation Error")
            return

        # Check if values are non-negative
        if pressure_required < 0 or flow_rate_required < 0:
            Messagebox.show_error("Pressure Required and Flow Rate Required must be non-negative values.", "Validation Error")
            return

        try:
            with connect_db() as conn:
                cursor = conn.cursor()
                serial = create_pump(
                    cursor,
                    model_entry.get(),
                    config_entry.get(),
                    customer_entry.get(),
                    username,
                    pressure_required=pressure_required,
                    flow_rate_required=flow_rate_required
                )
                create_bom_item(cursor, serial, "Impeller", "IMP-001", 1)
                create_bom_item(cursor, serial, "Motor", "MTR-3.0kW", 1)
                conn.commit()
            status_label.config(text=f"Created S/N: {serial}")
            logger.info(f"GUI: Pump {serial} created by {username}")
            # Refresh the tables in the tabs
            refresh_stores_pumps()
            refresh_all_pumps()
        except Exception as e:
            Messagebox.show_error(f"Failed to create pump: {str(e)}", "Error")
            logger.error(f"Failed to create pump: {str(e)}")

    ttk.Button(create_frame, text="Create Pump", command=create, bootstyle=SUCCESS).pack(pady=20)

    # Tabbed Section: All Pumps and Pumps in Stores
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill=BOTH, expand=True, pady=10)

    # Tab 1: All Pumps
    all_pumps_tab = ttk.Frame(notebook)
    notebook.add(all_pumps_tab, text="All Pumps")
    all_pumps_frame = ttk.LabelFrame(all_pumps_tab, text="All Pumps", padding=10)
    all_pumps_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration", "Created At", "Status", "Pressure Required", "Flow Rate Required")
    all_pumps_tree = ttk.Treeview(all_pumps_frame, columns=columns, show="headings", height=15)
    for col in columns:
        all_pumps_tree.heading(col, text=col, anchor=W)
        all_pumps_tree.column(col, width=150, anchor=W)
    all_pumps_tree.pack(side=LEFT, fill=BOTH, expand=True)

    scrollbar_all = ttk.Scrollbar(all_pumps_frame, orient=VERTICAL, command=all_pumps_tree.yview)
    scrollbar_all.pack(side=RIGHT, fill=Y)
    all_pumps_tree.configure(yscrollcommand=scrollbar_all.set)

    def refresh_all_pumps():
        for item in all_pumps_tree.get_children():
            all_pumps_tree.delete(item)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT serial_number, customer, branch, pump_model, configuration, created_at, status, pressure_required, flow_rate_required
                FROM pumps
            """)
            pumps = cursor.fetchall()
            logger.debug(f"Fetched {len(pumps)} pumps for All Pumps")
            for pump in pumps:
                all_pumps_tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"],
                                                      pump["pump_model"], pump["configuration"], pump["created_at"],
                                                      pump["status"], pump["pressure_required"], pump["flow_rate_required"]))
        logger.info("Refreshed All Pumps table")

    # Initial population of the table
    refresh_all_pumps()

    # Refresh Button for All Pumps
    button_frame_all = ttk.Frame(all_pumps_frame)
    button_frame_all.pack(pady=5)
    ttk.Button(button_frame_all, text="Refresh", command=refresh_all_pumps, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=5)

    # Tab 2: Pumps in Stores
    stores_tab = ttk.Frame(notebook)
    notebook.add(stores_tab, text="Pumps in Stores")
    stores_frame = ttk.LabelFrame(stores_tab, text="Pumps in Stores", padding=10)
    stores_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    stores_tree = ttk.Treeview(stores_frame, columns=columns, show="headings", height=15)
    for col in columns:
        stores_tree.heading(col, text=col, anchor=W)
        stores_tree.column(col, width=150, anchor=W)
    stores_tree.pack(side=LEFT, fill=BOTH, expand=True)

    scrollbar_stores = ttk.Scrollbar(stores_frame, orient=VERTICAL, command=stores_tree.yview)
    scrollbar_stores.pack(side=RIGHT, fill=Y)
    stores_tree.configure(yscrollcommand=scrollbar_stores.set)

    def refresh_stores_pumps():
        for item in stores_tree.get_children():
            stores_tree.delete(item)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT serial_number, customer, branch, pump_model, configuration, created_at, status, pressure_required, flow_rate_required
                FROM pumps WHERE customer = 'Stores'
            """)
            pumps = cursor.fetchall()
            logger.debug(f"Fetched {len(pumps)} pumps for Pumps in Stores")
            for pump in pumps:
                stores_tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"],
                                                   pump["pump_model"], pump["configuration"], pump["created_at"],
                                                   pump["status"], pump["pressure_required"], pump["flow_rate_required"]))
        logger.info("Refreshed Pumps in Stores table")

    # Initial population of the table
    refresh_stores_pumps()

    # Refresh Button for Pumps in Stores
    button_frame_stores = ttk.Frame(stores_frame)
    button_frame_stores.pack(pady=5)
    ttk.Button(button_frame_stores, text="Refresh", command=refresh_stores_pumps, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=5)

    # Logoff Button (Below the tabs)
    ttk.Button(main_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=10)

    # Copyright and Build Number
    ttk.Label(main_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(main_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_pump_originator_gui(root, "testuser", lambda: print("Logout"))
    root.mainloop()