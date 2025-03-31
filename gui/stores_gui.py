import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageTk
from database import get_db_connection, pull_bom_item
import os
from datetime import datetime
import threading
from utils.config import get_logger
from export_utils import send_email, generate_pump_details_table, generate_bom_table

logger = get_logger("stores_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
BUILD_NUMBER = "1.0.0"

def show_stores_dashboard(root, username, role, logout_callback):
    """Display the Stores dashboard for managing pumps to be assembled."""
    root.state('zoomed')
    for widget in root.winfo_children():
        widget.destroy()

    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    header_frame = ttk.Frame(main_frame, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20), ipady=20)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.75), int(Image.open(LOGO_PATH).height * 0.75)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
        except Exception as e:
            logger.error(f"Stores logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Pumps to be Assembled", font=("Roboto", 12)).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Pumps in Stores", font=("Roboto", 16, "bold")).pack(pady=10)

    pump_list_frame = ttk.LabelFrame(main_frame, text="Pumps in Stores", padding=10)
    pump_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    columns = ("Serial Number", "Assembly Part Number", "Customer", "Branch", "Pump Model", "Configuration", "Created At")
    tree = ttk.Treeview(pump_list_frame, columns=columns, show="headings", height=15)
    for col in columns:
        tree.heading(col, text=col, anchor=W)
        tree.column(col, width=150, anchor=W)
    tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar = ttk.Scrollbar(pump_list_frame, orient=VERTICAL, command=tree.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    tree.configure(yscrollcommand=scrollbar.set)

    def refresh_pump_list():
        """Refresh the list of pumps in Stores."""
        tree.delete(*tree.get_children())
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT serial_number, assembly_part_number, customer, branch, pump_model, configuration, created_at
                    FROM pumps WHERE status = 'Stores'
                """)
                for pump in cursor.fetchall():
                    # pump is a tuple: (serial_number, assembly_part_number, customer, branch, pump_model, configuration, created_at)
                    tree.insert("", END, values=(pump[0], pump[1] or "N/A", pump[2], pump[3], pump[4], pump[5], pump[6]))
            logger.info("Refreshed Pumps in Stores table")
        except Exception as e:
            logger.error(f"Failed to refresh pump list: {str(e)}")
            Messagebox.show_error("Error", f"Failed to load pumps: {str(e)}")

    refresh_pump_list()
    tree.bind("<Double-1>", lambda event: show_bom_window(main_frame, tree, username, refresh_pump_list))

    ttk.Button(main_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=10)
    ttk.Label(main_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(main_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

def show_bom_window(parent_frame, tree, username, refresh_callback):
    """Display and manage BOM for a selected pump with mouse wheel scrolling."""
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    serial_number = tree.item(selected[0])["values"][0]
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pumps WHERE serial_number = ?", (serial_number,))
            # Convert tuple to dict using column names
            columns = [desc[0] for desc in cursor.description]
            pump_tuple = cursor.fetchone()
            if not pump_tuple:
                logger.warning(f"No pump found for serial_number: {serial_number}")
                Messagebox.show_error("Error", f"Pump {serial_number} not found")
                return
            pump = dict(zip(columns, pump_tuple))
            cursor.execute("SELECT part_name, part_code, quantity, pulled_at FROM bom_items WHERE serial_number = ?", (serial_number,))
            bom_items = cursor.fetchall()
            cursor.execute("SELECT username, email FROM users WHERE username = ?", (pump["requested_by"],))
            # originator is a tuple: (username, email)
            originator = cursor.fetchone()
    except Exception as e:
        logger.error(f"Failed to load BOM data: {str(e)}")
        Messagebox.show_error("Error", f"Failed to load BOM: {str(e)}")
        return

    bom_window = ttk.Toplevel(parent_frame)
    bom_window.title(f"BOM for Pump {serial_number}")
    bom_window.state("zoomed")

    header_frame = ttk.Frame(bom_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.5), int(Image.open(LOGO_PATH).height * 0.5)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
        except Exception as e:
            logger.error(f"BOM window logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Pump {serial_number}", font=("Roboto", 14, "bold")).pack(anchor=W, padx=10)

    bom_frame = ttk.LabelFrame(bom_window, text="Bill of Materials", padding=10)
    bom_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    canvas = ttk.Canvas(bom_frame)
    scrollbar = ttk.Scrollbar(bom_frame, orient=VERTICAL, command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill=Y)

    # Enable mouse wheel scrolling, bound only to the canvas
    def on_mouse_wheel(event):
        if canvas.winfo_exists():  # Prevent scroll if canvas is destroyed
            # Windows uses delta (positive = up, negative = down), Linux/macOS use Button-4 (up) and Button-5 (down)
            if event.delta > 0 or event.num == 4:  # Scroll up
                canvas.yview_scroll(-1, "units")
            elif event.delta < 0 or event.num == 5:  # Scroll down
                canvas.yview_scroll(1, "units")

    # Bind mouse wheel events to the canvas only (not globally)
    canvas.bind("<MouseWheel>", on_mouse_wheel)  # Windows
    canvas.bind("<Button-4>", on_mouse_wheel)    # Linux/macOS scroll up
    canvas.bind("<Button-5>", on_mouse_wheel)    # Linux/macOS scroll down

    # Clean up bindings on window close
    def on_close():
        try:
            if canvas.winfo_exists():
                canvas.unbind("<MouseWheel>")
                canvas.unbind("<Button-4>")
                canvas.unbind("<Button-5>")
            bom_window.destroy()
        except Exception as e:
            logger.debug(f"Minor error during BOM window close: {str(e)}")

    bom_window.protocol("WM_DELETE_WINDOW", on_close)

    headers = ["Part Number", "Part Name", "Quantity", "Pulled", "Reason"]
    for col, header in enumerate(headers):
        ttk.Label(scrollable_frame, text=header, font=("Roboto", 10, "bold")).grid(row=0, column=col, padx=5, pady=5, sticky=W)

    check_vars = []
    reason_entries = []
    for i, item in enumerate(bom_items, start=1):
        # item is a tuple: (part_name, part_code, quantity, pulled_at)
        ttk.Label(scrollable_frame, text=item[1]).grid(row=i, column=0, padx=5, pady=5, sticky=W)  # part_code
        ttk.Label(scrollable_frame, text=item[0]).grid(row=i, column=1, padx=5, pady=5, sticky=W)  # part_name
        ttk.Label(scrollable_frame, text=str(item[2])).grid(row=i, column=2, padx=5, pady=5, sticky=W)  # quantity
        var = ttk.BooleanVar(value=bool(item[3]))  # pulled_at
        check = ttk.Checkbutton(scrollable_frame, variable=var, state=DISABLED if item[3] else NORMAL)
        check.grid(row=i, column=3, padx=5, pady=5)
        check_vars.append((item[1], var))  # part_code
        entry = ttk.Entry(scrollable_frame, width=40, state=NORMAL if not var.get() else DISABLED)
        entry.grid(row=i, column=4, padx=5, pady=5, sticky=W)
        reason_entries.append((item[1], entry))  # part_code
        var.trace("w", lambda *args, v=var, e=entry: [e.configure(state=NORMAL if not v.get() else DISABLED), e.delete(0, END) if v.get() else None, check_submit_state()])

    footer_frame = ttk.Frame(bom_window)
    footer_frame.pack(side=BOTTOM, pady=10)
    submit_btn = ttk.Button(footer_frame, text="Submit", bootstyle="success", style="large.TButton", state=DISABLED)
    submit_btn.pack(pady=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    def check_submit_state():
        """Enable submit button only if all items are pulled or have reasons."""
        all_complete = all(var.get() or next(e.get().strip() for pc, e in reason_entries if pc == part_code) for part_code, var in check_vars)
        submit_btn.configure(state=NORMAL if all_complete else DISABLED)

    def submit_bom():
        """Submit BOM, update pump status, and notify originator."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                bom_items_list = []
                for part_code, var in check_vars:
                    pulled = var.get()
                    reason = next(e.get().strip() for pc, e in reason_entries if pc == part_code)
                    if pulled and not next(item[3] for item in bom_items if item[1] == part_code):  # pulled_at
                        pull_bom_item(cursor, serial_number, part_code, username)
                    part_name = next(item[0] for item in bom_items if item[1] == part_code)  # part_name
                    quantity = next(item[2] for item in bom_items if item[1] == part_code)  # quantity
                    bom_items_list.append({"part_name": part_name, "part_code": part_code, "quantity": quantity, "pulled": "Yes" if pulled else "No", "reason": reason})
                    if reason:
                        cursor.execute("INSERT INTO audit_log (timestamp, username, action) VALUES (?, ?, ?)",
                                       (datetime.now(), username, f"Reason for not pulling {part_code} on {serial_number}: {reason}"))
                cursor.execute("UPDATE pumps SET status = 'Assembler' WHERE serial_number = ?", (serial_number,))
                conn.commit()
                logger.info(f"BOM submitted for {serial_number} by {username}, moved to Assembler")

                try:
                    with open("bom_print.txt", "w") as f:
                        f.write(f"BOM for Pump {serial_number}:\n" + "\n".join(f"Part: {item['part_name']} ({item['part_code']}), Qty: {item['quantity']}, Pulled: {item['pulled']}, Reason: {item['reason']}" for item in bom_items_list))
                    os.startfile("bom_print.txt", "print")
                    logger.info(f"BOM printed for {serial_number}")
                except Exception as e:
                    logger.error(f"Failed to print BOM: {str(e)}")

                if originator:
                    pump_data = {k: pump.get(k, "") for k in ["serial_number", "assembly_part_number", "customer", "branch", "pump_model", "configuration", "impeller_size", "connection_type", "pressure_required", "flow_rate_required", "custom_motor", "flush_seal_housing"]}
                    threading.Thread(target=send_email, args=(originator[1], f"Pump {serial_number} Moved to Assembly", f"Dear {originator[0]},",
                                                              f"<p>All items for pump {serial_number} pulled, moved to Assembly.</p><h3 style='color: #34495e;'>Pump Details</h3>{generate_pump_details_table(pump_data)}{generate_bom_table(bom_items_list)}",
                                                              "Regards,<br>Stores Team"), daemon=True).start()
                else:
                    logger.warning(f"No originator found for pump {serial_number}")

            refresh_callback()
            bom_window.destroy()
        except Exception as e:
            logger.error(f"BOM submission failed: {str(e)}")
            Messagebox.show_error("Error", f"Failed to submit BOM: {str(e)}")

    submit_btn.configure(command=submit_bom)
    check_submit_state()
    bom_window.after(100, check_submit_state)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_stores_dashboard(root, "testuser", "Stores", lambda: print("Logout"))
    root.mainloop()