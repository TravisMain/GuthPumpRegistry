import csv
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from database import connect_db, get_all_pumps, get_audit_log
from utils.config import get_logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(BASE_DIR, "data", "exports")
DOCS_DIR = os.path.join(BASE_DIR, "data", "docs")
logger = get_logger("export_utils")

def export_pumps():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(EXPORT_DIR, f"pumps_export_{timestamp}.csv")
    
    with connect_db() as conn:
        cursor = conn.cursor()
        pumps = get_all_pumps(cursor)
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Serial Number", "Pump Model", "Customer", "Status", "Test Result", "Test Date"])
        for pump in pumps:
            writer.writerow([pump["serial_number"], pump["pump_model"], pump["customer"],
                            pump["status"], pump["test_result"], pump["test_date"]])
    
    logger.info(f"Pump data exported to {csv_path}")
    return csv_path

def export_audit_log():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(EXPORT_DIR, f"audit_log_export_{timestamp}.csv")
    
    with connect_db() as conn:
        cursor = conn.cursor()
        logs = get_audit_log(cursor)
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Username", "Action"])
        for log in logs:
            writer.writerow([log["timestamp"], log["username"], log["action"]])
    
    logger.info(f"Audit log exported to {csv_path}")
    return csv_path

def generate_user_guide():
    os.makedirs(DOCS_DIR, exist_ok=True)
    pdf_path = os.path.join(DOCS_DIR, "user_guide.pdf")
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Guth Pump Registry User Guide", styles['Title']))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Roles and Responsibilities", styles['Heading1']))
    story.append(Spacer(1, 12))
    
    roles = {
        "Pump Originator": "Create new pump records with model, configuration, and customer details.",
        "Stores": "Pull parts from the BOM for assembly.",
        "Assembler": "Verify BOM items as assembled.",
        "Testing": "Test pumps, record results, and generate certificates.",
        "Admin": "Manage users, view pump status, and export data."
    }
    for role, desc in roles.items():
        story.append(Paragraph(f"{role}: {desc}", styles['BodyText']))
        story.append(Spacer(1, 6))
    
    story.append(Paragraph("Usage", styles['Heading1']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("1. Login with your credentials.", styles['BodyText']))
    story.append(Paragraph("2. Use the sidebar buttons based on your role.", styles['BodyText']))
    story.append(Paragraph("3. Admins can export data and manage users from the Admin Panel.", styles['BodyText']))
    
    doc.build(story)
    logger.info(f"User guide generated at {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    export_pumps()
    export_audit_log()
    generate_user_guide()