# -*- coding: utf-8 -*-
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
from database import connect_db
import os
import json
from datetime import datetime
from utils.config import get_logger
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib.pyplot as plt
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Logger setup
logger = get_logger("approval_gui")

# Paths and constants
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
PDF_LOGO_PATH = os.path.join(BASE_DIR, "assets", "guth_logo.png")
FONT_PATH = os.path.join(BASE_DIR, "assets", "Roboto-Regular.ttf")
FONT_BOLD_PATH = os.path.join(BASE_DIR, "assets", "Roboto-Black.ttf")
BUILD_NUMBER = "1.0.0"

# Register Roboto fonts for PDF generation
pdfmetrics.registerFont(TTFont('Roboto', FONT_PATH))
pdfmetrics.registerFont(TTFont('Roboto-Black', FONT_BOLD_PATH))

def send_email(to_email, pdf_path, pump_details):
    # Email configuration (replace with your SMTP settings)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "your-email@gmail.com"  # Replace with your email
    sender_password = "your-app-specific-password"  # Replace with your password or app-specific password

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = f"Pump Test Approval - Serial Number {pump_details['serial_number']}"

    # Email body with pump details
    body = f"""
    Dear {pump_details['originator']},

    The pump with Serial Number {pump_details['serial_number']} has been approved and is now completed.

    Pump Details:
    - Serial Number: {pump_details['serial_number']}
    - Customer: {pump_details['customer']}
    - Pump Model: {pump_details['pump_model']}
    - Configuration: {pump_details['configuration']}
    - Motor Size: {pump_details['motor_size']}
    - Motor Speed: {pump_details['motor_speed']}
    - Motor Volts: {pump_details['motor_volts']}
    - Motor Enclosure: {pump_details['motor_enclosure']}
    - Mechanical Seal: {pump_details['mechanical_seal']}
    - Frequency: {pump_details['frequency']}
    - Pump Housing: {pump_details['pump_housing']}
    - Pump Connection: {pump_details['pump_connection']}
    - Suction: {pump_details['suction']}
    - Discharge: {pump_details['discharge']}
    - Flush Arrangement: {pump_details['flush_arrangement']}
    - Date of Test: {pump_details['date_of_test']}
    - Duration of Test: {pump_details['duration_of_test']}
    - Test Medium: {pump_details['test_medium']}
    - Tested By: {pump_details['tested_by']}

    Please find the test report certificate attached.

    Regards,
    Guth Pump Registry Team
    """
    msg.attach(MIMEText(body, 'plain'))

    # Attach the PDF
    with open(pdf_path, 'rb') as f:
        attachment = MIMEApplication(f.read(), _subtype="pdf")
        attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
        msg.attach(attachment)

    # Send the email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        logger.info(f"Email sent to {to_email} with certificate for pump {pump_details['serial_number']}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")

def generate_certificate(data, serial_number):
    pdf_path = os.path.join(BASE_DIR, f"certificates/Pump_Test_Report_{serial_number}.pdf")
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    custom_style = ParagraphStyle(name='Custom', parent=styles['Normal'], fontName='Roboto', fontSize=8)
    heading_style = ParagraphStyle(name='Heading', parent=styles['Heading1'], fontName='Roboto-Black', fontSize=14, fontWeight='bold', alignment=0)
    subheading_style = ParagraphStyle(name='Subheading', fontName='Roboto-Black', fontSize=9, fontWeight='bold', alignment=1)
    footer_style = ParagraphStyle(name='Footer', fontName='Roboto', fontSize=7, alignment=0)

    story = []

    # Add logo to certificate
    if os.path.exists(PDF_LOGO_PATH):
        logo = RLImage(PDF_LOGO_PATH, width=120, height=60)
        logo.hAlign = 'RIGHT'
        story.append(logo)
        story.append(Spacer(1, 3))

    # Title
    title = Paragraph("PUMP TEST REPORT", heading_style)
    title.hAlign = 'LEFT'
    story.append(title)
    story.append(Spacer(1, 3))

    # Top Section: Invoice, Customer, Job Number
    top_data = [
        ["Invoice Number:", data["invoice_number"]],
        ["Customer:", data["customer"]],
        ["Job Number:", data["job_number"]],
    ]
    top_table = Table(top_data, colWidths=[125, 375], style=[
        ('FONTNAME', (0, 0), (-1, -1), 'Roboto'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('LEADING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ])
    top_table.hAlign = 'LEFT'
    story.append(top_table)
    story.append(Spacer(1, 3))

    # Fabrication and Hydraulic Test Sections
    fab_data = [
        ["FABRICATION", ""],
        ["Pump Model:", data["pump_model"]],
        ["Serial Number:", data["serial_number"]],
        ["Impeller Diameter:", data["impeller_diameter"]],
        ["Assembled By:", data["assembled_by"]],
    ]
    fab_table = Table(fab_data, colWidths=[80, 170], style=[
        ('FONTNAME', (0, 0), (-1, -1), 'Roboto'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('LEADING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (1, 0), 'Roboto-Black'),
        ('FONTSIZE', (0, 0), (1, 0), 9),
        ('FONTWEIGHT', (0, 0), (1, 0), 'bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (1, 0), colors.Color(188/255, 161/255, 4/255)),
    ])
    fab_table.hAlign = 'LEFT'

    hydro_data = [
        ["HYDRAULIC TEST", ""],
        ["Date of Test:", data["date_of_test"]],
        ["Duration of Test:", data["duration_of_test"]],
        ["Test Medium:", data["test_medium"]],
        ["Tested By:", data["tested_by"]],
    ]
    hydro_table = Table(hydro_data, colWidths=[80, 170], style=[
        ('FONTNAME', (0, 0), (-1, -1), 'Roboto'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('LEADING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (1, 0), 'Roboto-Black'),
        ('FONTSIZE', (0, 0), (1, 0), 9),
        ('FONTWEIGHT', (0, 0), (1, 0), 'bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (1, 0), colors.Color(188/255, 161/255, 4/255)),
    ])
    hydro_table.hAlign = 'LEFT'

    side_by_side_table = Table([[fab_table, hydro_table]], colWidths=[250, 250], style=[
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ])
    side_by_side_table.hAlign = 'LEFT'
    story.append(side_by_side_table)
    story.append(Spacer(1, 3))

    # Details Section
    details_data = [
        ["DETAILS", "", "", ""],
        ["Motor Size:", data["motor_size"], "Frequency:", data["frequency"]],
        ["Motor Speed:", data["motor_speed"], "Pump Housing:", data["pump_housing"]],
        ["Motor Volts:", data["motor_volts"], "Pump Connection:", data["pump_connection"]],
        ["Motor Enclosure:", data["motor_enclosure"], "Suction:", data["suction"]],
        ["Mechanical Seal:", data["mechanical_seal"], "Discharge:", data["discharge"]],
        ["", "", "Flush Arrangement:", data["flush_arrangement"]],
    ]
    details_table = Table(details_data, colWidths=[125, 125, 125, 125], style=[
        ('FONTNAME', (0, 0), (-1, -1), 'Roboto'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('LEADING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (3, 0), 'Roboto-Black'),
        ('FONTSIZE', (0, 0), (3, 0), 9),
        ('FONTWEIGHT', (0, 0), (3, 0), 'bold'),
        ('SPAN', (0, 0), (3, 0)),
        ('ALIGN', (0, 0), (3, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (3, 0), colors.Color(188/255, 161/255, 4/255)),
    ])
    details_table.hAlign = 'LEFT'
    story.append(details_table)
    story.append(Spacer(1, 3))

    # Test Results Section
    test_results_heading = Paragraph("TEST RESULTS", subheading_style)
    test_results_heading.hAlign = 'LEFT'
    story.append(test_results_heading)
    story.append(Spacer(1, 3))

    test_results_data = [
        ["Test", "Flowrate (L/h)", "Pressure (bar)", "Amperage (A)"],
    ]
    for i in range(5):
        test_results_data.append([f"Test {i+1}", data["flowrate"][i], data["pressure"][i], data["amperage"][i]])

    test_results_table = Table(test_results_data, colWidths=[125, 125, 125, 125], style=[
        ('FONTNAME', (0, 0), (-1, -1), 'Roboto'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('LEADING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (3, 0), 'Roboto'),
        ('FONTSIZE', (0, 0), (3, 0), 8),
        ('FONTWEIGHT', (0, 0), (3, 0), 'bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (3, 0), colors.Color(188/255, 161/255, 4/255)),
    ])
    test_results_table.hAlign = 'LEFT'
    story.append(test_results_table)
    story.append(Spacer(1, 3))

    # Generate Graph
    buf = io.BytesIO()
    fig, ax1 = plt.subplots(figsize=(6, 2.5))
    desaturated_blue = (100/255, 149/255, 237/255)
    desaturated_red = (255/255, 99/255, 71/255)
    ax1.plot([float(x or 0) for x in data["flowrate"]], [float(x or 0) for x in data["pressure"]], 
             color=desaturated_blue, linestyle='-')
    ax1.set_xlabel("Flow (L/h)", fontsize=10)
    ax1.set_ylabel("Pressure (bar)", color=desaturated_blue, fontsize=10)
    ax1.tick_params('y', colors=desaturated_blue)
    ax1.set_xlim(0, 20000)
    ax1.set_ylim(0, 3.5)
    ax1.set_xticks([0, 5000, 10000, 15000, 20000])
    ax1.set_yticks([0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5])
    ax1.grid(True, linestyle='--', alpha=0.7)
    for spine in ax1.spines.values():
        spine.set_linewidth(0.5)
    ax2 = ax1.twinx()
    ax2.plot([float(x or 0) for x in data["flowrate"]], [float(x or 0) for x in data["amperage"]], 
             color=desaturated_red, linestyle='-')
    ax2.set_ylabel("Amperage (A)", color=desaturated_red, fontsize=10)
    ax2.tick_params('y', colors=desaturated_red)
    ax2.set_ylim(0, 7)
    ax2.set_yticks([0, 1, 2, 3, 4, 5, 6, 7])
    for spine in ax2.spines.values():
        spine.set_linewidth(0.5)
    fig.tight_layout()
    plt.savefig(buf, format='png', dpi=400)
    buf.seek(0)
    graph = RLImage(buf, width=450, height=200)
    graph_table = Table([[graph]], colWidths=[500], style=[
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ])
    graph_table.hAlign = 'LEFT'
    story.append(graph_table)
    story.append(Spacer(1, 3))

    # Approval Section
    approval_data = [
        ["APPROVAL", "", "", ""],
        ["Approved By:", data["approved_by"], "", ""],  # Username of the approver
        ["Date:", data["approval_date"], "", ""],
    ]
    approval_table = Table(approval_data, colWidths=[125, 125, 125, 125], style=[
        ('FONTNAME', (0, 0), (-1, -1), 'Roboto'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('LEADING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (3, 0), 'Roboto-Black'),
        ('FONTSIZE', (0, 0), (3, 0), 9),
        ('FONTWEIGHT', (0, 0), (3, 0), 'bold'),
        ('SPAN', (0, 0), (3, 0)),
        ('ALIGN', (0, 0), (3, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (3, 0), colors.Color(188/255, 161/255, 4/255)),
    ])
    approval_table.hAlign = 'LEFT'
    story.append(approval_table)
    story.append(Spacer(1, 10))

    # Footer with Copyright and Build Number
    footer_text = f"\u00A9 Guth South Africa | Build {BUILD_NUMBER}"
    footer = Paragraph(footer_text, footer_style)
    footer.hAlign = 'LEFT'
    story.append(footer)

    # Build the PDF
    doc.build(story)
    buf.close()
    logger.info(f"Certificate generated: {pdf_path}")
    return pdf_path

def show_approval_dashboard(root, username, role, logout_callback):
    # Clear the window
    for widget in root.winfo_children():
        widget.destroy()

    root.state('zoomed')
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Header
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
            logger.error(f"Approval logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Review and approve completed pump tests.", font=("Roboto", 12)).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Approval Dashboard", font=("Roboto", 16, "bold")).pack(pady=10)

    # Pump List
    pump_list_frame = ttk.LabelFrame(main_frame, text="Pumps Pending Approval", padding=10)
    pump_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    columns = ("Serial Number", "Customer", "Branch", "Pump Model", "Configuration")
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
                SELECT serial_number, customer, branch, pump_model, configuration
                FROM pumps WHERE status = 'Pending Approval'
            """)
            for pump in cursor.fetchall():
                tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"],
                                            pump["pump_model"], pump["configuration"]))

    refresh_pump_list()
    tree.bind("<Double-1>", lambda event: show_approval_details(main_frame, tree, username, refresh_pump_list))

    # Footer
    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=10)
    ttk.Button(footer_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

def show_approval_details(parent_frame, tree, username, refresh_callback):
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    serial_number = tree.item(selected[0])["values"][0]
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT customer, pump_model, configuration, originator, test_data FROM pumps WHERE serial_number = ?", (serial_number,))
        pump = cursor.fetchone()
        if not pump:
            logger.warning(f"No pump found for serial_number: {serial_number}")
            return
        test_data = json.loads(pump["test_data"]) if pump["test_data"] else {}

    # Create a new window for approval details
    approval_window = ttk.Toplevel(parent_frame)
    approval_window.title(f"Approve Pump {serial_number}")
    approval_window.state("zoomed")

    # Header
    header_frame = ttk.Frame(approval_window, style="white.TFrame")
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
            logger.error(f"Approval details logo load failed: {str(e)}")
    ttk.Label(header_frame, text="Pump Approval", font=("Roboto", 14, "bold")).pack(anchor=W, padx=10)

    # Scrollable canvas
    canvas = ttk.Canvas(approval_window)
    scrollbar = ttk.Scrollbar(approval_window, orient=VERTICAL, command=canvas.yview)
    main_frame = ttk.Frame(canvas)

    main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=main_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)
    scrollbar.pack(side=RIGHT, fill=Y)

    def on_mouse_wheel(event):
        canvas.yview_scroll(-1 * (event.delta // 120), "units")
    canvas.bind_all("<MouseWheel>", on_mouse_wheel)

    # Pump Details (non-editable)
    details_frame = ttk.LabelFrame(main_frame, text="Pump Details", padding=10)
    details_frame.pack(fill=X, padx=10, pady=10)

    ttk.Label(details_frame, text="Serial Number:", font=("Roboto", 10)).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(details_frame, text=serial_number, font=("Roboto", 10)).grid(row=0, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(details_frame, text="Customer:", font=("Roboto", 10)).grid(row=1, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(details_frame, text=pump["customer"], font=("Roboto", 10)).grid(row=1, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(details_frame, text="Pump Model:", font=("Roboto", 10)).grid(row=2, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(details_frame, text=pump["pump_model"], font=("Roboto", 10)).grid(row=2, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(details_frame, text="Configuration:", font=("Roboto", 10)).grid(row=3, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(details_frame, text=pump["configuration"], font=("Roboto", 10)).grid(row=3, column=1, padx=5, pady=5, sticky=W)

    # Test Details (editable)
    test_frame = ttk.LabelFrame(main_frame, text="Test Details", padding=10)
    test_frame.pack(fill=X, padx=10, pady=10)

    # Fabrication and Hydraulic Test
    ttk.Label(test_frame, text="Fabrication", font=("Roboto", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=5)
    fab_fields = [
        ("Pump Model:", test_data.get("pump_model", ""), ttk.Entry(test_frame, width=20)),
        ("Serial Number:", serial_number, ttk.Label(test_frame, text=serial_number, font=("Roboto", 10))),  # Non-editable
        ("Impeller Diameter:", test_data.get("impeller_diameter", ""), ttk.Entry(test_frame, width=20)),
        ("Assembled By:", test_data.get("assembled_by", ""), ttk.Entry(test_frame, width=20)),
    ]
    for i, (label, value, widget) in enumerate(fab_fields, start=1):
        ttk.Label(test_frame, text=label, font=("Roboto", 10)).grid(row=i, column=0, padx=5, pady=2, sticky=W)
        if isinstance(widget, ttk.Entry):
            widget.insert(0, value)
        widget.grid(row=i, column=1, padx=5, pady=2, sticky=W)

    ttk.Label(test_frame, text="Hydraulic Test", font=("Roboto", 12, "bold")).grid(row=0, column=2, columnspan=2, pady=5)
    hydro_fields = [
        ("Date of Test:", test_data.get("date_of_test", ""), ttk.Entry(test_frame, width=20)),
        ("Duration of Test:", test_data.get("duration_of_test", ""), ttk.Entry(test_frame, width=20)),
        ("Test Medium:", test_data.get("test_medium", ""), ttk.Entry(test_frame, width=20)),
        ("Tested By:", test_data.get("tested_by", ""), ttk.Label(test_frame, text=test_data.get("tested_by", ""), font=("Roboto", 10))),  # Non-editable
    ]
    for i, (label, value, widget) in enumerate(hydro_fields, start=1):
        ttk.Label(test_frame, text=label, font=("Roboto", 10)).grid(row=i, column=2, padx=5, pady=2, sticky=W)
        if isinstance(widget, ttk.Entry):
            widget.insert(0, value)
        widget.grid(row=i, column=3, padx=5, pady=2, sticky=W)

    # Details Section
    details_subframe = ttk.LabelFrame(main_frame, text="Details", padding=10)
    details_subframe.pack(fill=X, padx=10, pady=10)
    details_fields_left = [
        ("Motor Size:", test_data.get("motor_size", ""), ttk.Entry(details_subframe, width=20)),
        ("Motor Speed:", test_data.get("motor_speed", ""), ttk.Entry(details_subframe, width=20)),
        ("Motor Volts:", test_data.get("motor_volts", ""), ttk.Entry(details_subframe, width=20)),
        ("Motor Enclosure:", test_data.get("motor_enclosure", ""), ttk.Entry(details_subframe, width=20)),
        ("Mechanical Seal:", test_data.get("mechanical_seal", ""), ttk.Entry(details_subframe, width=20)),
    ]
    details_fields_right = [
        ("Frequency:", test_data.get("frequency", ""), ttk.Entry(details_subframe, width=20)),
        ("Pump Housing:", test_data.get("pump_housing", ""), ttk.Entry(details_subframe, width=20)),
        ("Pump Connection:", test_data.get("pump_connection", ""), ttk.Entry(details_subframe, width=20)),
        ("Suction:", test_data.get("suction", ""), ttk.Entry(details_subframe, width=20)),
        ("Discharge:", test_data.get("discharge", ""), ttk.Entry(details_subframe, width=20)),
        ("Flush Arrangement:", test_data.get("flush_arrangement", ""), ttk.Entry(details_subframe, width=20)),
    ]
    for i, (label, value, widget) in enumerate(details_fields_left):
        ttk.Label(details_subframe, text=label, font=("Roboto", 10)).grid(row=i, column=0, padx=5, pady=2, sticky=W)
        widget.insert(0, value)
        widget.grid(row=i, column=1, padx=5, pady=2, sticky=W)
    for i, (label, value, widget) in enumerate(details_fields_right):
        ttk.Label(details_subframe, text=label, font=("Roboto", 10)).grid(row=i, column=2, padx=5, pady=2, sticky=W)
        widget.insert(0, value)
        widget.grid(row=i, column=3, padx=5, pady=2, sticky=W)

    # Test Results
    test_results_frame = ttk.LabelFrame(main_frame, text="Test Results", padding=10)
    test_results_frame.pack(fill=X, padx=10, pady=10)
    ttk.Label(test_results_frame, text="Test", font=("Roboto", 10)).grid(row=0, column=0, padx=5, pady=5)
    ttk.Label(test_results_frame, text="Flowrate (L/h)", font=("Roboto", 10)).grid(row=0, column=1, padx=5, pady=5)
    ttk.Label(test_results_frame, text="Pressure (bar)", font=("Roboto", 10)).grid(row=0, column=2, padx=5, pady=5)
    ttk.Label(test_results_frame, text="Amperage (A)", font=("Roboto", 10)).grid(row=0, column=3, padx=5, pady=5)

    flow_entries = []
    pressure_entries = []
    amp_entries = []
    for i in range(5):
        ttk.Label(test_results_frame, text=f"Test {i+1}", font=("Roboto", 10)).grid(row=i+1, column=0, padx=5, pady=2, sticky=W)
        flow_entry = ttk.Entry(test_results_frame, width=15)
        flow_entry.insert(0, test_data.get("flowrate", [""]*5)[i])
        flow_entry.grid(row=i+1, column=1, padx=5, pady=2, sticky=W)
        pressure_entry = ttk.Entry(test_results_frame, width=15)
        pressure_entry.insert(0, test_data.get("pressure", [""]*5)[i])
        pressure_entry.grid(row=i+1, column=2, padx=5, pady=2, sticky=W)
        amp_entry = ttk.Entry(test_results_frame, width=15)
        amp_entry.insert(0, test_data.get("amperage", [""]*5)[i])
        amp_entry.grid(row=i+1, column=3, padx=5, pady=2, sticky=W)
        flow_entries.append(flow_entry)
        pressure_entries.append(pressure_entry)
        amp_entries.append(amp_entry)

    # Error label for validation
    error_frame = ttk.Frame(main_frame)
    error_frame.pack(fill=X, padx=10, pady=5)
    error_label = ttk.Label(error_frame, text="", font=("Roboto", 10), bootstyle="danger")
    error_label.pack()

    # Validation for numeric fields
    def validate_numeric_fields():
        for i in range(5):
            try:
                flow = flow_entries[i].get()
                if flow and not float(flow) >= 0:
                    raise ValueError("Flowrate must be a non-negative number")
            except ValueError:
                error_label.config(text=f"Flowrate for Test {i+1} must be a valid number")
                return False
            try:
                pressure = pressure_entries[i].get()
                if pressure and not float(pressure) >= 0:
                    raise ValueError("Pressure must be a non-negative number")
            except ValueError:
                error_label.config(text=f"Pressure for Test {i+1} must be a valid number")
                return False
            try:
                amperage = amp_entries[i].get()
                if amperage and not float(amperage) >= 0:
                    raise ValueError("Amperage must be a non-negative number")
            except ValueError:
                error_label.config(text=f"Amperage for Test {i+1} must be a valid number")
                return False
        return True

    # Update test_data with edited values
    def update_test_data_from_fields():
        test_data["pump_model"] = fab_fields[0][2].get()
        test_data["impeller_diameter"] = fab_fields[2][2].get()
        test_data["assembled_by"] = fab_fields[3][2].get()
        test_data["date_of_test"] = hydro_fields[0][2].get()
        test_data["duration_of_test"] = hydro_fields[1][2].get()
        test_data["test_medium"] = hydro_fields[2][2].get()
        test_data["motor_size"] = details_fields_left[0][2].get()
        test_data["motor_speed"] = details_fields_left[1][2].get()
        test_data["motor_volts"] = details_fields_left[2][2].get()
        test_data["motor_enclosure"] = details_fields_left[3][2].get()
        test_data["mechanical_seal"] = details_fields_left[4][2].get()
        test_data["frequency"] = details_fields_right[0][2].get()
        test_data["pump_housing"] = details_fields_right[1][2].get()
        test_data["pump_connection"] = details_fields_right[2][2].get()
        test_data["suction"] = details_fields_right[3][2].get()
        test_data["discharge"] = details_fields_right[4][2].get()
        test_data["flush_arrangement"] = details_fields_right[5][2].get()
        test_data["flowrate"] = [entry.get() for entry in flow_entries]
        test_data["pressure"] = [entry.get() for entry in pressure_entries]
        test_data["amperage"] = [entry.get() for entry in amp_entries]

    # Action Buttons
    action_frame = ttk.Frame(main_frame)
    action_frame.pack(fill=X, padx=10, pady=10)

    def save_changes():
        if not validate_numeric_fields():
            return
        update_test_data_from_fields()
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pumps SET test_data = ? WHERE serial_number = ?", (json.dumps(test_data), serial_number))
            conn.commit()
            logger.info(f"Changes saved for pump {serial_number} by {username}")
        error_label.config(text="Changes saved successfully", bootstyle="success")

    def approve_pump():
        if not validate_numeric_fields():
            return
        update_test_data_from_fields()
        test_data["approved_by"] = username  # Set the approver's username
        test_data["approval_date"] = datetime.now().strftime("%Y-%m-%d")
        pdf_path = generate_certificate(test_data, serial_number)
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pumps SET status = 'Completed', test_data = ? WHERE serial_number = ?", 
                          (json.dumps(test_data), serial_number))
            conn.commit()
            logger.info(f"Pump {serial_number} approved by {username}, status set to Completed")
        originator = pump["originator"]
        originator_email = f"{originator}@example.com"  # Replace with actual email mapping
        test_data["originator"] = originator
        send_email(originator_email, pdf_path, test_data)
        refresh_callback()
        approval_window.destroy()

    def reject_pump():
        if not validate_numeric_fields():
            return
        update_test_data_from_fields()
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pumps SET status = 'Testing', test_data = ? WHERE serial_number = ?", 
                          (json.dumps(test_data), serial_number))
            conn.commit()
            logger.info(f"Pump {serial_number} rejected by {username}, returned to Testing with updated data")
        refresh_callback()
        approval_window.destroy()

    def close_window():
        # Close the window without changing the pump's status
        approval_window.destroy()

    ttk.Button(action_frame, text="Save Changes", command=save_changes, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=10)
    ttk.Button(action_frame, text="Approve", command=approve_pump, bootstyle="success", style="large.TButton").pack(side=LEFT, padx=10)
    ttk.Button(action_frame, text="Reject", command=reject_pump, bootstyle="danger", style="large.TButton").pack(side=LEFT, padx=10)
    ttk.Button(action_frame, text="Close", command=close_window, bootstyle="secondary", style="large.TButton").pack(side=LEFT, padx=10)

    # Footer
    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=10)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_approval_dashboard(root, "approver1", "approval", lambda: print("Logged off"))
    root.mainloop()