import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
from database import connect_db
import os
from utils.config import get_logger

logger = get_logger("assembler_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
BUILD_NUMBER = "1.0.0"

def show_assembler_dashboard(root, username, role, logout_callback):
    for widget in root.winfo_children():
        widget.destroy()

    root.state('zoomed')
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    header_frame = ttk.Frame(main_frame, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20), ipady=20)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH)
            img_resized = img.resize((int(img.width * 0.75), int(img.height * 0.75)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            logo_label = ttk.Label(header_frame, image=logo)
            logo_label.image = logo
            logo_label.pack(side=RIGHT, padx=10)
        except Exception as e:
            logger.error(f"Assembler logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="View and manage pumps in Assembler status.", font=("Roboto", 12)).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Assembler Pump Inventory", font=("Roboto", 16, "bold")).pack(pady=10)

    pump_list_frame = ttk.LabelFrame(main_frame, text="Pumps in Assembler", padding=10)
    pump_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration", "Received")
    tree = ttk.Treeview(pump_list_frame, columns=columns, show="headings", height=15)
    for col in columns:
        tree.heading(col, text=col, anchor=W)
        tree.column(col, width=150, anchor=W)
    tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar = ttk.Scrollbar(pump_list_frame, orient=VERTICAL, command=tree.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    tree.configure(yscrollcommand=scrollbar.set)

    def refresh_pump_list():
        for item in tree.get_children():
            tree.delete(item)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.serial_number, p.customer, p.branch, p.pump_model, p.configuration,
                       CASE WHEN COUNT(b.pulled_at) = COUNT(b.part_code) THEN 'Yes' ELSE 'No' END AS received
                FROM pumps p
                LEFT JOIN bom_items b ON p.serial_number = b.serial_number
                WHERE p.status = 'Assembler'
                GROUP BY p.serial_number, p.customer, p.branch, p.pump_model, p.configuration
            """)
            for pump in cursor.fetchall():
                tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"],
                                            pump["pump_model"], pump["configuration"], pump["received"]))

    refresh_pump_list()
    tree.bind("<Double-1>", lambda event: show_bom_window(main_frame, tree, username, refresh_pump_list))

    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=10)
    ttk.Button(footer_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

def show_bom_window(parent_frame, tree, username, refresh_callback):
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    serial_number = tree.item(selected[0])["values"][0]
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pumps WHERE serial_number = ?", (serial_number,))
        pump = cursor.fetchone()
        if not pump:
            logger.warning(f"No pump found for serial_number: {serial_number}")
            return
        cursor.execute("SELECT part_name, part_code, quantity, pulled_at FROM bom_items WHERE serial_number = ? AND pulled_at IS NOT NULL", (serial_number,))
        bom_items = cursor.fetchall()
        logger.debug(f"Fetched {len(bom_items)} received BOM items for {serial_number}: {[(item['part_name'], item['part_code']) for item in bom_items]}")

    bom_window = ttk.Toplevel(parent_frame)
    bom_window.title(f"BOM for Pump {serial_number}")
    bom_window.state("zoomed")

    header_frame = ttk.Frame(bom_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH)
            img_resized = img.resize((int(img.width * 0.5), int(img.height * 0.5)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img_resized)
            logo_label = ttk.Label(header_frame, image=logo)
            logo_label.image = logo
            logo_label.pack(side=RIGHT, padx=10)
        except Exception as e:
            logger.error(f"BOM window logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Pump {serial_number}", font=("Roboto", 14, "bold")).pack(anchor=W, padx=10)

    bom_frame = ttk.LabelFrame(bom_window, text="Bill of Materials (Received Items)", padding=10)
    bom_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    canvas = ttk.Canvas(bom_frame)
    scrollbar = ttk.Scrollbar(bom_frame, orient=VERTICAL, command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill=Y)

    # BOM Headers (Removed "Received")
    ttk.Label(scrollable_frame, text="Part Number", font=("Roboto", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Part Name", font=("Roboto", 10, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Quantity", font=("Roboto", 10, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Confirmed", font=("Roboto", 10, "bold")).grid(row=0, column=3, padx=5, pady=5, sticky=W)

    # BOM Items (only "Confirmed" checkbox)
    confirm_vars = []
    for i, item in enumerate(bom_items, start=1):
        ttk.Label(scrollable_frame, text=item["part_code"]).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        ttk.Label(scrollable_frame, text=item["part_name"]).grid(row=i, column=1, padx=5, pady=5, sticky=W)
        ttk.Label(scrollable_frame, text=str(item["quantity"])).grid(row=i, column=2, padx=5, pady=5, sticky=W)

        confirm_var = ttk.BooleanVar(value=False)
        confirm_check = ttk.Checkbutton(scrollable_frame, variable=confirm_var)
        confirm_check.grid(row=i, column=3, padx=5, pady=5)
        confirm_vars.append(confirm_var)

    unpulled_frame = ttk.LabelFrame(bom_window, text="Items Not Pulled", padding=10)
    unpulled_frame.pack(fill=X, padx=10, pady=10)
    unpulled_columns = ("Part Code", "Part Name", "Reason")
    unpulled_tree = ttk.Treeview(unpulled_frame, columns=unpulled_columns, show="headings", height=5)
    for col in unpulled_columns:
        unpulled_tree.heading(col, text=col, anchor=W)
        unpulled_tree.column(col, width=200, anchor=W)
    unpulled_tree.pack(side=LEFT, fill=X, expand=True)
    unpulled_scrollbar = ttk.Scrollbar(unpulled_frame, orient=VERTICAL, command=unpulled_tree.yview)
    unpulled_scrollbar.pack(side=RIGHT, fill=Y)
    unpulled_tree.configure(yscrollcommand=unpulled_scrollbar.set)

    def refresh_unpulled_list():
        for item in unpulled_tree.get_children():
            unpulled_tree.delete(item)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.part_code, b.part_name, COALESCE((
                    SELECT action FROM audit_log 
                    WHERE action LIKE '%Reason for not pulling ' || b.part_code || ' on ' || b.serial_number || '%'
                    ORDER BY timestamp DESC LIMIT 1
                ), 'No reason provided') AS reason
                FROM bom_items b
                WHERE b.serial_number = ? AND b.pulled_at IS NULL
            """, (serial_number,))
            for item in cursor.fetchall():
                reason = item["reason"].replace(f"Reason for not pulling {item['part_code']} on {serial_number}: ", "") if item["reason"].startswith("Reason") else item["reason"]
                unpulled_tree.insert("", END, values=(item["part_code"], item["part_name"], reason))

    refresh_unpulled_list()

    footer_frame = ttk.Frame(bom_window)
    footer_frame.pack(side=BOTTOM, pady=10)
    submit_btn = ttk.Button(footer_frame, text="Submit", bootstyle="success", style="large.TButton", state=DISABLED)
    submit_btn.pack(pady=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    def check_submit_state():
        all_confirmed = all(var.get() for var in confirm_vars)
        logger.debug(f"All confirmed: {all_confirmed}")
        submit_btn.configure(state=NORMAL if all_confirmed else DISABLED)

    def submit_bom():
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pumps SET status = 'Testing' WHERE serial_number = ?", (serial_number,))
            conn.commit()
            logger.info(f"Pump {serial_number} moved to Testing by {username}")
            cursor.execute("SELECT status FROM pumps WHERE serial_number = ?", (serial_number,))
            new_status = cursor.fetchone()["status"]
            logger.debug(f"Post-submit status for {serial_number}: {new_status}")

        refresh_callback()
        bom_window.destroy()

    submit_btn.configure(command=submit_bom)

    for var in confirm_vars:
        var.trace("w", lambda *args: check_submit_state())

    check_submit_state()

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_assembler_dashboard(root, "assembler1", "assembler", lambda: print("Logged off"))
    root.mainloop()