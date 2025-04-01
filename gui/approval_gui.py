import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageTk
import os
import sys
from database import get_db_connection
from utils.config import get_logger
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch  # Explicitly import inch to fix warnings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import threading
from export_utils import send_email, generate_pump_details_table

logger = get_logger("approval_gui")

# Determine the base directory for bundled resources
if getattr(sys, 'frozen', False):
    # Running as a bundled executable (PyInstaller)
    BASE_DIR = sys._MEIPASS
else:
    # Running in development mode
    BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"

LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
PDF_LOGO_PATH = os.path.join(BASE_DIR, "assets", "guth_logo.png")
FONT_PATH = os.path.join(BASE_DIR, "assets", "Roboto-Regular.ttf")
FONT_BOLD_PATH = os.path.join(BASE_DIR, "assets", "Roboto-Black.ttf")
BUILD_NUMBER = "1.0.0"

# Register Roboto fonts with error handling
try:
    pdfmetrics.registerFont(TTFont('Roboto', FONT_PATH))
    pdfmetrics.registerFont(TTFont('Roboto-Black', FONT_BOLD_PATH))
    logger.info("Roboto fonts registered successfully")
except Exception as e:
    error_msg = f"Failed to register fonts: {str(e)}"
    logger.error(error_msg)
    raise Exception(error_msg)

def generate_test_graph(test_data, output_path=None, for_gui=False):
    """Generate a graph of test data (amperage and pressure vs. flowrate) for GUI or PDF."""
    try:
        # Collect valid data points
        flowrate = [float(f) if f.strip() else 0.0 for f in test_data["flowrate"]]
        pressure = [float(p) if p.strip() else 0.0 for p in test_data["pressure"]]
        amperage = [float(a) if a.strip() else 0.0 for a in test_data["amperage"]]

        # Filter out points where all values are 0
        valid_data = [(f, p, a) for f, p, a in zip(flowrate, pressure, amperage) if f or p or a]
        if not valid_data:
            logger.debug("No valid data to plot")
            return None

        flowrate, pressure, amperage = zip(*valid_data)
        sorted_data = sorted(zip(flowrate, pressure, amperage), key=lambda x: x[0])
        flowrate, pressure, amperage = zip(*sorted_data) if sorted_data else ([], [], [])

        # Set figure size based on context (GUI or PDF)
        figsize = (4, 2) if for_gui else (6, 3)
        fig, ax1 = plt.subplots(figsize=figsize)
        desaturated_blue = (100/255, 149/255, 237/255)  # #6495ED
        desaturated_red = (255/255, 99/255, 71/255)     # #FF6347

        # Plot pressure vs. flowrate
        ax1.plot(flowrate, pressure, marker='o', color=desaturated_blue, label='Pressure (bar)', linewidth=1.5)
        ax1.set_xlabel("Flowrate (l/h)", fontsize=8)
        ax1.set_ylabel("Pressure (bar)", color=desaturated_blue, fontsize=8)
        ax1.tick_params(axis='y', labelcolor=desaturated_blue, labelsize=6)
        ax1.tick_params(axis='x', labelsize=6)
        ax1.grid(True, linestyle='--', alpha=0.7)

        # Plot amperage vs. flowrate on twin axis
        ax2 = ax1.twinx()
        ax2.plot(flowrate, amperage, marker='s', color=desaturated_red, label='Amperage (A)', linewidth=1.5)
        ax2.set_ylabel("Amperage (A)", color=desaturated_red, fontsize=8)
        ax2.tick_params(axis='y', labelcolor=desaturated_red, labelsize=6)

        # Dynamic axis limits with explicit list handling to avoid linter warnings
        positive_flowrate = [f for f in flowrate if f > 0]
        flow_min = min(positive_flowrate) if positive_flowrate else 0
        flow_max = max(flowrate) if flowrate else 1000

        positive_pressure = [p for p in pressure if p > 0]
        press_min = min(positive_pressure) if positive_pressure else 0
        press_max = max(pressure) if pressure else 5

        positive_amperage = [a for a in amperage if a > 0]
        amp_min = min(positive_amperage) if positive_amperage else 0
        amp_max = max(amperage) if amperage else 10

        flow_range = flow_max - flow_min if flow_max > flow_min else 100
        press_range = press_max - press_min if press_max > press_min else 1
        amp_range = amp_max - amp_min if amp_max > amp_min else 1

        ax1.set_xlim(max(0, flow_min - flow_range * 0.1), flow_max + flow_range * 0.1)
        ax1.set_ylim(max(0, press_min - press_range * 0.1), press_max + press_range * 0.1)
        ax2.set_ylim(max(0, amp_min - amp_range * 0.1), amp_max + amp_range * 0.1)

        ax1.set_title("Pump Test Results", fontsize=10, pad=5)
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=6)

        plt.tight_layout()
        if output_path:
            plt.savefig(output_path, format='png', dpi=100, bbox_inches="tight")
            plt.close()
            logger.info(f"Generated test graph at {output_path}")
            return output_path
        return fig
    except Exception as e:
        logger.error(f"Graph generation failed: {str(e)}")
        return None

def generate_certificate(data, serial_number):
    """Generate a pump test certificate PDF."""
    config = load_config()
    cert_dir = config["document_dirs"]["certificate"]
    os.makedirs(cert_dir, exist_ok=True)
    pdf_path = os.path.join(cert_dir, f"Pump_Test_Report_{serial_number}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    custom_style = ParagraphStyle(name='Custom', fontName='Roboto', fontSize=8)
    heading_style = ParagraphStyle(name='Heading', fontName='Roboto-Black', fontSize=14, alignment=0)
    subheading_style = ParagraphStyle(name='Subheading', fontName='Roboto-Black', fontSize=9, alignment=1)

    story = []
    if os.path.exists(PDF_LOGO_PATH):
        try:
            logo = RLImage(PDF_LOGO_PATH, width=120, height=60)
            logo.hAlign = 'RIGHT'
            story.append(logo)
            story.append(Spacer(1, 3))
        except Exception as e:
            logger.error(f"Failed to add logo to certificate: {str(e)}")

    story.append(Paragraph("PUMP TEST REPORT", heading_style))
    story.append(Spacer(1, 3))

    top_data = [
        ["Invoice Number:", data.get("invoice_number", "N/A")],
        ["Customer:", data.get("customer", "N/A")],
        ["Job Number:", data.get("job_number", "N/A")]
    ]
    top_table = Table(top_data, colWidths=[125, 375], style=[
        ('FONTNAME', (0, 0), (-1, -1), 'Roboto'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('LEADING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ])
    story.append(top_table)
    story.append(Spacer(1, 3))

    fab_data = [
        ["FABRICATION", ""],
        ["Assembly Number:", data.get("assembly_part_number", "N/A")],
        ["Pump Model:", data.get("pump_model", "N/A")],
        ["Serial Number:", serial_number],
        ["Impeller Diameter:", data.get("impeller_diameter", "N/A")],
        ["Assembled By:", data.get("assembled_by", "N/A")],
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

    hydro_data = [
        ["HYDRAULIC TEST", ""],
        ["Date of Test:", data.get("date_of_test", "N/A")],
        ["Duration of Test:", data.get("duration_of_test", "N/A")],
        ["Test Medium:", data.get("test_medium", "N/A")],
        ["Tested By:", data.get("tested_by", "N/A")],
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

    side_by_side_table = Table([[fab_table, hydro_table]], colWidths=[250, 250], style=[
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ])
    story.append(side_by_side_table)
    story.append(Spacer(1, 3))

    details_data = [
        ["DETAILS", "", "", ""],
        ["Motor Size:", data.get("motor_size", "N/A"), "Frequency:", data.get("frequency", "N/A")],
        ["Motor Speed:", data.get("motor_speed", "N/A"), "Pump Housing:", data.get("pump_housing", "N/A")],
        ["Motor Volts:", data.get("motor_volts", "N/A"), "Pump Connection:", data.get("pump_connection", "N/A")],
        ["Motor Enclosure:", data.get("motor_enclosure", "N/A"), "Suction:", data.get("suction", "N/A")],
        ["Mechanical Seal:", data.get("mechanical_seal", "N/A"), "Discharge:", data.get("discharge", "N/A")],
        ["", "", "Flush Arrangement:", data.get("flush_arrangement", "N/A")],
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
    story.append(details_table)
    story.append(Spacer(1, 3))

    story.append(Paragraph("TEST RESULTS", subheading_style))
    story.append(Spacer(1, 3))

    test_results_data = [["Test", "Flowrate (L/h)", "Pressure (bar)", "Amperage (A)"]]
    for i in range(5):
        test_results_data.append([
            f"Test {i+1}",
            data["flowrate"][i] if i < len(data["flowrate"]) else "",
            data["pressure"][i] if i < len(data["pressure"]) else "",
            data["amperage"][i] if i < len(data["amperage"]) else ""
        ])
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
    story.append(test_results_table)
    story.append(Spacer(1, 3))

    # Embed graph in PDF
    graph_path = generate_test_graph(data, output_path=f"temp_graph_{serial_number}.png")
    if graph_path and os.path.exists(graph_path):
        graph = RLImage(graph_path, width=6*inch, height=3*inch)
        graph_table = Table([[graph]], colWidths=[6*inch], style=[
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ])
        story.append(graph_table)
        story.append(Spacer(1, 3))

    approval_data = [
        ["APPROVAL", "", "", ""],
        ["Approved By:", data.get("approved_by", "N/A"), "", ""],
        ["Date:", data.get("approval_date", "N/A"), "", ""],
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
    story.append(approval_table)

    try:
        doc.build(story)
        logger.info(f"Certificate generated: {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"Failed to generate certificate: {str(e)}")
        raise

def load_config():
    """Load configuration from config.json."""
    config_path = os.path.join(BASE_DIR, "config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        return {"document_dirs": {"certificate": os.path.join(BASE_DIR, "certificates")}}

def show_pump_details_window(parent, serial_number, username, refresh_callback):
    """Display pump details for approval, mirroring Tester dashboard with live graph."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT test_data FROM pumps WHERE serial_number = ?", (serial_number,))
            pump = cursor.fetchone()
            if not pump or not pump[0]:
                logger.warning(f"No test data found for serial_number: {serial_number}")
                Messagebox.show_warning("No Data", f"No test data found for pump {serial_number}")
                return
            test_data = json.loads(pump[0])

            cursor.execute("""
                SELECT serial_number, customer, pump_model, configuration, requested_by, branch, impeller_size,
                       connection_type, pressure_required, flow_rate_required, custom_motor, flush_seal_housing,
                       assembly_part_number
                FROM pumps WHERE serial_number = ?
            """, (serial_number,))
            columns = [desc[0] for desc in cursor.description]
            pump_tuple = cursor.fetchone()
            if not pump_tuple:
                logger.warning(f"No pump found for serial_number: {serial_number}")
                return
            pump = dict(zip(columns, pump_tuple))
            cursor.execute("SELECT username, email FROM users WHERE username = ?", (pump["requested_by"],))
            originator = cursor.fetchone()
    except Exception as e:
        logger.error(f"Failed to load pump data: {str(e)}")
        Messagebox.show_error("Error", f"Failed to load pump data: {str(e)}")
        return

    details_window = ttk.Toplevel(parent)
    details_window.title(f"Pump Details - {serial_number}")
    details_window.state("zoomed")

    container_frame = ttk.Frame(details_window)
    container_frame.pack(fill=BOTH, expand=True)

    header_frame = ttk.Frame(container_frame, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.5), int(Image.open(LOGO_PATH).height * 0.5)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
        except Exception as e:
            logger.error(f"Details window logo load failed: {str(e)}")
    ttk.Label(header_frame, text="Pump Approval Details", font=("Roboto", 14, "bold")).pack(anchor=W, padx=10)

    content_frame = ttk.Frame(container_frame)
    content_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    canvas = ttk.Canvas(content_frame)
    scrollbar = ttk.Scrollbar(content_frame, orient=VERTICAL, command=canvas.yview)
    main_frame = ttk.Frame(canvas)
    main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=main_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar.pack(side=RIGHT, fill=Y)

    def on_mouse_wheel(event):
        if canvas.winfo_exists():
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

    canvas.bind("<MouseWheel>", on_mouse_wheel)
    def on_close():
        try:
            if canvas.winfo_exists():
                canvas.unbind("<MouseWheel>")
            details_window.destroy()
        except Exception as e:
            logger.debug(f"Minor error during window close: {str(e)}")
    details_window.protocol("WM_DELETE_WINDOW", on_close)

    top_frame = ttk.Frame(main_frame)
    top_frame.grid(row=0, column=0, pady=(0, 15), sticky=W)

    ttk.Label(top_frame, text="Invoice Number:", font=("Roboto", 10)).grid(row=0, column=0, padx=10, pady=2, sticky=W)
    invoice_entry = ttk.Entry(top_frame, width=30)
    invoice_entry.insert(0, test_data.get("invoice_number", ""))
    invoice_entry.grid(row=0, column=1, padx=10, pady=2, sticky=W)

    ttk.Label(top_frame, text="Customer:", font=("Roboto", 10)).grid(row=1, column=0, padx=10, pady=2, sticky=W)
    ttk.Label(top_frame, text=pump["customer"], font=("Roboto", 10)).grid(row=1, column=1, padx=10, pady=2, sticky=W)

    ttk.Label(top_frame, text="Job Number:", font=("Roboto", 10)).grid(row=2, column=0, padx=10, pady=2, sticky=W)
    job_entry = ttk.Entry(top_frame, width=30)
    job_entry.insert(0, test_data.get("job_number", ""))
    job_entry.grid(row=2, column=1, padx=10, pady=2, sticky=W)

    main_layout = ttk.Frame(main_frame)
    main_layout.grid(row=1, column=0, pady=15, sticky=W+E)

    left_frame = ttk.Frame(main_layout)
    left_frame.pack(side=LEFT, padx=15, fill=Y)

    fab_frame = ttk.LabelFrame(left_frame, text="Fabrication", padding=10)
    fab_frame.pack(pady=(0, 10), fill=X)

    ttk.Label(fab_frame, text="Assembly Part Number:", font=("Roboto", 10)).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=pump.get("assembly_part_number", "N/A"), font=("Roboto", 10)).grid(row=0, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Pump Model:", font=("Roboto", 10)).grid(row=1, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=pump["pump_model"], font=("Roboto", 10)).grid(row=1, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Serial Number:", font=("Roboto", 10)).grid(row=2, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=serial_number, font=("Roboto", 10)).grid(row=2, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Impeller Diameter:", font=("Roboto", 10)).grid(row=3, column=0, padx=5, pady=5, sticky=W)
    impeller_entry = ttk.Entry(fab_frame, width=20)
    impeller_entry.insert(0, test_data.get("impeller_diameter", pump.get("impeller_size", "")))
    impeller_entry.grid(row=3, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(fab_frame, text="Assembled By:", font=("Roboto", 10)).grid(row=4, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(fab_frame, text=test_data.get("assembled_by", username), font=("Roboto", 10)).grid(row=4, column=1, padx=5, pady=5, sticky=W)

    details_frame = ttk.LabelFrame(left_frame, text="Details", padding=10)
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
        ("Flush Arrangement:", ttk.Entry(details_frame, width=20)),
    ]
    for i, (label, widget) in enumerate(fields_left):
        ttk.Label(details_frame, text=label, font=("Roboto", 10)).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        widget.grid(row=i, column=1, padx=5, pady=5, sticky=W)
        widget.insert(0, test_data.get(label.lower().replace(":", "").replace(" ", "_"), ""))
    for i, (label, widget) in enumerate(fields_right):
        ttk.Label(details_frame, text=label, font=("Roboto", 10)).grid(row=i, column=2, padx=5, pady=5, sticky=W)
        widget.grid(row=i, column=3, padx=5, pady=5, sticky=W)
        widget.insert(0, test_data.get(label.lower().replace(":", "").replace(" ", "_"), "Yes" if "flush" in pump["configuration"].lower() else "No" if label == "Flush Arrangement:" else ""))

    right_frame = ttk.Frame(main_layout)
    right_frame.pack(side=LEFT, padx=15, fill=Y)

    test_graph_frame = ttk.Frame(right_frame)
    test_graph_frame.pack(fill=X, pady=(0, 10))

    table_frame = ttk.LabelFrame(test_graph_frame, text="Test Data", padding=10)
    table_frame.pack(side=LEFT, fill=Y)

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
        flow_entry.insert(0, test_data["flowrate"][i-1] if i-1 < len(test_data["flowrate"]) else "")
        pressure_entry.insert(0, test_data["pressure"][i-1] if i-1 < len(test_data["pressure"]) else "")
        amp_entry.insert(0, test_data["amperage"][i-1] if i-1 < len(test_data["amperage"]) else "")
        flow_entries.append(flow_entry)
        pressure_entries.append(pressure_entry)
        amp_entries.append(amp_entry)

    graph_frame = ttk.LabelFrame(test_graph_frame, text="Graph Preview", padding=5)
    graph_frame.pack(side=LEFT, fill=Y, padx=(10, 0))

    def update_graph(*args):
        current_data = {
            "flowrate": [entry.get() for entry in flow_entries],
            "pressure": [entry.get() for entry in pressure_entries],
            "amperage": [entry.get() for entry in amp_entries],
            "serial_number": serial_number
        }
        fig = generate_test_graph(current_data, for_gui=True)
        for widget in graph_frame.winfo_children():
            widget.destroy()
        if fig:
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=BOTH, expand=True)
        else:
            ttk.Label(graph_frame, text="No valid data to plot", font=("Roboto", 10)).pack(expand=True)

    update_graph()
    for entry in flow_entries + pressure_entries + amp_entries:
        entry.bind("<KeyRelease>", update_graph)

    hydro_frame = ttk.LabelFrame(right_frame, text="Hydraulic Test", padding=10)
    hydro_frame.pack(fill=X)

    ttk.Label(hydro_frame, text="Date of Test:", font=("Roboto", 10)).grid(row=0, column=0, padx=5, pady=5, sticky=W)
    date_entry = ttk.Entry(hydro_frame, width=20)
    date_entry.insert(0, test_data.get("date_of_test", datetime.now().strftime("%Y-%m-%d")))
    date_entry.grid(row=0, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(hydro_frame, text="Duration of Test:", font=("Roboto", 10)).grid(row=1, column=0, padx=5, pady=5, sticky=W)
    duration_entry = ttk.Entry(hydro_frame, width=20)
    duration_entry.insert(0, test_data.get("duration_of_test", ""))
    duration_entry.grid(row=1, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(hydro_frame, text="Test Medium:", font=("Roboto", 10)).grid(row=2, column=0, padx=5, pady=5, sticky=W)
    medium_entry = ttk.Entry(hydro_frame, width=20)
    medium_entry.insert(0, test_data.get("test_medium", ""))
    medium_entry.grid(row=2, column=1, padx=5, pady=5, sticky=W)

    ttk.Label(hydro_frame, text="Tested By:", font=("Roboto", 10)).grid(row=3, column=0, padx=5, pady=5, sticky=W)
    ttk.Label(hydro_frame, text=test_data.get("tested_by", username), font=("Roboto", 10)).grid(row=3, column=1, padx=5, pady=5, sticky=W)

    approval_frame = ttk.Frame(main_frame)
    approval_frame.grid(row=2, column=0, pady=15, sticky=W+E)
    ttk.Label(approval_frame, text="Date:", font=("Roboto", 10)).pack(side=LEFT, padx=10)
    ttk.Label(approval_frame, text=datetime.now().strftime("%Y-%m-%d"), font=("Roboto", 10)).pack(side=LEFT, padx=10)

    button_frame = ttk.Frame(container_frame)
    button_frame.pack(side=BOTTOM, pady=15, anchor=W)

    def retest_pump():
        updated_test_data = {
            "invoice_number": invoice_entry.get(),
            "customer": pump["customer"],
            "job_number": job_entry.get(),
            "assembly_part_number": pump.get("assembly_part_number", "N/A"),
            "pump_model": pump["pump_model"],
            "serial_number": serial_number,
            "impeller_diameter": impeller_entry.get(),
            "assembled_by": test_data.get("assembled_by", username),
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
            "flush_arrangement": fields_right[5][1].get(),
            "date_of_test": date_entry.get(),
            "duration_of_test": duration_entry.get(),
            "test_medium": medium_entry.get(),
            "tested_by": test_data.get("tested_by", username),
            "flowrate": [entry.get() for entry in flow_entries],
            "pressure": [entry.get() for entry in pressure_entries],
            "amperage": [entry.get() for entry in amp_entries],
        }
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE pumps SET status = 'Testing', test_data = ? WHERE serial_number = ?",
                               (json.dumps(updated_test_data), serial_number))
                conn.commit()
                logger.info(f"Pump {serial_number} sent back to Testing by {username}")
            refresh_callback()
            details_window.destroy()
            Messagebox.show_info(f"Pump {serial_number} sent back to Testing.", "Retest Initiated")
        except Exception as e:
            logger.error(f"Failed to send pump back to Testing: {str(e)}")
            Messagebox.show_error("Error", f"Failed to retest pump: {str(e)}")

    def approve_pump():
        updated_test_data = {
            "invoice_number": invoice_entry.get(),
            "customer": pump["customer"],
            "job_number": job_entry.get(),
            "assembly_part_number": pump.get("assembly_part_number", "N/A"),
            "pump_model": pump["pump_model"],
            "serial_number": serial_number,
            "impeller_diameter": impeller_entry.get(),
            "assembled_by": test_data.get("assembled_by", username),
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
            "flush_arrangement": fields_right[5][1].get(),
            "date_of_test": date_entry.get(),
            "duration_of_test": duration_entry.get(),
            "test_medium": medium_entry.get(),
            "tested_by": test_data.get("tested_by", username),
            "flowrate": [entry.get() for entry in flow_entries],
            "pressure": [entry.get() for entry in pressure_entries],
            "amperage": [entry.get() for entry in amp_entries],
            "approved_by": username,
            "approval_date": datetime.now().strftime("%Y-%m-%d"),
        }
        try:
            for i in range(5):
                if updated_test_data["flowrate"][i]:
                    float(updated_test_data["flowrate"][i])
                if updated_test_data["pressure"][i]:
                    float(updated_test_data["pressure"][i])
                if updated_test_data["amperage"][i]:
                    float(updated_test_data["amperage"][i])
        except ValueError:
            Messagebox.show_error("Flowrate, Pressure, and Amperage must be numeric values.", "Validation Error")
            return

        try:
            pdf_path = generate_certificate(updated_test_data, serial_number)
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT requested_by FROM pumps WHERE serial_number = ?", (serial_number,))
                requested_by_data = cursor.fetchone()
                if requested_by_data and requested_by_data[0]:
                    requested_by_username = requested_by_data[0]
                    cursor.execute("SELECT email FROM users WHERE username = ?", (requested_by_username,))
                    requested_by_email = cursor.fetchone()
                    if requested_by_email and requested_by_email[0]:
                        subject = f"Pump {serial_number} Approved"
                        greeting = f"Dear {requested_by_username},"
                        body_content = f"""
                            <p>We are pleased to inform you that the pump with serial number <strong>{serial_number}</strong> has been approved on {updated_test_data["approval_date"]}.</p>
                            {generate_pump_details_table(updated_test_data)}
                            <p>Please find the attached pump certificate for your records.</p>
                        """
                        footer = "Best regards,<br>Guth Pump Registry Approval Team"
                        threading.Thread(
                            target=send_email,
                            args=(requested_by_email[0], subject, greeting, body_content, footer, pdf_path),
                            daemon=True
                        ).start()
                        logger.info(f"Approval email sent to {requested_by_email[0]} for pump {serial_number}")
                    else:
                        logger.warning(f"No email found for requested_by user {requested_by_username}")
                        Messagebox.show_warning("Email Not Sent", f"No email address found for {requested_by_username}.")
                else:
                    logger.warning(f"No requested_by user found for pump {serial_number}")
                    Messagebox.show_warning("Email Not Sent", "No requested_by user found.")

                cursor.execute("UPDATE pumps SET status = 'Completed', test_data = ? WHERE serial_number = ?",
                               (json.dumps(updated_test_data), serial_number))
                conn.commit()
                logger.info(f"Pump {serial_number} approved by {username}")

            refresh_callback()
            details_window.destroy()
            os.startfile(pdf_path)
            Messagebox.show_info(f"Pump {serial_number} approved.\nCertificate saved at: {pdf_path}", "Approval Success")
        except Exception as e:
            logger.error(f"Failed to approve pump: {str(e)}")
            Messagebox.show_error("Error", f"Failed to approve pump: {str(e)}")

    ttk.Button(button_frame, text="Retest", command=retest_pump, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Button(button_frame, text="Approve", command=approve_pump, bootstyle="success", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Button(button_frame, text="Close", command=details_window.destroy, bootstyle="secondary", style="large.TButton").pack(side=LEFT, padx=5)

    footer_frame = ttk.Frame(container_frame)
    footer_frame.pack(side=BOTTOM, pady=10, fill=X)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(expand=True)
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack(expand=True)

def show_approval_dashboard(root, username, role, logout_callback):
    root.state('zoomed')
    for widget in root.winfo_children():
        widget.destroy()

    main_frame = ttk.Frame(root)
    main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    header_frame = ttk.Frame(main_frame, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 20), ipady=20)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 1.0), int(Image.open(LOGO_PATH).height * 1.0)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
        except Exception as e:
            logger.error(f"Logo load failed: {str(e)}")
    ttk.Label(header_frame, text=f"Welcome, {username}", font=("Roboto", 18, "bold")).pack(anchor=W, padx=10)
    ttk.Label(header_frame, text="Approval Dashboard", font=("Roboto", 12)).pack(anchor=W, padx=10)

    approval_list_frame = ttk.LabelFrame(main_frame, text="Pumps for Approval", padding=10)
    approval_list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    columns = ("Serial Number", "Assembly Part Number", "Customer", "Branch", "Pump Model", "Configuration", "Originator")
    tree = ttk.Treeview(approval_list_frame, columns=columns, show="headings", height=10)
    for col in columns:
        tree.heading(col, text=col, anchor=W)
        tree.column(col, width=150, anchor=W)
    tree.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar = ttk.Scrollbar(approval_list_frame, orient=VERTICAL, command=tree.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    tree.configure(yscrollcommand=scrollbar.set)

    def refresh_approval_list():
        tree.delete(*tree.get_children())
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT serial_number, assembly_part_number, customer, branch, pump_model, configuration, requested_by AS originator
                    FROM pumps WHERE status = 'Pending Approval'
                """)
                columns = [desc[0] for desc in cursor.description]
                for row in cursor.fetchall():
                    pump = dict(zip(columns, row))
                    tree.insert("", END, values=(pump["serial_number"], pump["assembly_part_number"] or "N/A",
                                                 pump["customer"], pump["branch"], pump["pump_model"],
                                                 pump["configuration"], pump["originator"]))
            logger.info("Refreshed approval list")
        except Exception as e:
            logger.error(f"Failed to refresh approval list: {str(e)}")
            Messagebox.show_error("Error", f"Failed to load pumps: {str(e)}")

    refresh_approval_list()
    tree.bind("<Double-1>", lambda event: show_pump_details_window(root, tree.item(tree.selection())["values"][0], username, refresh_approval_list) if tree.selection() else None)

    pump_frame = ttk.LabelFrame(main_frame, text="Actions", padding=10)
    pump_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    ttk.Button(pump_frame, text="Logoff", command=logout_callback, bootstyle="secondary", style="large.TButton").pack(pady=5)

    footer_frame = ttk.Frame(main_frame)
    footer_frame.pack(side=BOTTOM, pady=10)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack()
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack()

    return main_frame

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    show_approval_dashboard(root, "testuser", "Approval", lambda: print("Logout"))
    root.mainloop()