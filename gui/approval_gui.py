import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from PIL import Image, ImageTk
import os
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import threading
from export_utils import send_email, generate_pump_details_table

logger = get_logger("approval_gui")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
PDF_LOGO_PATH = os.path.join(BASE_DIR, "assets", "guth_logo.png")
FONT_PATH = os.path.join(BASE_DIR, "assets", "Roboto-Regular.ttf")
FONT_BOLD_PATH = os.path.join(BASE_DIR, "assets", "Roboto-Black.ttf")
BUILD_NUMBER = "1.0.0"

# Register Roboto fonts
pdfmetrics.registerFont(TTFont('Roboto', FONT_PATH))
pdfmetrics.registerFont(TTFont('Roboto-Black', FONT_BOLD_PATH))

def generate_graph(test_data):
    """Generate a performance graph for the pump test data."""
    try:
        flowrate = [float(f) for f in test_data["flowrate"] if f]
        pressure = [float(p) for p in test_data["pressure"] if p]
        amperage = [float(a) for a in test_data["amperage"] if a]

        if not flowrate or len(flowrate) != len(pressure) or len(flowrate) != len(amperage):
            logger.error("No valid data to plot: flowrate, pressure, or amperage lists are empty or mismatched")
            return None

        fig, ax1 = plt.subplots(figsize=(10, 6))
        desaturated_blue = (100/255, 149/255, 237/255)  # #6495ED
        desaturated_red = (255/255, 99/255, 71/255)     # #FF6347

        ax1.plot(flowrate, pressure, marker='o', color=desaturated_blue, label='Pressure (bar)')
        ax1.set_xlabel("Flowrate (l/h)", fontsize=12)
        ax1.set_ylabel("Pressure (bar)", color=desaturated_blue, fontsize=12)
        ax1.tick_params(axis='y', labelcolor=desaturated_blue, labelsize=10)
        ax1.tick_params(axis='x', labelsize=10)
        ax1.grid(True, linestyle='--', alpha=0.7)

        ax2 = ax1.twinx()
        ax2.plot(flowrate, amperage, marker='s', color=desaturated_red, label='Amperage (A)')
        ax2.set_ylabel("Amperage (A)", color=desaturated_red, fontsize=12)
        ax2.tick_params(axis='y', labelcolor=desaturated_red, labelsize=10)

        flowrate_range = max(flowrate) - min(flowrate) if flowrate else 1
        pressure_range = max(pressure) - min(pressure) if pressure else 1
        amperage_range = max(amperage) - min(amperage) if amperage else 1

        ax1.set_xlim(min(flowrate) - flowrate_range * 0.1, max(flowrate) + flowrate_range * 0.1)
        ax1.set_ylim(min(pressure) - pressure_range * 0.1, max(pressure) + pressure_range * 0.1)
        ax2.set_ylim(min(amperage) - amperage_range * 0.1, max(amperage) + amperage_range * 0.1)

        ax1.set_title(f"Performance Graph for Pump {test_data['serial_number']}", fontsize=14, pad=15)
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=10)

        plt.tight_layout()
        return fig
    except Exception as e:
        logger.error(f"Graph generation failed: {str(e)}")
        return None

def display_graph(fig):
    """Display the performance graph in a new window."""
    if not fig:
        Messagebox.show_error("Failed to generate graph. Check test data for invalid entries.", "Graph Error")
        return
    graph_window = ttk.Toplevel()
    graph_window.title("Performance Graph")
    graph_window.state("zoomed")
    canvas = FigureCanvasTkAgg(fig, master=graph_window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=BOTH, expand=True)

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
        ["Job Number:", data.get("job_number", data.get("job_number_1", "N/A"))]
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
        ["Assembly Part Number:", data.get("assembly_part_number", "N/A")],
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

    buf = io.BytesIO()
    fig, ax1 = plt.subplots(figsize=(6, 2.5))
    desaturated_blue = (100/255, 149/255, 237/255)
    desaturated_red = (255/255, 99/255, 71/255)

    flowrate_values = [float(f) if f else 0.0 for f in data["flowrate"]]
    pressure_values = [float(p) if p else 0.0 for p in data["pressure"]]
    amperage_values = [float(a) if a else 0.0 for a in data["amperage"]]

    ax1.plot(flowrate_values, pressure_values, color=desaturated_blue, linestyle='-')
    ax1.set_xlabel("Flow (L/h)", fontsize=10)
    ax1.set_ylabel("Pressure (bar)", color=desaturated_blue, fontsize=10)
    ax1.tick_params('y', colors=desaturated_blue)
    ax1.set_xlim(0, 20000)
    ax1.set_ylim(0, 3.5)
    ax1.set_xticks([0, 5000, 10000, 15000, 20000])
    ax1.set_yticks([0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5])
    ax1.grid(True, linestyle='--', alpha=0.7)

    ax2 = ax1.twinx()
    ax2.plot(flowrate_values, amperage_values, color=desaturated_red, linestyle='-')
    ax2.set_ylabel("Amperage (A)", color=desaturated_red, fontsize=10)
    ax2.tick_params('y', colors=desaturated_red)
    ax2.set_ylim(0, 7)
    ax2.set_yticks([0, 1, 2, 3, 4, 5, 6, 7])

    fig.tight_layout()
    plt.savefig(buf, format='png', dpi=400)
    buf.seek(0)
    graph = RLImage(buf, width=450, height=200)
    graph_table = Table([[graph]], colWidths=[500], style=[
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
    finally:
        buf.close()

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
    """Display pump details for approval."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT test_data FROM pumps WHERE serial_number = ?", (serial_number,))
            pump = cursor.fetchone()
            if not pump or not pump["test_data"]:
                logger.warning(f"No test data found for serial_number: {serial_number}")
                Messagebox.show_warning("No Data", f"No test data found for pump {serial_number}")
                return
            test_data = json.loads(pump["test_data"])
    except Exception as e:
        logger.error(f"Failed to load test data: {str(e)}")
        Messagebox.show_error("Error", f"Failed to load pump data: {str(e)}")
        return

    details_window = ttk.Toplevel(parent)
    details_window.title(f"Pump Details - {serial_number}")
    details_window.state("zoomed")

    header_frame = ttk.Frame(details_window, style="white.TFrame")
    header_frame.pack(fill=X, pady=(0, 10), ipady=10)
    ttk.Label(header_frame, text=f"Pump Details - {serial_number}", font=("Roboto", 14, "bold")).pack(anchor=W, padx=10)
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).resize((int(Image.open(LOGO_PATH).width * 0.5), int(Image.open(LOGO_PATH).height * 0.5)), Image.Resampling.LANCZOS)
            logo = ImageTk.PhotoImage(img)
            ttk.Label(header_frame, image=logo).pack(side=RIGHT, padx=10)
            header_frame.image = logo
        except Exception as e:
            logger.error(f"Logo load failed: {str(e)}")

    canvas = ttk.Canvas(details_window)
    scrollbar = ttk.Scrollbar(details_window, orient=VERTICAL, command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)
    scrollbar.pack(side=RIGHT, fill=Y)

    def on_mouse_wheel(event):
        canvas.yview_scroll(-1 * (event.delta // 120), "units")

    canvas.bind("<MouseWheel>", on_mouse_wheel)
    details_window.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind("<MouseWheel>"), details_window.destroy()))

    main_layout = ttk.Frame(scrollable_frame)
    main_layout.pack(fill=BOTH, expand=True, padx=10, pady=10)

    left_frame = ttk.Frame(main_layout)
    left_frame.pack(side=LEFT, fill=Y, padx=(0, 15))

    right_frame = ttk.Frame(main_layout)
    right_frame.pack(side=LEFT, fill=Y, padx=(15, 0))

    labels_entries = {}
    fields = [
        "invoice_number", "customer", "job_number", "assembly_part_number", "pump_model", "serial_number",
        "impeller_diameter", "assembled_by", "motor_size", "motor_speed", "motor_volts",
        "motor_enclosure", "mechanical_seal", "frequency", "pump_housing", "pump_connection",
        "suction", "discharge", "flush_arrangement", "date_of_test", "duration_of_test",
        "test_medium", "tested_by"
    ]

    mid_point = len(fields) // 2
    left_fields = fields[:mid_point]
    right_fields = fields[mid_point:]

    for i, field in enumerate(left_fields):
        ttk.Label(left_frame, text=f"{field.replace('_', ' ').title()}:", font=("Roboto", 10)).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        entry = ttk.Entry(left_frame, width=30)
        entry.grid(row=i, column=1, padx=5, pady=5, sticky=W)
        entry.insert(0, test_data.get(field, ""))
        labels_entries[field] = entry

    for i, field in enumerate(right_fields):
        ttk.Label(right_frame, text=f"{field.replace('_', ' ').title()}:", font=("Roboto", 10)).grid(row=i, column=0, padx=5, pady=5, sticky=W)
        entry = ttk.Entry(right_frame, width=30)
        entry.grid(row=i, column=1, padx=5, pady=5, sticky=W)
        entry.insert(0, test_data.get(field, ""))
        labels_entries[field] = entry

    table_frame = ttk.LabelFrame(right_frame, text="Test Data", padding=10)
    table_frame.grid(row=len(right_fields), column=0, columnspan=2, pady=10, sticky=W+E)

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

    button_frame = ttk.Frame(scrollable_frame)
    button_frame.pack(pady=10)

    def save_changes():
        """Save changes to pump test data."""
        updated_test_data = {field: entry.get() for field, entry in labels_entries.items()}
        updated_test_data["flowrate"] = [entry.get() for entry in flow_entries]
        updated_test_data["pressure"] = [entry.get() for entry in pressure_entries]
        updated_test_data["amperage"] = [entry.get() for entry in amp_entries]

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
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE pumps SET test_data = ? WHERE serial_number = ?",
                               (json.dumps(updated_test_data), serial_number))
                conn.commit()
                logger.info(f"Test data updated for pump {serial_number} by {username}")
            refresh_callback()
            details_window.destroy()
        except Exception as e:
            logger.error(f"Failed to save changes: {str(e)}")
            Messagebox.show_error("Error", f"Failed to save changes: {str(e)}")

    def view_graph():
        """Display the performance graph."""
        fig = generate_graph(test_data)
        display_graph(fig)

    def approve_pump():
        """Approve the pump and generate/send certificate."""
        updated_test_data = {field: entry.get() for field, entry in labels_entries.items()}
        updated_test_data["flowrate"] = [entry.get() for entry in flow_entries]
        updated_test_data["pressure"] = [entry.get() for entry in pressure_entries]
        updated_test_data["amperage"] = [entry.get() for entry in amp_entries]
        updated_test_data["approved_by"] = username
        updated_test_data["approval_date"] = datetime.now().strftime("%Y-%m-%d")

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
                if requested_by_data and requested_by_data["requested_by"]:
                    requested_by_username = requested_by_data["requested_by"]
                    cursor.execute("SELECT email FROM users WHERE username = ?", (requested_by_username,))
                    requested_by_email = cursor.fetchone()
                    if requested_by_email and requested_by_email["email"]:
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
                            args=(requested_by_email["email"], subject, greeting, body_content, footer, pdf_path),
                            daemon=True
                        ).start()
                        logger.info(f"Approval email sent to {requested_by_email['email']} for pump {serial_number}")
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

    ttk.Button(button_frame, text="Save Changes", command=save_changes, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Button(button_frame, text="View Graph", command=view_graph, bootstyle="info", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Button(button_frame, text="Approve", command=approve_pump, bootstyle="success", style="large.TButton").pack(side=LEFT, padx=5)
    ttk.Button(button_frame, text="Close", command=details_window.destroy, bootstyle="secondary", style="large.TButton").pack(side=LEFT, padx=5)

    footer_frame = ttk.Frame(details_window)
    footer_frame.pack(side=BOTTOM, pady=10, fill=X)
    ttk.Label(footer_frame, text="\u00A9 Guth South Africa", font=("Roboto", 10)).pack(expand=True)
    ttk.Label(footer_frame, text=f"Build {BUILD_NUMBER}", font=("Roboto", 10)).pack(expand=True)

def show_approval_dashboard(root, username, role, logout_callback):
    """Display the approval dashboard."""
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
        """Refresh the list of pumps pending approval."""
        tree.delete(*tree.get_children())
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT serial_number, assembly_part_number, customer, branch, pump_model, configuration, requested_by AS originator
                    FROM pumps WHERE status = 'Pending Approval'
                """)
                for pump in cursor.fetchall():
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