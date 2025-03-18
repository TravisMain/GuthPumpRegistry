import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
from database import connect_db, pull_bom_item
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from utils.config import get_logger

logger = get_logger("stores_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
BUILD_NUMBER = "1.0.0"

def show_stores_dashboard(root, username, role, logout_callback):
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
            logger.error(f"Stores logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Pumps to be Assembled", font=("Roboto", 12)).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Pumps to be Assembled", font=("Roboto", 16, "bold")).pack(pady=10)  # Updated heading

    # Pumps in Stores (to be assembled) Table
    pump_list_frame = ttk.LabelFrame(main_frame, text="Pumps in Stores", padding=10)
    pump_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration", "Created At")
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
                SELECT serial_number, customer, branch, pump_model, configuration, created_at
                FROM pumps WHERE status = 'Stores'
            """)
            for pump in cursor.fetchall():
                tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"],
                                            pump["pump_model"], pump["configuration"], pump["created_at"]))

    refresh_pump_list()
    tree.bind("<Double-1>", lambda event: show_bom_window(main_frame, tree, username, refresh_pump_list))

    # All Pumps in Stores Table
    all_pumps_frame = ttk.LabelFrame(main_frame, text="All Pumps in Stores", padding=10)
    all_pumps_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    all_columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration", "Created At", "Status")
    all_tree = ttk.Treeview(all_pumps_frame, columns=all_columns, show="headings", height=15)
    for col in all_columns:
        all_tree.heading(col, text=col, anchor=W)
        all_tree.column(col, width=120, anchor=W)  # Adjusted width for extra column
    all_tree.pack(side=LEFT, fill=BOTH, expand=True)
    all_scrollbar = ttk.Scrollbar(all_pumps_frame, orient=VERTICAL, command=all_tree.yview)
    all_scrollbar.pack(side=RIGHT, fill=Y)
    all_tree.configure(yscrollcommand=all_scrollbar.set)

    def refresh_all_pumps_list():
        for item in all_tree.get_children():
            all_tree.delete(item)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT serial_number, customer, branch, pump_model, configuration, created_at, status
                FROM pumps WHERE customer = 'Stores'
            """)
            for pump in cursor.fetchall():
                all_tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"],
                                                pump["pump_model"], pump["configuration"], pump["created_at"], pump["status"]))

    refresh_all_pumps_list()
    all_tree.bind("<Double-1>", lambda event: show_bom_window(main_frame, all_tree, username, refresh_all_pumps_list))

    ttk.Button(main_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=10)
    ttk.Label(main_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(pady=(5, 0))
    ttk.Label(main_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

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
        cursor.execute("SELECT part_name, part_code, quantity, pulled_at FROM bom_items WHERE serial_number = ?", (serial_number,))
        bom_items = cursor.fetchall()
        logger.debug(f"Fetched {len(bom_items)} BOM items for {serial_number}: {[(item['part_name'], item['part_code']) for item in bom_items]}")
        cursor.execute("SELECT username, email FROM users WHERE username = ?", (pump["requested_by"],))
        originator = cursor.fetchone()

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

    ttk.Label(scrollable_frame, text="Part Number", font=("Roboto", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Part Name", font=("Roboto", 10, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Quantity", font=("Roboto", 10, "bold")).grid(row=0, column=2, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Pulled", font=("Roboto", 10, "bold")).grid(row=0, column=3, padx=5, pady=5, sticky=W)
    ttk.Label(scrollable_frame, text="Reason", font=("Roboto", 10, "bold")).grid(row=0, column=4, padx=5, pady=5, sticky=W)

    check_vars = []
    reason_entries = []
    for i, item in enumerate(bom_items, start=1):
        ttk.Label(scrollable_frame, text=item["part_code"]).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        ttk.Label(scrollable_frame, text=item["part_name"]).grid(row=i, column=1, padx=5, pady=5, sticky=W)
        ttk.Label(scrollable_frame, text=str(item["quantity"])).grid(row=i, column=2, padx=5, pady=5, sticky=W)

        var = ttk.BooleanVar(value=item["pulled_at"] is not None)
        check = ttk.Checkbutton(scrollable_frame, variable=var, state=DISABLED if item["pulled_at"] else NORMAL)
        check.grid(row=i, column=3, padx=5, pady=5)
        check_vars.append((item["part_code"], var))

        entry = ttk.Entry(scrollable_frame, width=40)
        entry.grid(row=i, column=4, padx=5, pady=5, sticky=W)
        entry.configure(state=NORMAL if not var.get() else DISABLED)
        reason_entries.append((item["part_code"], entry))

        def toggle_reason(*args, v=var, e=entry):
            e.configure(state=NORMAL if not v.get() else DISABLED)
            if v.get():
                e.delete(0, END)
            check_submit_state()

        var.trace("w", toggle_reason)

    # Footer Frame for Submit, Copyright, Build Number
    footer_frame = ttk.Frame(bom_window)
    footer_frame.pack(side=BOTTOM, pady=10)

    submit_btn = ttk.Button(footer_frame, text="Submit", bootstyle="success", style="large.TButton", state=DISABLED)
    submit_btn.pack(pady=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    def check_submit_state():
        all_complete = True
        for part_code, var in check_vars:
            pulled = var.get()
            reason = next(e.get().strip() for pc, e in reason_entries if pc == part_code)
            logger.debug(f"Item {part_code}: pulled={pulled}, reason='{reason}'")
            if not pulled and not reason:
                all_complete = False
                logger.debug(f"Item {part_code} blocks submit: not pulled and no reason")
                break
        logger.debug(f"All complete: {all_complete}")
        submit_btn.configure(state=NORMAL if all_complete else DISABLED)

    def submit_bom():
        with connect_db() as conn:
            cursor = conn.cursor()
            bom_text = f"BOM for Pump {serial_number}:\n"
            for part_code, var in check_vars:
                pulled = var.get()
                reason = next(e.get().strip() for pc, e in reason_entries if pc == part_code)
                if pulled and not next(item["pulled_at"] for item in bom_items if item["part_code"] == part_code):
                    pull_bom_item(cursor, serial_number, part_code, username)
                bom_text += f"Part: {next(item['part_name'] for item in bom_items if item['part_code'] == part_code)} ({part_code}), Qty: {next(item['quantity'] for item in bom_items if item['part_code'] == part_code)}, Pulled: {'Yes' if pulled else 'No'}, Reason: {reason}\n"
                if reason:
                    cursor.execute("INSERT INTO audit_log (timestamp, username, action) VALUES (?, ?, ?)",
                                  (datetime.now(), username, f"Reason for not pulling {part_code} on {serial_number}: {reason}"))
            cursor.execute("UPDATE pumps SET status = 'Assembler' WHERE serial_number = ?", (serial_number,))
            conn.commit()
            logger.info(f"BOM submitted for {serial_number} by {username}, moved to Assembler")
            cursor.execute("SELECT status FROM pumps WHERE serial_number = ?", (serial_number,))
            new_status = cursor.fetchone()["status"]
            logger.debug(f"Post-submit status for {serial_number}: {new_status}")

            try:
                with open("bom_print.txt", "w") as f:
                    f.write(bom_text)
                os.startfile("bom_print.txt", "print")
                logger.info(f"BOM printed for {serial_number}")
            except Exception as e:
                logger.error(f"Failed to print BOM: {str(e)}")

            if originator:
                try:
                    msg = MIMEText(f"Dear {originator['username']},\n\nAll items have been pulled from stock for pump {serial_number}:\n\n{bom_text}\n\nDetails:\n- Model: {pump['pump_model']}\n- Config: {pump['configuration']}\n- Customer: {pump['customer']}\n- Branch: {pump['branch']}\n\nRegards,\nStores Team")
                    msg["Subject"] = f"Pump {serial_number} Stock Pulled"
                    msg["From"] = "stores@guthpumps.example.com"
                    msg["To"] = originator["email"]
                    with smtplib.SMTP("smtp.example.com", 587) as server:
                        server.login("your_email", "your_password")
                        server.send_message(msg)
                    logger.info(f"Email sent to {originator['email']} for {serial_number}")
                except Exception as e:
                    logger.error(f"Failed to send email: {str(e)}")
            else:
                logger.warning(f"No originator found for pump {serial_number}")

        refresh_callback()  # Refresh the dashboard list
        bom_window.destroy()

    submit_btn.configure(command=submit_bom)
    check_submit_state()
    bom_window.after(100, check_submit_state)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_stores_dashboard(root, "testuser", "Stores", lambda: print("Logout"))
    root.mainloop()