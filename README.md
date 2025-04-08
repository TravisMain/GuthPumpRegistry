markdown
# Guth Pump Registry

The Guth Pump Registry is a desktop application designed to manage the lifecycle of pump assemblies at Guth South Africa. It provides a user-friendly interface for creating, tracking, and approving pump assemblies, integrating with a SQL Server database to store pump details, Bills of Materials (BOM), user accounts, and audit logs. Built with Python and `ttkbootstrap`, it supports multiple user roles and generates PDF notifications and email alerts for key workflow events.

## Features

- **Role-Based Access**:
  - **Pump Originator**: Create new pump assemblies and view status.
  - **Stores**: Manage BOM item pulling for assembly.
  - **Assembler/Tester**: Assemble pumps, perform tests, and submit for approval.
  - **Approval**: Approve or reject tested pumps.
  - **Admin**: Configure settings, manage users, and oversee the system.

- **Pump Management**:
  - Generate unique serial numbers (e.g., `5101 001 - 25`) based on model, configuration, and year.
  - Track pump status: Stores → Assembler → Testing → Pending Approval → Completed.
  - Store pump details (model, configuration, customer, etc.) and test data.

- **Bill of Materials (BOM)**:
  - Automatically populate BOM items from `bom.json` when creating pumps.
  - Mark items as pulled and log reasons for non-pulled items.

- **Notifications**:
  - Generate PDF reports for pump creation, assembly, testing, and approval.
  - Send email notifications with attachments to relevant stakeholders (e.g., Stores team).

- **Database Integration**:
  - Uses SQL Server via `pyodbc` with a singleton connection pool.
  - Stores pumps, BOM items, users, and audit logs with indexing for performance.

- **User Interface**:
  - Modern GUI with `ttkbootstrap` (flatly theme) and custom styles (`styles.py`).
  - Features include tabbed views, tooltips, and consistent typography (Roboto font).

## Prerequisites

- **Python 3.8+**: Required to run the application.
- **SQL Server**: GuthPumpRegistry database (create manually or via `database.py`).
- **ODBC Driver**: Install "ODBC Driver 17 for SQL Server" for database connectivity.
- **Dependencies**: Install via `requirements.txt`:
  ```bash
  pip install ttkbootstrap pyodbc bcrypt reportlab pillow
Installation

    Clone the Repository:
    bash

git clone https://github.com/yourusername/guth-pump-registry.git
cd guth-pump-registry
Install Dependencies:
bash
pip install -r requirements.txt
Configure Database:

    Create a SQL Server database named GuthPumpRegistry.
    Update config.json with your connection string:
    json

{
  "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=your_server;DATABASE=GuthPumpRegistry;Trusted_Connection=yes;"
}
Run database.py to initialize tables and insert test data:
bash

    python database.py

Build Executable (Optional):

    Use PyInstaller:
    bash

pyinstaller base_gui.spec
Update base_gui.spec to include assets:
python

        datas=[('assets/logo.png', 'assets'), ('assets/bom.json', 'assets'), ('assets/pump_options.json', 'assets'), ('assets/assembly_part_numbers.json', 'assets'), ('config.json', '.')]
        Compile with Inno Setup (see setup.iss).

Usage

    Run the Application:
        Development:
        bash

        python src/base_gui.py
        Installed: Launch GuthPumpRegistry.exe from the installation directory.
    Login:
        Use test credentials (e.g., admin1/password) or register a new user.
        Roles determine the dashboard displayed.
    Key Actions:
        Pump Originator: Create pumps, view all pumps or those in Stores.
        Stores: Pull BOM items for assembly.
        Assembler/Tester: Assemble and test pumps, submit for approval.
        Approval: Approve/reject pumps.
        Admin: Manage users, SMTP settings, and document paths.
    Notifications:
        PDFs are saved to config-driven paths (e.g., AppData/GuthPumpRegistry/notifications).
        Emails require SMTP settings in config.json (e.g., Gmail).

Configuration

    config.json:
    json

    {
      "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=your_server;DATABASE=GuthPumpRegistry;Trusted_Connection=yes;",
      "document_dirs": {
        "notifications": "C:/Custom/Path/Notifications",
        "certificates": "C:/Custom/Path/Certificates",
        "boms": "C:/Custom/Path/BOMs",
        "confirmations": "C:/Custom/Path/Confirmations"
      },
      "email_settings": {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": "587",
        "smtp_username": "your_email@gmail.com",
        "smtp_password": "your_app_password",
        "sender_email": "your_email@gmail.com",
        "use_tls": true
      }
    }
        Update paths and SMTP settings via the Admin GUI.
    bom.json: Defines BOM items for each pump model/configuration.

Project Structure
text
guth-pump-registry/
├── assets/
│   ├── bom.json              # BOM definitions
│   ├── logo.png             # Company logo
│   ├── pump_options.json    # Pump model/config options
│   └── assembly_part_numbers.json  # Assembly part numbers
├── gui/
│   ├── base_gui.py          # Main entry point
│   ├── login_gui.py         # Login screen
│   ├── register_gui.py      # Registration screen
│   ├── pump_originator.py   # Pump Originator GUI
│   ├── admin_gui.py         # Admin GUI
│   ├── stores_gui.py        # Stores GUI
│   ├── combined_assembler_tester_gui.py  # Assembler/Tester GUI
│   ├── approval_gui.py      # Approval GUI
│   └── styles.py            # Custom styles
├── utils/
│   ├── config.py            # Logging setup
│   ├── serial_utils.py      # Serial number generation
│   ├── bom_utils.py         # BOM utilities (optional)
│   └── doc_utils.py         # PDF/email utilities (optional)
├── database.py              # Database operations
├── config.json              # Configuration file
├── base_gui.spec            # PyInstaller spec
├── setup.iss                # Inno Setup script
└── README.md                # This file
Troubleshooting

    Database Errors: Ensure SQL Server is running, ODBC driver is installed, and connection_string is correct.
    Email Issues: Verify SMTP settings and network connectivity; check app.log for errors.
    PDF Generation: Confirm logo.png exists and output paths are writable.
    Logs: Located in BASE_DIR/logs (dev) or AppData/GuthPumpRegistry/logs (installed).

Contributing

    Fork the repository, make changes, and submit a pull request.
    Report issues or suggest features via GitHub Issues.

License

This project is proprietary to Guth South Africa. Contact the company for usage permissions.
Contact

For support, contact the Guth South Africa IT team at support@guth.co.za.
text

---

### Notes on Updates
1. **Clarity**: Describes the app’s purpose, roles, and workflow concisely.
2. **Setup**: Includes detailed instructions for both development and installed use, covering database and PyInstaller.
3. **Usage**: Explains how to run and use key features, with examples.
4. **Structure**: Reflects the codebase we’ve reviewed, noting optional files (`bom_utils.py`, `doc_utils.py`).
5. **Troubleshooting**: Addresses common issues based on our analysis.

---

### Testing Steps
1. **Create/Update File**:
   - Save this as `README.md` in `C:\Users\travism\source\repos\GuthPumpRegistry`.
   - If an existing file exists, overwrite or merge as needed.

2. **Review Locally**:
   - Open in a Markdown viewer (e.g., VS Code, GitHub Desktop) to check formatting.
   - Verify all paths and instructions match your setup.

3. **Test Instructions**:
   - Follow the **Installation** steps to ensure they work:
     - Clone, install dependencies, configure `config.json`, run `database.py`, and launch `base_gui.py`.
   - Build the executable and test the installed app.

4. **Push to GitHub (Optional)**:
   - If using GitHub:
     ```bash
     git add README.md
     git commit -m "Update README with project overview"
     git push origin main

    Check rendering on GitHub.