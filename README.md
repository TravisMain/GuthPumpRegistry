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
  - Track pump status: Stores -> Assembler -> Testing -> Pending Approval -> Completed.
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

- **Python 3.8+**: Required to run the application in development mode.
- **SQL Server**: GuthPumpRegistry database (create manually or via `database.py`).
- **ODBC Driver**: Install "ODBC Driver 17 for SQL Server" for database connectivity.
- **Dependencies**: Install via `requirements.txt`:
  ```bash
  pip install ttkbootstrap pyodbc bcrypt reportlab pillow