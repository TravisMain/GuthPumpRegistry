import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from database import connect_db, insert_user, update_user, delete_user, get_all_users, get_all_pumps, get_audit_log
from utils.config import get_logger

logger = get_logger("admin_gui")

def show_admin_gui(root, username):
    frame = ttk.Frame(root)
    frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

    ttk.Label(frame, text="Admin Panel", font=("Helvetica", 16, "bold")).pack(pady=10)

    notebook = ttk.Notebook(frame)
    notebook.pack(fill=BOTH, expand=True)

    # User Management Tab
    user_tab = ttk.Frame(notebook)
    notebook.add(user_tab, text="User Management")

    ttk.Label(user_tab, text="Add/Edit User").pack(pady=5)
    ttk.Label(user_tab, text="Username:").pack()
    username_entry = ttk.Entry(user_tab)
    username_entry.pack(pady=5)

    ttk.Label(user_tab, text="Password (leave blank to keep unchanged):").pack()
    password_entry = ttk.Entry(user_tab, show="*")
    password_entry.pack(pady=5)

    ttk.Label(user_tab, text="Role:").pack()
    role_var = ttk.StringVar(value="Pump Originator")
    role_dropdown = ttk.Combobox(user_tab, textvariable=role_var, 
                                 values=["Pump Originator", "Stores", "Assembler", "Testing", "Admin"])
    role_dropdown.pack(pady=5)

    ttk.Label(user_tab, text="Name:").pack()
    name_entry = ttk.Entry(user_tab)
    name_entry.pack(pady=5)

    ttk.Label(user_tab, text="Surname:").pack()
    surname_entry = ttk.Entry(user_tab)
    surname_entry.pack(pady=5)

    ttk.Label(user_tab, text="Email:").pack()
    email_entry = ttk.Entry(user_tab)
    email_entry.pack(pady=5)

    def add_user():
        with connect_db() as conn:
            cursor = conn.cursor()
            try:
                insert_user(cursor, username_entry.get(), password_entry.get(), role_var.get(),
                           name_entry.get(), surname_entry.get(), email_entry.get())
                conn.commit()
                ttk.Label(user_tab, text="User added!", bootstyle=SUCCESS).pack(pady=5)
                refresh_users()
            except sqlite3.IntegrityError:
                ttk.Label(user_tab, text="Username already exists", bootstyle=DANGER).pack(pady=5)

    def edit_user():
        with connect_db() as conn:
            cursor = conn.cursor()
            update_user(cursor, username_entry.get(), password_entry.get() or None, role_var.get(),
                       name_entry.get(), surname_entry.get(), email_entry.get())
            conn.commit()
            ttk.Label(user_tab, text="User updated!", bootstyle=SUCCESS).pack(pady=5)
            refresh_users()

    def delete_user():
        if ttk.dialogs.Messagebox.yesno("Confirm", f"Delete {username_entry.get()}?"):
            with connect_db() as conn:
                cursor = conn.cursor()
                delete_user(cursor, username_entry.get())
                conn.commit()
                ttk.Label(user_tab, text="User deleted!", bootstyle=SUCCESS).pack(pady=5)
                refresh_users()

    ttk.Button(user_tab, text="Add User", command=add_user, bootstyle=SUCCESS).pack(side=LEFT, padx=5, pady=10)
    ttk.Button(user_tab, text="Edit User", command=edit_user, bootstyle=INFO).pack(side=LEFT, padx=5, pady=10)
    ttk.Button(user_tab, text="Delete User", command=delete_user, bootstyle=DANGER).pack(side=LEFT, padx=5, pady=10)

    user_tree = ttk.Treeview(user_tab, columns=("Username", "Role", "Name", "Surname", "Email"), show="headings")
    user_tree.heading("Username", text="Username")
    user_tree.heading("Role", text="Role")
    user_tree.heading("Name", text="Name")
    user_tree.heading("Surname", text="Surname")
    user_tree.heading("Email", text="Email")
    user_tree.pack(fill=BOTH, expand=True, pady=10)

    def refresh_users():
        for item in user_tree.get_children():
            user_tree.delete(item)
        with connect_db() as conn:
            cursor = conn.cursor()
            users = get_all_users(cursor)
            for user in users:
                user_tree.insert("", END, values=(user["username"], user["role"], user["name"], user["surname"], user["email"]))

    def on_user_select(event):
        selected = user_tree.selection()
        if selected:
            item = user_tree.item(selected[0])
            username_entry.delete(0, END)
            username_entry.insert(0, item["values"][0])
            role_var.set(item["values"][1])
            name_entry.delete(0, END)
            name_entry.insert(0, item["values"][2] or "")
            surname_entry.delete(0, END)
            surname_entry.insert(0, item["values"][3] or "")
            email_entry.delete(0, END)
            email_entry.insert(0, item["values"][4] or "")

    user_tree.bind("<<TreeviewSelect>>", on_user_select)
    refresh_users()

    # Pump Status Report Tab
    pump_tab = ttk.Frame(notebook)
    notebook.add(pump_tab, text="Pump Status Report")

    pump_tree = ttk.Treeview(pump_tab, columns=("Serial", "Model", "Customer", "Status", "Result", "Test Date"), show="headings")
    pump_tree.heading("Serial", text="Serial Number")
    pump_tree.heading("Model", text="Model")
    pump_tree.heading("Customer", text="Customer")
    pump_tree.heading("Status", text="Status")
    pump_tree.heading("Result", text="Test Result")
    pump_tree.heading("Test Date", text="Test Date")
    pump_tree.pack(fill=BOTH, expand=True, pady=10)

    with connect_db() as conn:
        cursor = conn.cursor()
        pumps = get_all_pumps(cursor)
        for pump in pumps:
            pump_tree.insert("", END, values=(pump["serial_number"], pump["pump_model"], pump["customer"],
                                             pump["status"], pump["test_result"], pump["test_date"]))

    # Audit Log Report Tab
    audit_tab = ttk.Frame(notebook)
    notebook.add(audit_tab, text="Audit Log")

    audit_tree = ttk.Treeview(audit_tab, columns=("Timestamp", "Username", "Action"), show="headings")
    audit_tree.heading("Timestamp", text="Timestamp")
    audit_tree.heading("Username", text="Username")
    audit_tree.heading("Action", text="Action")
    audit_tree.pack(fill=BOTH, expand=True, pady=10)

    with connect_db() as conn:
        cursor = conn.cursor()
        logs = get_audit_log(cursor)
        for log in logs:
            audit_tree.insert("", END, values=(log["timestamp"], log["username"], log["action"]))