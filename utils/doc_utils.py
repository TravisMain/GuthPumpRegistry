import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from utils.config import get_logger
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERT_DIR = os.path.join(BASE_DIR, "data", "certificates")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
BUILD_NUMBER = "1.0.0"
logger = get_logger("doc_utils")

# SMTP Configuration (to be updated with real credentials)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "guthsouthafrica@gmail.com"  # Replace with your Gmail address
SMTP_PASSWORD = "Ventil@14"  # Replace with your App Password

def generate_html_email(subject, greeting, body_content, footer=""):
    """Generate a styled HTML email template."""
    return f"""
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
            <p style="font-size: 12px; color: #777; text-align: center;">© Guth South Africa | Build {BUILD_NUMBER}</p>
        </div>
    </body>
    </html>
    """

def generate_pump_details_table(pump_data):
    """Generate an HTML table for pump details."""
    rows = ""
    for key, value in pump_data.items():
        if value:  # Only include non-empty values
            rows += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{key.replace('_', ' ').title()}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{value}</td>
                </tr>
            """
    return f"""
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tbody>
                {rows}
            </tbody>
        </table>
    """

def generate_bom_table(bom_items):
    """Generate an HTML table for BOM items."""
    rows = ""
    for item in bom_items:
        rows += f"""
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">{item['part_name']}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{item['part_code']}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{item['quantity']}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{item['pulled']}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{item['reason'] or 'N/A'}</td>
            </tr>
        """
    return f"""
        <h3 style="color: #34495e;">Bill of Materials</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <thead>
                <tr style="background-color: #f4f4f4;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Part Name</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Part Code</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Quantity</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Pulled</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Reason</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    """

def generate_test_data_table(test_data):
    """Generate an HTML table for test data."""
    rows = ""
    for i in range(5):
        flow = test_data["flowrate"][i] if i < len(test_data["flowrate"]) else ""
        pressure = test_data["pressure"][i] if i < len(test_data["pressure"]) else ""
        amperage = test_data["amperage"][i] if i < len(test_data["amperage"]) else ""
        rows += f"""
            <tr>
                <td style="border: 1px solid #ddd; padding: 8px;">Test {i+1}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{flow}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{pressure}</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{amperage}</td>
            </tr>
        """
    return f"""
        <h3 style="color: #34495e;">Test Summary</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <thead>
                <tr style="background-color: #f4f4f4;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Test</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Flowrate (l/h)</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Pressure (bar)</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Amperage (A)</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    """

def generate_pdf_notification(serial_number, pump_data, title="Pump Assembly Notification"):
    """Generate a PDF notification document."""
    pdf_path = os.path.join(BASE_DIR, "data", f"notification_{serial_number}.pdf")
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    if os.path.exists(LOGO_PATH):
        logo = Image(LOGO_PATH, width=120, height=60)
        logo.hAlign = 'RIGHT'
        story.append(logo)
        story.append(Spacer(1, 12))

    story.append(Paragraph(title, styles['Heading1']))
    story.append(Spacer(1, 12))

    data = [[key.replace('_', ' ').title(), value] for key, value in pump_data.items() if value]
    table = Table(data, colWidths=[150, 350], style=[
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
    ])
    story.append(table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("© Guth South Africa | Build " + BUILD_NUMBER, styles['Normal']))
    doc.build(story)
    logger.info(f"PDF notification generated: {pdf_path}")
    return pdf_path

def send_email(to_email, subject, greeting, body_content, footer="", attachment_path=None, smtp_retries=3):
    """Send an email with optional attachment."""
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject

    html_body = generate_html_email(subject, greeting, body_content, footer)
    msg.attach(MIMEText(html_body, 'html'))

    if attachment_path:
        with open(attachment_path, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype="pdf")
            attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
            msg.attach(attachment)

    for attempt in range(smtp_retries):
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            logger.info(f"Email sent to {to_email} with subject '{subject}'")
            return True
        except Exception as e:
            logger.warning(f"Email attempt {attempt + 1} failed: {str(e)}")
            time.sleep(2)
    logger.error(f"Failed to send email to {to_email} after {smtp_retries} attempts")
    return False