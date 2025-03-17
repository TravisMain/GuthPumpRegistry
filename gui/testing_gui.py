import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
from database import connect_db
import os
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

logger = get_logger("testing_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
PDF_LOGO_PATH = os.path.join(BASE_DIR, "assets", "guth_logo.png")  # New logo for PDF
FONT_PATH = os.path.join(BASE_DIR, "assets", "Roboto-Regular.ttf")
FONT_BOLD_PATH = os.path.join(BASE_DIR, "assets", "Roboto-Black.ttf")
BUILD_NUMBER = "1.0.0"

# Register Roboto fonts
pdfmetrics.registerFont(TTFont('Roboto', FONT_PATH))
pdfmetrics.registerFont(TTFont('Roboto-Black', FONT_BOLD_PATH))

def show_testing_dashboard(root, username, role, logout_callback):
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
            logger.error(f"Testing logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="View and manage pumps in Testing status.", font=("Roboto", 12)).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Testing Pump Inventory", font=("Roboto", 16, "bold")).pack(pady=10)

    pump_list_frame = ttk.LabelFrame(main_frame, text="Pumps in Testing", padding=10)
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
                FROM pumps WHERE status = 'Testing'
            """)
            for pump in cursor.fetchall():
                tree.insert("", END, values=(pump["serial_number"], pump["customer"], pump["branch"],
                                            pump["pump_model"], pump["configuration"]))

    refresh_pump_list()
    tree.bind("<Double-1>", lambda event: show_test_report(main_frame, tree, username, refresh_pump_list))

    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=10)
    ttk.Button(footer_frame, text="Logoff", command=logout_callback, bootstyle="warning", style="large.TButton").pack(pady=5)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

def generate_certificate(data, serial_number):
    pdf_path = os.path.join(BASE_DIR, f"certificates/Pump_Test_Report_{serial_number}.pdf")
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    # Custom styles with Roboto
    custom_style = ParagraphStyle(name='Custom', parent=styles['Normal'], fontName='Roboto', fontSize=8)
    heading_style = ParagraphStyle(name='Heading', parent=styles['Heading1'], fontName='Roboto-Black', fontSize=14, fontWeight='bold', alignment=0)
    subheading_style = ParagraphStyle(name='Subheading', fontName='Roboto-Black', fontSize=9, fontWeight='bold', alignment=1)

    story = []

    # Logo (above title, right-aligned)
    if os.path.exists(PDF_LOGO_PATH):  # Updated to use PDF_LOGO_PATH
        logo = RLImage(PDF_LOGO_PATH, width=120, height=60)
        logo.hAlign = 'RIGHT'
        story.append(logo)
        story.append(Spacer(1, 3))

    # Title (aligned with tables)
    title = Paragraph("PUMP TEST REPORT", heading_style)
    title.hAlign = 'LEFT'
    story.append(title)
    story.append(Spacer(1, 3))

    # Top Fields Table
    top_data = [
        ["Invoice Number:", data["invoice_number"]],
        ["Customer:", data["customer"]],  # Fixed to use data["customer"]
        ["Job Number:", data["job_number"]]
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

    # Fabrication and Hydraulic Test Tables Side by Side
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

    # Details Table
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

    # Test Results as a separate section
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

    # Graph with Border
    buf = io.BytesIO()
    fig, ax1 = plt.subplots(figsize=(6, 2.5))
    
    # Desaturated colors: cornflower blue for Pressure, tomato for Amperage
    desaturated_blue = (100/255, 149/255, 237/255)  # #6495ED
    desaturated_red = (255/255, 99/255, 71/255)     # #FF6347
    
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

    # Approval Table
    approval_data = [
        ["APPROVAL", "", "", ""],
        ["Approved By:", data["approved_by"], "", ""],
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

    doc.build(story)
    buf.close()
    logger.info(f"Certificate generated: {pdf_path}")
    return pdf_path

def show_test_report(parent_frame, tree, username, refresh_callback):
    selected = tree.selection()
    if not selected:
        logger.debug("No pump selected in Treeview")
        return

    serial_number = tree.item(selected[0])["values"][0]
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT customer, pump_model, configuration FROM pumps WHERE serial_number = ?", (serial_number,))
        pump = cursor.fetchone()
        if not pump:
            logger.warning(f"No pump found for serial_number: {serial_number}")
            return

    test_window = ttk.Toplevel(parent_frame)
    test_window.title(f"Test Report for Pump {serial_number}")
    test_window.state("zoomed")

    header_frame = ttk.Frame(test_window, style="white.TFrame")
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
            logger.error(f"Test report logo load failed: {str(e)}")
    ttk.Label(header_frame, text="Pump Test Report", font=("Roboto", 14, "bold")).pack(anchor=W, padx=10)

    canvas = ttk.Canvas(test_window)
    scrollbar = ttk.Scrollbar(test_window, orient=VERTICAL, command=canvas.yview)
    main_frame = ttk.Frame(canvas)

    main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=main_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)
    scrollbar.pack(side=RIGHT, fill=Y)

    def on_mouse_wheel(event):
        canvas.yview_scroll(-1 * (event.delta // 120), "units")
    canvas.bind_all("<MouseWheel>", on_mouse_wheel)

    top_frame = ttk.Frame(main_frame)
    top_frame.grid(row=0, column=0, pady=(0, 15), sticky=W)

    ttk.Label(top_frame, text="Invoice Number:", font=("Roboto", 10)).grid(row=0, column=0, padx=10, pady=2, sticky=W)
    invoice_entry = ttk.Entry(top_frame, width=30)
    invoice_entry.grid(row=0, column=1, padx=10, pady=2, sticky=W)

    ttk.Label(top_frame, text="Customer:", font=("Roboto", 10)).grid(row=1, column=0, padx=10, pady=2, sticky=W)
    ttk.Label(top_frame, text=pump["customer"], font=("Roboto", 10)).grid(row=1, column=1, padx=10, pady=2, sticky=W)

    ttk.Label(top_frame, text="Job Number:", font=("Roboto", 10)).grid(row=2, column=0, padx=10, pady=2, sticky=W)
    job_entry = ttk.Entry(top_frame, width=30)
    job_entry.grid(row=2, column=1, padx=10, pady=2, sticky=W)

    main_layout = ttk.Frame(main_frame)
    main_layout.grid(row=1, column=0, pady=15, sticky=W+E)

    left_frame = ttk.Frame(main_layout)
    left_frame.pack(side=LEFT, padx=15, fill=Y)

    fab_frame = ttk.LabelFrame(left_frame, text="Fabrication", padding=10, labelwidget=ttk.Label(left_frame, text="Fabrication", font=("Roboto", 12, "bold")))
    fab_frame.pack(pady=(0, 10), fill=X)

    ttk.Label(fab_frame, text="Pump Model:", font=("Roboto", 10)).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=pump["pump_model"], font=("Roboto", 10)).grid(row=0, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Serial Number:", font=("Roboto", 10)).grid(row=1, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=serial_number, font=("Roboto", 10)).grid(row=1, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Impeller Diameter:", font=("Roboto", 10)).grid(row=2, column=0, padx=5, pady=5, sticky=W)
    impeller_entry = ttk.Entry(fab_frame, width=20)
    impeller_entry.grid(row=2, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Assembled By:", font=("Roboto", 10)).grid(row=3, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=username, font=("Roboto", 10)).grid(row=3, column=1, padx=5, pady=5, sticky=W)

    details_frame = ttk.LabelFrame(left_frame, text="Details", padding=10, labelwidget=ttk.Label(left_frame, text="Details", font=("Roboto", 12, "bold")))
    details_frame.pack(fill=X)

    fields_left = [
        ("Motor Size:", ttk.Entry(details_frame, width=20)),
        ("Motor Speed:", ttk.Entry(details_frame, width=20)),
        ("Motor Volts:", ttk.Entry(details_frame, width=20)),
        ("Motor Enclosure:", ttk.Entry(details_frame, width=20)),
        ("Mechanical Seal:", ttk.Entry(details_frame, width=20)),
    ]
    fields_right = [
        ("Frequency:", ttk.Entry(details_frame, width=20)),
        ("Pump Housing:", ttk.Entry(details_frame, width=20)),
        ("Pump Connection:", ttk.Entry(details_frame, width=20)),
        ("Suction:", ttk.Entry(details_frame, width=20)),
        ("Discharge:", ttk.Entry(details_frame, width=20)),
        ("Flush Arrangement:", ttk.Label(details_frame, text="Yes" if "flush" in pump["configuration"].lower() else "No", font=("Roboto", 10))),
    ]
    for i, (label, widget) in enumerate(fields_left):
        ttk.Label(details_frame, text=label, font=("Roboto", 10)).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        widget.grid(row=i, column=1, padx=5, pady=5, sticky=W)
    for i, (label, widget) in enumerate(fields_right):
        ttk.Label(details_frame, text=label, font=("Roboto", 10)).grid(row=i, column=2, padx=5, pady=5, sticky=W)
        widget.grid(row=i, column=3, padx=5, pady=5, sticky=W)

    right_frame = ttk.Frame(main_layout)
    right_frame.pack(side=LEFT, padx=15, fill=BOTH, expand=True)

    table_frame = ttk.LabelFrame(right_frame, text="Test Data", padding=10, labelwidget=ttk.Label(right_frame, text="Test Data", font=("Roboto", 12, "bold")))
    table_frame.pack(pady=(0, 10), fill=BOTH, expand=True)

    ttk.Label(table_frame, text="Flowrate (l/h)", font=("Roboto", 10)).grid(row=0, column=1, padx=5, pady=5)
    ttk.Label(table_frame, text="Pressure (bar)", font=("Roboto", 10)).grid(row=0, column=2, padx=5, pady=5)
    ttk.Label(table_frame, text="Amperage", font=("Roboto", 10)).grid(row=0, column=3, padx=5, pady=5)

    flow_entries = []
    pressure_entries = []
    amp_entries = []
    for i in range(1, 6):
        ttk.Label(table_frame, text=f"Test {i}", font=("Roboto", 10)).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        flow_entry = ttk.Entry(table_frame, width=15)
        flow_entry.grid(row=i, column=1, padx=5, pady=5)
        pressure_entry = ttk.Entry(table_frame, width=15)
        pressure_entry.grid(row=i, column=2, padx=5, pady=5)
        amp_entry = ttk.Entry(table_frame, width=15)
        amp_entry.grid(row=i, column=3, padx=5, pady=5)
        flow_entries.append(flow_entry)
        pressure_entries.append(pressure_entry)
        amp_entries.append(amp_entry)

    hydro_frame = ttk.LabelFrame(right_frame, text="Hydraulic Test", padding=10, labelwidget=ttk.Label(right_frame, text="Hydraulic Test", font=("Roboto", 12, "bold")))
    hydro_frame.pack(fill=X)

    ttk.Label(hydro_frame, text="Date of Test:", font=("Roboto", 10)).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(hydro_frame, text=datetime.now().strftime("%Y-%m-%d"), font=("Roboto", 10)).grid(row=0, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(hydro_frame, text="Duration of Test:", font=("Roboto", 10)).grid(row=1, column=0, padx=5, pady=5, sticky=W)
    duration_entry = ttk.Entry(hydro_frame, width=20)
    duration_entry.grid(row=1, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(hydro_frame, text="Test Medium:", font=("Roboto", 10)).grid(row=2, column=0, padx=5, pady=5, sticky=W)
    medium_entry = ttk.Entry(hydro_frame, width=20)
    medium_entry.grid(row=2, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(hydro_frame, text="Tested By:", font=("Roboto", 10)).grid(row=3, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(hydro_frame, text=username, font=("Roboto", 10)).grid(row=3, column=1, padx=5, pady=5, sticky=W)

    approval_frame = ttk.Frame(main_frame)
    approval_frame.grid(row=2, column=0, pady=15, sticky=W+E)
    ttk.Label(approval_frame, text="Approved By:", font=("Roboto", 10)).pack(side=LEFT, padx=10)
    name_entry = ttk.Entry(approval_frame, width=20)
    name_entry.pack(side=LEFT, padx=10)
    ttk.Label(approval_frame, text="Date:", font=("Roboto", 10)).pack(side=LEFT, padx=10)
    ttk.Label(approval_frame, text=datetime.now().strftime("%Y-%m-%d"), font=("Roboto", 10)).pack(side=LEFT, padx=10)

    footer_frame = ttk.Frame(main_frame)
    footer_frame.grid(row=3, column=0, pady=15, sticky=W+E)
    complete_btn = ttk.Button(footer_frame, text="Complete", bootstyle="success", style="large.TButton")
    complete_btn.pack(pady=(0, 5))
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    def complete_test():
        data = {
            "invoice_number": invoice_entry.get(),
            "customer": pump["customer"],
            "job_number": job_entry.get(),
            "pump_model": pump["pump_model"],
            "serial_number": serial_number,
            "impeller_diameter": impeller_entry.get(),
            "assembled_by": username,
            "motor_size": fields_left[0][1].get(),
            "motor_speed": fields_left[1][1].get(),
            "motor_volts": fields_left[2][1].get(),
            "motor_enclosure": fields_left[3][1].get(),
            "mechanical_seal": fields_left[4][1].get(),
            "frequency": fields_right[0][1].get(),
            "pump_housing": fields_right[1][1].get(),
            "pump_connection": fields_right[2][1].get(),
            "suction": fields_right[3][1].get(),
            "discharge": fields_right[4][1].get(),
            "flush_arrangement": fields_right[5][1].cget("text"),
            "date_of_test": datetime.now().strftime("%Y-%m-%d"),
            "duration_of_test": duration_entry.get(),
            "test_medium": medium_entry.get(),
            "tested_by": username,
            "flowrate": [entry.get() for entry in flow_entries],
            "pressure": [entry.get() for entry in pressure_entries],
            "amperage": [entry.get() for entry in amp_entries],
            "approved_by": name_entry.get(),
            "approval_date": datetime.now().strftime("%Y-%m-%d"),
        }

        pdf_path = generate_certificate(data, serial_number)

        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pumps SET status = 'Completed' WHERE serial_number = ?", (serial_number,))
            conn.commit()
            logger.info(f"Pump {serial_number} moved to Completed by {username}")

        refresh_callback()
        test_window.destroy()
        os.startfile(pdf_path)

    complete_btn.configure(command=complete_test)

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_testing_dashboard(root, "tester1", "testing", lambda: print("Logged off"))
    root.mainloop()