import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageTk
from database import get_db_connection, pull_bom_item
import os
import sys
from datetime import datetime
import threading
from utils.config import get_logger
from export_utils import send_email, generate_pump_details_table, generate_bom_table

# Initialize logger before using it
logger = get_logger("stores_gui")

# Try to import pyperclip, with a fallback if not available
# Suppress the import warning if pyperclip is installed but not recognized by IntelliSense
# pylint: disable=import-error
try:
    import pyperclip
    PYCLIP_AVAILABLE = True
except ImportError:
    logger.warning("pyperclip module not found. Copy functionality will be disabled.")
    PYCLIP_AVAILABLE = False

# Determine the base directory for bundled resources
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"

# Define config paths
if getattr(sys, 'frozen', False):
    # Use AppData for persistent config in installed app
    CONFIG_DIR = os.path.join(os.getenv('APPDATA'), "GuthPumpRegistry")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
    DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
else:
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
    DEFAULT_CONFIG_PATH = CONFIG_PATH

LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
COPY_ICON_PATH = os.path.join(BASE_DIR, "assets", "copy_icon.png")  # Ensure you have a small copy icon image
BUILD_NUMBER = "1.0.0"

class CustomTooltip:
    """Custom tooltip class for widgets."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height()
        self.tooltip_window = ttk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        ttk.Label(self.tooltip_window, text=self.text, background="lightyellow", relief="solid", borderwidth=1, font=("Roboto", 10)).pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

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
    # Add description under the heading
    ttk.Label(header_frame, text="This dashboard helps you manage pumps in Stores. Pull items from the Bill of Materials to send pumps to Assembly.",
              font=("Roboto", 10), wraplength=600).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Pumps in Stores", font=("Roboto", 16, "bold")).pack(pady=10)

    pump_list_frame = ttk.LabelFrame(main_frame, text="Pumps in Stores", padding=10)
    pump_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    columns = ("Serial Number", "Assembly Part Number", "Customer", "Branch", "Created At")
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
                    SELECT serial_number, assembly_part_number, customer, branch, created_at
                    FROM pumps WHERE status = 'Stores'
                """)
                for pump in cursor.fetchall():
                    # pump is a tuple: (serial_number, assembly_part_number, customer, branch, created_at)
                    tree.insert("", END, values=(pump[0], pump[1] or "N/A", pump[2], pump[3], pump[4]))
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

    # Load copy icon if available
    copy_icon = None
    if os.path.exists(COPY_ICON_PATH):
        try:
            img = Image.open(COPY_ICON_PATH).resize((16, 16), Image.Resampling.LANCZOS)
            copy_icon = ImageTk.PhotoImage(img)
        except Exception as e:
            logger.error(f"Failed to load copy icon: {str(e)}")
            copy_icon = None

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

    # Header with Serial Number, Assembly Part Number, Pump Model, and Description (stacked vertically)
    header_info_frame = ttk.Frame(header_frame)
    header_info_frame.pack(anchor=W, padx=10)

    # Tooltip message for Serial Number and Assembly Part Number
    tooltip_message = "Copy this into Sage for pump assembly. Complete the Bill of Materials here only after the pump assembly is done in Sage and items are booked out."

    # Serial Number with Copy Button
    serial_frame = ttk.Frame(header_info_frame)
    serial_frame.pack(anchor=W, pady=5)
    ttk.Label(serial_frame, text="Serial Number: ", font=("Roboto", 14)).pack(side=LEFT)  # Not bold
    serial_value_label = ttk.Label(serial_frame, text=serial_number, font=("Roboto", 14, "bold"))  # Bold
    serial_value_label.pack(side=LEFT)
    CustomTooltip(serial_value_label, tooltip_message)  # Add tooltip to the value
    if PYCLIP_AVAILABLE:
        def copy_serial():
            pyperclip.copy(serial_number.replace(".", ""))
        if copy_icon:
            ttk.Button(serial_frame, image=copy_icon, command=copy_serial, style="link.TButton").pack(side=LEFT, padx=5)
            serial_frame.copy_icon = copy_icon  # Keep reference
        else:
            ttk.Button(serial_frame, text="Copy", command=copy_serial, style="link.TButton").pack(side=LEFT, padx=5)

    # Assembly Part Number with Copy Button
    assembly_part_number = pump.get("assembly_part_number", "N/A")
    assembly_frame = ttk.Frame(header_info_frame)
    assembly_frame.pack(anchor=W, pady=5)
    ttk.Label(assembly_frame, text="Assembly Part Number: ", font=("Roboto", 14)).pack(side=LEFT)  # Not bold
    assembly_value_label = ttk.Label(assembly_frame, text=assembly_part_number, font=("Roboto", 14, "bold"))  # Bold
    assembly_value_label.pack(side=LEFT)
    CustomTooltip(assembly_value_label, tooltip_message)  # Add tooltip to the value
    if PYCLIP_AVAILABLE:
        def copy_assembly():
            pyperclip.copy(assembly_part_number.replace(".", ""))
        if copy_icon:
            ttk.Button(assembly_frame, image=copy_icon, command=copy_assembly, style="link.TButton").pack(side=LEFT, padx=5)
            assembly_frame.copy_icon = copy_icon  # Keep reference
        else:
            ttk.Button(assembly_frame, text="Copy", command=copy_assembly, style="link.TButton").pack(side=LEFT, padx=5)

    # Pump Model
    pump_model_frame = ttk.Frame(header_info_frame)
    pump_model_frame.pack(anchor=W, pady=5)
    ttk.Label(pump_model_frame, text="Pump Model: ", font=("Roboto", 14)).pack(side=LEFT)  # Not bold
    ttk.Label(pump_model_frame, text=pump['pump_model'], font=("Roboto", 14, "bold")).pack(side=LEFT)  # Bold

    # Short Description
    ttk.Label(header_frame, text="Pull items from the Bill of Materials below. Provide a reason for any items not pulled before submitting to Assembly.",
              font=("Roboto", 10), wraplength=600).pack(anchor=W, padx=10, pady=(10, 0))

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
            if event.delta > 0 or event.num == 4:  # Scroll up
                canvas.yview_scroll(-1, "units")
            elif event.delta < 0 or event.num == 5:  # Scroll down
                canvas.yview_scroll(1, "units")

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

    # Notes Section
    notes_frame = ttk.LabelFrame(bom_window, text="Notes", padding=10)
    notes_frame.pack(fill=BOTH, expand=False, padx=10, pady=10)
    notes_text = ttk.Text(notes_frame, height=5, width=80, font=("Roboto", 10))
    notes_text.pack(fill=BOTH, expand=True, padx=5, pady=5)

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
                
                # Get the notes from the text field
                notes = notes_text.get("1.0", ttk.END).strip()
                
                # Update the pumps table with the notes and status
                cursor.execute("UPDATE pumps SET status = ?, notes = ? WHERE serial_number = ?", ("Assembler", notes, serial_number))
                conn.commit()
                logger.info(f"BOM submitted for {serial_number} by {username}, moved to Assembler")

                # Print BOM to a temporary file
                temp_dir = os.path.join(os.getenv('TEMP', os.path.join(BASE_DIR, "temp")))
                os.makedirs(temp_dir, exist_ok=True)
                bom_print_path = os.path.join(temp_dir, f"bom_print_{serial_number}.txt")
                try:
                    with open(bom_print_path, "w") as f:
                        f.write(f"BOM for Pump {serial_number}:\n" + "\n".join(f"Part: {item['part_name']} ({item['part_code']}), Qty: {item['quantity']}, Pulled: {item['pulled']}, Reason: {item['reason']}" for item in bom_items_list))
                    os.startfile(bom_print_path, "print")
                    logger.info(f"BOM printed for {serial_number} to {bom_print_path}")
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