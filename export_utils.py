import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from utils.config import get_logger
import json
from datetime import datetime
from PIL import Image as PILImage
import matplotlib.pyplot as plt

logger = get_logger("export_utils")
EXPORT_UTILS_VERSION = "2025-03-30_v5"
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")

def load_config():
    """Load configuration from config.json."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {CONFIG_PATH}: {str(e)}")
        raise FileNotFoundError(f"Config file not found or invalid at {CONFIG_PATH}")

def generate_test_graph(test_data, output_path="temp_graph.png"):
    """Generate a graph of test data (amperage and pressure)."""
    try:
        plt.figure(figsize=(6, 3))
        # Filter out empty entries and convert to float, using test numbers as x-axis
        time = [i + 1 for i, x in enumerate(test_data["amperage"]) if x.strip()]
        amperage = [float(x) for x in test_data["amperage"] if x.strip()]
        pressure = [float(x) for x in test_data["pressure"] if x.strip()]

        if amperage:
            plt.plot(time, amperage, label="Amperage (A)", color="blue", marker="o")
        if pressure:
            plt.plot(time, pressure, label="Pressure (bar)", color="red", marker="o")
        plt.xlabel("Test Number")
        plt.ylabel("Value")
        plt.title("Pump Test Results")
        plt.legend()
        plt.grid(True)
        plt.savefig(output_path, dpi=100, bbox_inches="tight")
        plt.close()
        logger.info(f"Generated test graph at {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate test graph: {str(e)}")
        return None

def send_email(to_email, subject, greeting, body_content, footer="", *attachment_paths):
    """Send an email with multiple optional attachments using SMTP settings from config.json."""
    config = load_config()
    email_settings = config.get("email_settings", {})
    smtp_server = email_settings.get("smtp_host", "")
    smtp_port = int(email_settings.get("smtp_port", 587))
    sender_email = email_settings.get("sender_email", "")
    smtp_username = email_settings.get("smtp_username", "")
    smtp_password = email_settings.get("smtp_password", "")
    use_tls = email_settings.get("use_tls", True)

    if not all([smtp_server, smtp_port, sender_email]):
        logger.error("Required email settings (smtp_host, smtp_port, sender_email) not found in config.json")
        raise ValueError("Required email settings not set in config.json")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <div style="text-align: center;">
                    <img src="file://{LOGO_PATH}" alt="Guth Logo" style="max-width: 150px; height: auto;" />
                </div>
                <h2 style="color: #2c3e50; text-align: center;">{subject}</h2>
                <p>{greeting}</p>
                {body_content}
                <p style="margin-top: 20px;">{footer}</p>
                <hr style="border: 0; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #777; text-align: center;">© Guth South Africa | Version {EXPORT_UTILS_VERSION}</p>
            </div>
        </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    for attachment_path in attachment_paths:
        if os.path.exists(attachment_path):
            try:
                with open(attachment_path, 'rb') as f:
                    attachment = MIMEApplication(f.read(), _subtype="pdf")
                    attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                    msg.attach(attachment)
                logger.info(f"Attached file to email: {attachment_path}")
            except Exception as e:
                logger.error(f"Failed to attach {attachment_path}: {str(e)}")
        else:
            logger.warning(f"Attachment not found: {attachment_path}")

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if use_tls:
                server.starttls()
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        logger.info(f"Email sent to {to_email} with subject '{subject}' and {len(attachment_paths)} attachments")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise

def generate_pdf_notification(serial_number, data, title="Pump Assembly Notification", output_path=None):
    """Generate a PDF document with pump details, BOM items, and test data graph if applicable."""
    if output_path is None:
        config = load_config()
        output_dir = config["document_dirs"].get("certificate", os.path.join(BASE_DIR, "certificates"))
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{serial_number}_{title.replace(' ', '_')}.pdf")

    doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    title_style.alignment = 1
    heading2_style = styles["Heading2"]
    normal_style = styles["Normal"]
    cell_style = ParagraphStyle(name="CellStyle", fontSize=10, leading=12, wordWrap="CJK", alignment=0)
    elements = []

    if os.path.exists(LOGO_PATH):
        try:
            with PILImage.open(LOGO_PATH) as img:
                orig_width, orig_height = img.size
                logo_width = min(orig_width * 0.5, 120)
                logo_height = min(orig_height * 0.5, 60)
                logo = Image(LOGO_PATH, width=logo_width, height=logo_height)
            logo.hAlign = 'RIGHT'
            elements.append(logo)
            elements.append(Spacer(1, 12))
        except Exception as e:
            logger.warning(f"Failed to load logo for PDF: {str(e)}")

    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 12))

    # Add test data graph if present
    if "flowrate" in data and "pressure" in data and "amperage" in data:
        test_data = {
            "flowrate": data["flowrate"],
            "pressure": data["pressure"],
            "amperage": data["amperage"]
        }
        graph_path = generate_test_graph(test_data)
        if graph_path and os.path.exists(graph_path):
            elements.append(Paragraph("Test Data Graph", heading2_style))
            elements.append(Image(graph_path, width=6*inch, height=3*inch))
            elements.append(Spacer(1, 12))

    if "bom_items" in data:
        elements.append(Paragraph("Please use this checklist to pull the required items for the pump assembly.", normal_style))
        elements.append(Spacer(1, 12))
        bom_items = data["bom_items"]
        if not isinstance(bom_items, (list, tuple)) or not bom_items:
            elements.append(Paragraph("Invalid BOM data received. Please check the pump configuration.", normal_style))
        else:
            table_data = [["Part Code", "Item", "Quantity", "Check"]]
            for item in bom_items:
                part_name = item.get("part_name", "N/A") if isinstance(item, dict) else str(item)
                part_code = item.get("part_code", "N/A") if isinstance(item, dict) else "N/A"
                quantity = str(item.get("quantity", "1")) if isinstance(item, dict) else "1"
                table_data.append([Paragraph(part_code, cell_style), Paragraph(part_name, cell_style), quantity, "[ ]"])
            table = Table(table_data, colWidths=[2.5*inch, 2*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP")
            ]))
            elements.append(table)
    else:
        table_data = [["Field", "Value"]]
        for key, value in data.items():
            # Use display versions for table if available, otherwise raw value
            if key in ["flowrate", "pressure", "amperage"] and f"{key}_display" in data:
                display_key = f"{key}_display"
                value_paragraph = Paragraph(str(data[display_key]).replace("\n", "<br/>"), cell_style)
                table_data.append([key.replace("_", " ").title(), value_paragraph])
            elif key != "bom_items" and value and not key.endswith("_display"):
                value_paragraph = Paragraph(str(value).replace("\n", "<br/>"), cell_style)
                table_data.append([key.replace("_", " ").title(), value_paragraph])
        table = Table(table_data, colWidths=[2.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        elements.append(table)

    elements.append(Spacer(1, 12))
    footer_style = ParagraphStyle(name="Footer", fontSize=10, alignment=1, textColor=colors.grey)
    generated_on = data.get("generated_on", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    elements.append(Paragraph(f"Generated on {generated_on} | Version {EXPORT_UTILS_VERSION}", footer_style))

    try:
        doc.build(elements)
        logger.info(f"Generated PDF at {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate PDF for {serial_number}: {str(e)}")
        elements.append(Paragraph(f"Error generating PDF: {str(e)}", normal_style))
        doc.build(elements)
        return output_path

def generate_pump_details_table(data):
    """Generate an HTML table for pump details."""
    try:
        rows = "".join(f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9; font-weight: bold;">{key.replace('_', ' ').title()}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{value}</td>
            </tr>
        """ for key, value in data.items() if value and not key.endswith("_display"))
        return f"""
            <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 10px 0; font-family: Arial, sans-serif;">
                <tbody>{rows}</tbody>
            </table>
        """
    except Exception as e:
        logger.error(f"Failed to generate pump details table: {str(e)}")
        return "<p>Error generating pump details table.</p>"

def generate_bom_table(bom_items):
    """Generate an HTML table for BOM items."""
    if not bom_items:
        return "<p>No BOM items available.</p>"
    try:
        rows = "".join(f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{item.get('part_name', 'N/A')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item.get('part_code', 'N/A')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item.get('quantity', 'N/A')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item.get('pulled', 'N/A')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item.get('reason', 'N/A')}</td>
            </tr>
        """ for item in bom_items)
        return f"""
            <h3 style="color: #34495e;">Bill of Materials</h3>
            <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #f4f4f4;">
                        <th style="padding: 8px; border: 1px solid #ddd;">Part Name</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Part Code</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Quantity</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Pulled</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Reason</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        """
    except Exception as e:
        logger.error(f"Failed to generate BOM table: {str(e)}")
        return "<p>Error generating BOM table.</p>"

def generate_test_data_table(test_data):
    """Generate an HTML table for test data."""
    if not test_data or not all(key in test_data for key in ["flowrate", "pressure", "amperage"]):
        return "<p>No valid test data available.</p>"
    try:
        rows = "".join(f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">Test {i+1}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{test_data['flowrate'][i] if i < len(test_data['flowrate']) else ''}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{test_data['pressure'][i] if i < len(test_data['pressure']) else ''}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{test_data['amperage'][i] if i < len(test_data['amperage']) else ''}</td>
            </tr>
        """ for i in range(5))
        return f"""
            <h3 style="color: #34495e;">Test Summary</h3>
            <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #f4f4f4;">
                        <th style="padding: 8px; border: 1px solid #ddd;">Test</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Flowrate (l/h)</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Pressure (bar)</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Amperage (A)</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        """
    except Exception as e:
        logger.error(f"Failed to generate test data table: {str(e)}")
        return "<p>Error generating test data table.</p>"