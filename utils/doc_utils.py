import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from utils.config import get_logger
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERT_DIR = os.path.join(BASE_DIR, "data", "certificates")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
logger = get_logger("doc_utils")

def generate_certificate(serial_number, pump_model, customer, test_result, test_date, username):
    os.makedirs(CERT_DIR, exist_ok=True)
    pdf_path = os.path.join(CERT_DIR, f"certificate_{serial_number}.pdf")
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    if os.path.exists(LOGO_PATH):
        logo = Image(LOGO_PATH, width=100, height=100)
        story.append(logo)
    else:
        story.append(Paragraph("Guth Pump Registry", styles['Title']))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Certificate of Completion", styles['Heading1']))
    story.append(Spacer(1, 12))
    
    content = f"""
    Serial Number: {serial_number}<br/>
    Pump Model: {pump_model}<br/>
    Customer: {customer}<br/>
    Test Result: {test_result}<br/>
    Test Date: {test_date}<br/>
    Certified By: {username}
    """
    story.append(Paragraph(content, styles['BodyText']))
    
    doc.build(story)
    logger.info(f"Certificate generated: {pdf_path}")
    return pdf_path

def send_email(to_email, serial_number, pdf_path, smtp_retries=3):
    sender = "noreply@guthpumpregistry.com"
    subject = f"Certificate for Pump {serial_number}"
    body = f"Attached is the certificate for pump {serial_number}."

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with open(pdf_path, 'rb') as f:
        pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
        msg.attach(pdf_attachment)

    for attempt in range(smtp_retries):
        try:
            # Use localhost:1025 with debug mode (no real server needed)
            smtp = smtplib.SMTP('localhost', 1025)
            smtp.set_debuglevel(1)  # Log SMTP interactions to console
            smtp.send_message(msg)
            smtp.quit()
            logger.info(f"Email sent to {to_email} for {serial_number}")
            return True
        except Exception as e:
            logger.warning(f"Email attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    logger.error(f"Failed to send email to {to_email} after {smtp_retries} attempts")
    return False

if __name__ == "__main__":
    pdf_path = generate_certificate("TEST-001", "P1 3.0kW", "Test Customer", "Pass", "2025-03-16", "tester1")
    send_email("test@example.com", "TEST-001", pdf_path)