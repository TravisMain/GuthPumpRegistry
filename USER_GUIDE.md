# Guth Pump Registry User Guide

Welcome to the Guth Pump Registry, a desktop application designed to streamline the management of pump assemblies at Guth South Africa. This guide provides step-by-step instructions for using the application, tailored to your role within the workflow. Whether you're creating pumps, pulling parts, testing assemblies, approving results, or managing the system, this document will help you get started and make the most of the tool.

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
   - [Installation](#installation)
   - [Logging In](#logging-in)
   - [Registering a New User](#registering-a-new-user)
3. [User Roles and Dashboards](#user-roles-and-dashboards)
   - [Pump Originator](#pump-originator)
   - [Stores](#stores)
   - [Assembler/Tester](#assembler-tester)
   - [Approval](#approval)
   - [Admin](#admin)
4. [Key Features](#key-features)
   - [Creating a Pump](#creating-a-pump)
   - [Managing BOM Items](#managing-bom-items)
   - [Testing Pumps](#testing-pumps)
   - [Approving Pumps](#approving-pumps)
   - [Notifications](#notifications)
   - [Configuration](#configuration)
5. [Troubleshooting](#troubleshooting)
6. [Contact Support](#contact-support)

## Overview

The Guth Pump Registry is a role-based application that tracks pump assemblies from creation to completion. It integrates with a SQL Server database to store pump details, Bills of Materials (BOM), user accounts, and audit logs. The application generates PDF notifications and sends email alerts to keep teams informed at each workflow stage.

### Key Workflow Stages
- **Stores**: Pumps are created and await BOM item pulling.
- **Assembler**: Parts are pulled and assembled.
- **Testing**: Assembled pumps are tested.
- **Pending Approval**: Tested pumps await approval.
- **Completed**: Approved pumps are finalized.

## Getting Started

### Installation
1. **For Installed Users**:
   - Run the installer (`GuthPumpRegistrySetup.exe`) provided by your IT team.
   - Follow the prompts to install the application (default: `C:\Program Files\GuthPumpRegistry`).
   - Launch the app from the Start menu or desktop shortcut.

2. **For Developers**:
   - See `README.md` for cloning, dependency installation, and database setup instructions.

### Logging In
1. Launch the application.
2. On the login screen:
   - **Username**: Enter your assigned username (e.g., `admin1`).
   - **Password**: Enter your password (e.g., `password` for test users).
   - Check **Remember Me** to save your credentials for future logins (stored securely in `AppData`).
   - Click **Login** or press Enter.
3. If credentials are incorrect, an error message appears. Use **Forgot Password?** to reset (requires SMTP setup).

### Registering a New User
1. From the login screen, click **Register**.
2. Fill in:
   - **Username**: Unique identifier (e.g., `jdoe`).
   - **Name**: First name (e.g., `John`).
   - **Surname**: Last name (e.g., `Doe`).
   - **Email**: Valid email address (e.g., `john.doe@guth.co.za`).
   - **Password**: Secure password.
3. Click **Submit**. On success, you'll see "Registration successful! You can now login." Default role is **Pump Originator**.

## User Roles and Dashboards

### Pump Originator
- **Dashboard**: Create new pumps and view status.
- **Tabs**:
  - **Create New Pump**: Form to input pump details.
  - **All Pumps**: Table of all pumps with status.
  - **Pumps in Stores**: Table of pumps awaiting BOM pulling.

### Stores
- **Dashboard**: Manage BOM items for assembly.
- **Features**:
  - View pumps in Stores status.
  - Pull BOM items or mark as not pulled with reasons.

### Assembler/Tester
- **Dashboard**: Assemble and test pumps.
- **Sections**:
  - **Assembly Tasks**: Confirm BOM items and move to Testing.
  - **Testing Tasks**: Enter test data and submit for approval.

### Approval
- **Dashboard**: Review and approve tested pumps.
- **Features**:
  - Approve or reject pumps with comments.
  - View test data and graphs (if configured).

### Admin
- **Dashboard**: System management.
- **Tabs**:
  - **Users**: Add/edit users and roles.
  - **Email**: Configure SMTP settings.
  - **Configuration**: Set document storage paths.

## Key Features

### Creating a Pump (Pump Originator)
1. Log in as a Pump Originator.
2. In **Create New Pump**:
   - Fill fields (e.g., Pump Model: `P1 3.0KW`, Configuration: `Standard`, Customer: `Guth Test`).
   - Required fields are marked with `*`.
   - Click **Create Pump**.
3. On success, see "Created S/N: <serial>" (e.g., `5101 001 - 25`).
   - A PDF notification is generated and emailed to Stores (if SMTP is set).

### Managing BOM Items (Stores)
1. Log in as Stores.
2. Select a pump in **Pumps in Stores**.
3. Double-click to open BOM:
   - Check items to mark as pulled.
   - Enter reasons for unpulled items.
   - Submit to move pump to **Assembler** status.
4. A confirmation PDF and email are sent.

### Testing Pumps (Assembler/Tester)
1. Log in as Assembler/Tester.
2. In **Assembly Tasks**:
   - Double-click a pump, confirm all BOM items, submit to move to **Testing**.
3. In **Testing Tasks**:
   - Double-click a pump, enter test data (e.g., Flowrate, Pressure, Amperage for 5 tests).
   - Submit for **Pending Approval**.
4. A test certificate PDF and email are generated.

### Approving Pumps (Approval)
1. Log in as Approval.
2. Select a pump in **Pending Approval**.
3. Review test data, approve or reject with comments.
4. On approval, pump moves to **Completed**; a PDF and email are sent.

### Notifications
- **PDFs**: Saved to paths set in `config.json` (e.g., `C:\Custom\Path\Notifications`).
- **Emails**: Sent to role-specific recipients (e.g., `stores@guth.co.za`) with attachments.
- Configure SMTP in Admin -> Email tab for email functionality.

### Configuration (Admin)
1. Log in as Admin.
2. **Users Tab**:
   - Add/edit users, assign roles (e.g., `Stores`, `Approval`).
3. **Email Tab**:
   - Set SMTP host, port, username, password, and sender email.
4. **Configuration Tab**:
   - Define paths for notifications, certificates, BOMs, and confirmations.

## Troubleshooting

- **Login Fails**:
  - Check username/password; use **Forgot Password?** if SMTP is configured.
  - Verify database connection in `config.json`.

- **PDFs Not Generating**:
  - Ensure `logo.png` exists in `assets\` and output paths are writable.
  - Check `app.log` for errors.

- **Emails Not Sending**:
  - Confirm SMTP settings in Admin -> Email.
  - Check network and `app.log` for SMTP errors.

- **Database Errors**:
  - Ensure SQL Server is running and ODBC Driver 17 is installed.
  - Verify `connection_string` in `config.json`.

- **Logs**:
  - Located in `BASE_DIR/logs` (dev) or `AppData/GuthPumpRegistry/logs` (installed).

## Contact Support

For assistance, contact the Guth South Africa IT team:
- **Email**: [support@guth.co.za](mailto:support@guth.co.za)
- **Phone**: [Insert contact number]
- Include `app.log` excerpts with support requests for faster resolution.

---

Happy pumping with Guth Pump Registry!