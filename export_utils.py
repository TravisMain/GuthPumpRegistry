import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from datetime import datetime
import logging
import time  # Added missing import
from fpdf import FPDF
from PIL import Image
import io
from utils.config import get_logger
import tempfile

logger = get_logger("export_utils")
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
BUILD_NUMBER = "1.0.0"

# SMTP Configuration (Update with your server details for stores@guth.co.za)
SMTP_CONFIG = {
    "host": "192.168.1.5",  # Replace with your SMTP server host
    "port": 587,  # Standard STARTTLS port; adjust if different (e.g., 465 for SSL)
    "username": "guth@guth.co.za",  # Replace with your email
    "password": "Ventil@14",  # Replace with your password or app-specific password
    "use_starttls": True,
}

def generate_pump_details_table(pump_data):
    html = "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    html += "<tr><th style='padding: 8px; background-color: #34495e; color: white;'>Field</th><th style='padding: 8px; background-color: #34495e; color: white;'>Value</th></tr>"
    for key, value in pump_data.items():
        html += f"<tr><td style='padding: 8px;'>{key.replace('_', ' ').title()}</td><td style='padding: 8px;'>{value or 'N/A'}</td></tr>"
    html += "</table>"
    return html

def generate_test_data_table(test_data):
    html = "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    html += "<tr><th style='padding: 8px; background-color: #34495e; color: white;'>Test</th><th style='padding: 8px; background-color: #34495e; color: white;'>Flowrate (l/h)</th><th style='padding: 8px; background-color: #34495e; color: white;'>Pressure (bar)</th><th style='padding: 8px; background-color: #34495e; color: white;'>Amperage</th></tr>"
    for i in range(5):
        html += f"<tr><td style='padding: 8px;'>Test {i+1}</td><td style='padding: 8px;'>{test_data['flowrate'][i] or 'N/A'}</td><td style='padding: 8px;'>{test_data['pressure'][i] or 'N/A'}</td><td style='padding: 8px;'>{test_data['amperage'][i] or 'N/A'}</td></tr>"
    html += "</table>"
    return html

def generate_bom_table(bom_items):
    html = "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    html += "<tr><th style='padding: 8px; background-color: #34495e; color: white;'>Part Name</th><th style='padding: 8px; background-color: #34495e; color: white;'>Part Code</th><th style='padding: 8px; background-color: #34495e; color: white;'>Quantity</th><th style='padding: 8px; background-color: #34495e; color: white;'>Pulled</th><th style='padding: 8px; background-color: #34495e; color: white;'>Reason</th></tr>"
    for item in bom_items:
        html += f"<tr><td style='padding: 8px;'>{item['part_name'] or 'N/A'}</td><td style='padding: 8px;'>{item['part_code'] or 'N/A'}</td><td style='padding: 8px;'>{item['quantity'] or 'N/A'}</td><td style='padding: 8px;'>{item['pulled'] or 'N/A'}</td><td style='padding: 8px;'>{item['reason'] or 'N/A'}</td></tr>"
    html += "</table>"
    return html

def generate_pdf_notification(serial_number, pump_data, title="Notification"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, 0, 1, "C")
    pdf.set_font("Arial", "", 12)

    # Add logo if it exists
    if os.path.exists(LOGO_PATH):
        logger.info(f"Logo file exists at: {LOGO_PATH}")
        try:
            img = Image.open(LOGO_PATH)
            logger.info(f"Logo loaded: {img.size}")
            img_resized = img.resize((int(img.width * 1.5), int(img.height * 1.5)), Image.Resampling.LANCZOS)
            logger.info(f"Logo scaled: {img_resized.size}")
            # Save to temporary file for fpdf compatibility
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                img_resized.save(tmp_file, format="PNG")
                tmp_path = tmp_file.name
            pdf.image(tmp_path, x=10, y=10, w=img_resized.width / 10, h=img_resized.height / 10)  # Scale down by factor of 10
            # Clean up temporary file
            os.unlink(tmp_path)
        except Exception as e:
            logger.error(f"Failed to add logo to PDF: {str(e)}")

    pdf.ln(20)
    pdf.cell(0, 10, f"Serial Number: {serial_number}", 0, 1)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", 0, 1)
    pdf.ln(10)

    # Add pump details as a table
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Pump Details", 0, 1)
    pdf.set_font("Arial", "", 12)
    for key, value in pump_data.items():
        pdf.cell(0, 10, f"{key.replace('_', ' ').title()}: {value or 'N/A'}", 0, 1)

    # Save PDF
    output_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, f"notification_{serial_number}.pdf")
    pdf.output(pdf_path)
    logger.info(f"PDF notification generated: {pdf_path}")
    return pdf_path

def send_email(to_email, subject, greeting, body_content, footer, attachment_path=None):
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_CONFIG["username"]
        msg["To"] = to_email
        msg["Subject"] = subject

        # Construct the email body
        body = f"{greeting}<br><br>{body_content}<br><br>{footer}<br><br>\u00A9 Guth South Africa | Build {BUILD_NUMBER}"
        msg.attach(MIMEText(body, "html"))

        # Attach PDF if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)

        # Connect to SMTP server with explicit STARTTLS and debugging
        for attempt in range(1, 4):  # Retry up to 3 times
            try:
                with smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"], timeout=10) as server:
                    logger.debug(f"Connected to SMTP server {SMTP_CONFIG['host']}:{SMTP_CONFIG['port']}")
                    server.set_debuglevel(1)  # Enable SMTP debugging for logs
                    if SMTP_CONFIG["use_starttls"]:
                        server.starttls()
                        logger.debug("STARTTLS negotiation successful")
                    try:
                        server.login(SMTP_CONFIG["username"], SMTP_CONFIG["password"])
                        logger.debug("Login successful")
                    except smtplib.SMTPAuthenticationError as e:
                        logger.warning(f"Authentication failed: {str(e)}. Trying without AUTH if supported...")
                        # Optionally skip AUTH if server allows (uncommon)
                        pass
                    server.send_message(msg)
                    logger.info(f"Email sent successfully to {to_email}")
                    return
            except smtplib.SMTPException as e:
                logger.warning(f"Email attempt {attempt} failed: {str(e)}")
            except Exception as e:
                logger.warning(f"Email attempt {attempt} failed: {str(e)}")
            if attempt < 3:
                logger.debug(f"Retrying email in 2 seconds... (Attempt {attempt + 1}/3)")
                time.sleep(2)
        logger.error(f"Failed to send email to {to_email} after 3 attempts")
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {str(e)}")

if __name__ == "__main__":
    # Example usage for testing
    pump_data = {"serial_number": "12345", "customer": "Test Customer"}
    pdf_path = generate_pdf_notification("12345", pump_data)
    send_email("recipient@example.com", "Test Subject", "Dear User,", "<p>Test body</p>", "Regards,<br>Test Team", pdf_path)