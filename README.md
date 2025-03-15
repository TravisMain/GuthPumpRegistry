# Guth Pump Assembly Registry

![Logo](assets/logo.png) <!-- Placeholder for logo, update when available -->

**Version:** 0.1.0 (Pre-Release)  
**Date:** March 14, 2025  
**Developed by:** Travis Main for Guth South Africa  

The Guth Pump Assembly Registry is a desktop application designed to digitize and optimize the pump assembly workflow for Guth South Africa. It provides role-based dashboards (Admin, Stores, Assembler, Testing, Pump Originator), secure authentication, serial number generation, automated test certificates, and data exports, all backed by an SQLite database. This project is developed in Python 3.11.6 and targets deployment on Windows 10+, macOS 10.14+, and Ubuntu 20.04+ by May 5, 2025.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Features](#features)
3. [System Requirements](#system-requirements)
4. [Installation](#installation)
5. [Project Structure](#project-structure)
6. [Usage](#usage)
7. [Development Phases](#development-phases)
8. [Contributing](#contributing)
9. [License](#license)
10. [Contact](#contact)

---

## Project Overview

The Guth Pump Assembly Registry automates the pump assembly process, reducing errors and time by 50%. It replaces paper-based workflows with a digital system featuring:
- **Role-Based Dashboards:** Tailored interfaces for each user role.
- **Serial Number Generation:** Unique identifiers (e.g., `S/N: 5101 090 – 25`).
- **Workflow Management:** Tracks pumps from creation (Pump Originator) to completion (Testing).
- **Documentation:** Stores test certificates in `docs/[serial_number]_[pump_model]/`.
- **Exports:** Admin can export activity logs, user lists, and pump lists to Excel.

This project is in active development, with Phase 1 (Planning and Design) underway as of March 14, 2025.

---

## Features

- **Current Features (Phase 1):**
  - SQLite database initialized with five tables: `pumps`, `bom_items`, `users`, `audit_log`, `serial_counter`.
  - Modular project structure with `gui/` and `utils/` directories.

- **Planned Features (Phases 2-4):**
  - Role-based GUI dashboards using `ttkbootstrap`.
  - Serial number generation (`S/N: ABCD EFG – HI`, CD as 01).
  - Bill of Materials (BOM) management and verification.
  - Automated PDF test certificates with email delivery.
  - Excel exports for activity logs, users, and pumps.
  - Multi-language support preparation (i18n).
  - Offsite backup options.

See the [Statement of Work (SOW) v2.12](#) for full details (link to be added post-documentation).

---

## System Requirements

### Hardware
- **Processor:** 1 GHz or faster
- **RAM:** 4 GB minimum
- **Disk Space:** 2 GB free (initial database <10 MB)
- **Display:** 1280x720 resolution

### Software
- **Operating Systems:** Windows 10/11, macOS 10.14+, Ubuntu 20.04+
- **Python:** 3.11.6
- **Dependencies:**
  - `ttkbootstrap==1.10.1`
  - `bcrypt==4.1.2`
  - `fpdf==1.7.2`
  - `python-dotenv==1.0.1`
  - `openpyxl==3.1.2`
- **Tools:**
  - Visual Studio Community 2022 (recommended)
  - Git (for version control)
  - PyInstaller (for executable packaging, Phase 4)

### Network
- 1 Mbps upload speed for SMTP (email certificates, optional local network)

---

## Installation

### Prerequisites
1. Install Python 3.11.6 from [python.org](https://www.python.org/downloads/release/python-3116/).
2. Install Git from [git-scm.com](https://git-scm.com/).
3. (Optional) Install Visual Studio Community 2022 from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/vs/community/).

### Steps
1. **Clone the Repository:**
   ```bash
   git clone https://github.com/[yourusername]/GuthPumpRegistry.git
   cd GuthPumpRegistry
