import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from utils.config import get_logger
import time
from datetime import datetime
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
BUILD_NUMBER = "1.0.0"
logger = get_logger("export_utils")

def load_config():
    """Load configuration from config.json."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {CONFIG_PATH}: {str(e)}")
        raise

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
    rows = "".join(f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{key.replace('_', ' ').title()}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{value}</td>
        </tr>
    """ for key, value in pump_data.items() if value)
    return f"""
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tbody>
                {rows}
            </tbody>
        </table>
    """

def generate_bom_table(bom_items):
    """Generate an HTML table for BOM items."""
    if not bom_items:
        return "<p>No BOM items available.</p>"
    rows = "".join(f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;">{item['part_name']}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{item['part_code']}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{item['quantity']}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{item.get('pulled', 'N/A')}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{item.get('reason', 'N/A')}</td>
        </tr>
    """ for item in bom_items)
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
    rows = "".join(f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;">Test {i+1}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{test_data['flowrate'][i] if i < len(test_data['flowrate']) else ''}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{test_data['pressure'][i] if i < len(test_data['pressure']) else ''}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{test_data['amperage'][i] if i < len(test_data['amperage']) else ''}</td>
        </tr>
    """ for i in range(5))
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

def generate_pdf_notification(serial_number, data, title="Pump Assembly Notification", output_path=None):
    """Generate a PDF notification document."""
    if output_path is None:
        output_path = os.path.join(BASE_DIR, "data", f"notification_{serial_number}.pdf")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    if os.path.exists(LOGO_PATH):
        try:
            logo = Image(LOGO_PATH, width=120, height=60)
            logo.hAlign = 'RIGHT'
            story.append(logo)
            story.append(Spacer(1, 12))
        except Exception as e:
            logger.error(f"Failed to add logo to PDF: {str(e)}")

    story.append(Paragraph(title, styles['Heading1']))
    story.append(Spacer(1, 12))

    table_data = [[key.replace('_', ' ').title(), str(value)] for key, value in data.items() if value and key != "bom_items"]
    if "bom_items" in data and data["bom_items"]:
        story.append(Paragraph("Bill of Materials", styles['Heading2']))
        story.append(Spacer(1, 6))
        bom_data = [["Part Name", "Part Code", "Quantity"]] + [[item["part_name"], item["part_code"], item["quantity"]] for item in data["bom_items"]]
        bom_table = Table(bom_data, colWidths=[150, 150, 50], style=[
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ])
        story.append(bom_table)
        story.append(Spacer(1, 12))
    else:
        table_data.append(["Bill of Materials", "Not included"])

    table = Table(table_data, colWidths=[150, 350], style=[
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
    ])
    story.append(table)
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"© Guth South Africa | Build {BUILD_NUMBER}", styles['Normal']))
    try:
        doc.build(story)
        logger.info(f"PDF notification generated: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate PDF: {str(e)}")
        raise

def send_email(to_email, subject, greeting, body_content, footer="", *attachment_paths, smtp_retries=3):
    """Send an email with multiple optional attachments."""
    config = load_config()
    email_settings = config.get("email_settings", {})
    smtp_server = email_settings.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(email_settings.get("smtp_port", 587))
    smtp_user = email_settings.get("smtp_username", "")
    smtp_password = email_settings.get("smtp_password", "")
    sender_email = email_settings.get("sender_email", smtp_user)
    use_tls = email_settings.get("use_tls", True)

    if not smtp_user or not smtp_password:
        logger.error("SMTP credentials not configured in config.json")
        raise ValueError("SMTP credentials not configured")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    html_body = generate_html_email(subject, greeting, body_content, footer)
    msg.attach(MIMEText(html_body, 'html'))

    for attachment_path in attachment_paths:
        if os.path.exists(attachment_path):
            try:
                with open(attachment_path, 'rb') as f:
                    attachment = MIMEApplication(f.read(), _subtype="pdf")
                    attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                    msg.attach(attachment)
            except Exception as e:
                logger.error(f"Failed to attach {attachment_path}: {str(e)}")

    for attempt in range(smtp_retries):
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            logger.info(f"Email sent to {to_email} with subject '{subject}'")
            return True
        except Exception as e:
            logger.warning(f"Email attempt {attempt + 1} failed: {str(e)}")
            time.sleep(2)
    logger.error(f"Failed to send email to {to_email} after {smtp_retries} attempts")
    return False