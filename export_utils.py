import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from utils.config import get_logger
import tempfile
from datetime import datetime

logger = get_logger("export_utils")

# Email configuration (update with your actual SMTP settings)
SMTP_SERVER = "smtp.gmail.com"  # Example: Gmail SMTP server
SMTP_PORT = 587  # Port for TLS
SMTP_USER = "your-email@gmail.com"  # Update with your email
SMTP_PASSWORD = "your-app-password"  # Update with your app-specific password

# Paths
BASE_DIR = r"C:\Users\travism\source\repos\GuthPumpRegistry"
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")

def send_email(to_email, subject, greeting, body_content, footer, *attachments):
    """
    Send an email with the specified subject, body, and attachments.
    
    Args:
        to_email (str): Recipient's email address.
        subject (str): Email subject.
        greeting (str): Greeting line (e.g., "Dear Stores Team,").
        body_content (str): Main body content (HTML supported).
        footer (str): Footer text (e.g., "Regards,<br>Guth Pump Registry").
        *attachments (str): Paths to files to attach.
    """
    try:
        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject

        # Construct the email body
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <p>{greeting}</p>
                {body_content}
                <br>
                {footer}
            </body>
        </html>
        """
        msg.attach(MIMEText(body, "html"))

        # Attach files
        for attachment_path in attachments:
            if not os.path.exists(attachment_path):
                logger.warning(f"Attachment not found: {attachment_path}")
                continue
            with open(attachment_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)
            logger.info(f"Attached file to email: {attachment_path}")

        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Enable TLS
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
            logger.info(f"Email sent to {to_email} with subject '{subject}' and {len(attachments)} attachments")

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise

def generate_pdf_notification(serial_number, data, title, output_path=None):
    """
    Generate a PDF document with a header, title, and data table.
    
    Args:
        serial_number (str): Serial number or identifier for the document.
        data (dict): Dictionary of data to display in the table (key-value pairs).
        title (str): Title of the document.
        output_path (str, optional): Path to save the PDF. If None, saves to a temp file.
    
    Returns:
        str: Path to the generated PDF file.
    """
    try:
        # Determine the output path
        if output_path is None:
            output_path = os.path.join(tempfile.gettempdir(), f"{serial_number}_{title.replace(' ', '_')}.pdf")

        # Create the PDF document
        doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = styles["Heading1"]
        title_style.alignment = 1  # Center
        title_style.fontSize = 16
        normal_style = styles["Normal"]
        normal_style.fontSize = 12

        # Header with logo (if available)
        header_table_data = []
        if os.path.exists(LOGO_PATH):
            try:
                logo = Image(LOGO_PATH, width=1.5*inch, height=1.5*inch)
                header_table_data.append([logo, Paragraph("Guth Pump Registry", styles["Heading2"])])
            except Exception as e:
                logger.warning(f"Failed to load logo for PDF: {str(e)}")
                header_table_data.append(["", Paragraph("Guth Pump Registry", styles["Heading2"])])
        else:
            header_table_data.append(["", Paragraph("Guth Pump Registry", styles["Heading2"])])
        header_table = Table(header_table_data, colWidths=[2*inch, 5*inch])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER")
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.25*inch))

        # Title
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 0.25*inch))

        # Data table
        table_data = [["Field", "Value"]]
        for key, value in data.items():
            table_data.append([key, str(value).replace("\n", "<br/>")])
        table = Table(table_data, colWidths=[2.5*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.25*inch))

        # Footer
        footer_style = ParagraphStyle(name="Footer", fontSize=10, alignment=1, textColor=colors.grey)
        elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style))

        # Build the PDF
        doc.build(elements)
        logger.info(f"Generated PDF at {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to generate PDF for {serial_number}: {str(e)}")
        raise

def generate_pump_details_table(data):
    """
    Generate an HTML table string for pump details to be used in email bodies.
    
    Args:
        data (dict): Dictionary containing pump details.
    
    Returns:
        str: HTML string of the table.
    """
    try:
        table_rows = ""
        for key, value in data.items():
            if value:  # Only include non-empty values
                table_rows += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9; font-weight: bold;">{key.replace('_', ' ').title()}</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">{value}</td>
                    </tr>
                """
        table_html = f"""
        <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 10px 0; font-family: Arial, sans-serif;">
            {table_rows}
        </table>
        """
        logger.debug("Generated pump details table for email")
        return table_html

    except Exception as e:
        logger.error(f"Failed to generate pump details table: {str(e)}")
        return "<p>Error generating pump details table.</p>"

def generate_bom_table(bom_data):
    """
    Generate an HTML table string for BOM (Bill of Materials) data to be used in email bodies or documents.
    
    Args:
        bom_data (list of dict): List of dictionaries containing BOM items.
            Each dict should have keys like 'part_number', 'description', 'quantity', etc.
    
    Returns:
        str: HTML string of the table.
    """
    try:
        if not bom_data:
            return "<p>No BOM data available.</p>"

        # Define the columns to display
        headers = ["Part Number", "Description", "Quantity"]
        table_rows = ""
        
        # Generate header row
        header_row = "".join(
            f'<th style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9; font-weight: bold;">{header}</th>'
            for header in headers
        )
        table_rows += f"<tr>{header_row}</tr>"

        # Generate data rows
        for item in bom_data:
            part_number = item.get("part_number", "N/A")
            description = item.get("description", "N/A")
            quantity = item.get("quantity", "N/A")
            table_rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{part_number}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{description}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{quantity}</td>
                </tr>
            """

        table_html = f"""
        <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 10px 0; font-family: Arial, sans-serif;">
            {table_rows}
        </table>
        """
        logger.debug("Generated BOM table for email/document")
        return table_html

    except Exception as e:
        logger.error(f"Failed to generate BOM table: {str(e)}")
        return "<p>Error generating BOM table.</p>"

def generate_test_data_table(test_data):
    """
    Generate an HTML table string for test data to be used in email bodies or documents.
    
    Args:
        test_data (dict): Dictionary containing test data.
            Expected keys might include 'test_name', 'value', 'status', etc.
    
    Returns:
        str: HTML string of the table.
    """
    try:
        if not test_data:
            return "<p>No test data available.</p>"

        # Define the columns to display
        headers = ["Test Parameter", "Value", "Status"]
        table_rows = ""
        
        # Generate header row
        header_row = "".join(
            f'<th style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9; font-weight: bold;">{header}</th>'
            for header in headers
        )
        table_rows += f"<tr>{header_row}</tr>"

        # Generate data rows
        # Assuming test_data is a dictionary where keys are test parameters and values are dicts with 'value' and 'status'
        for test_name, details in test_data.items():
            value = details.get("value", "N/A")
            status = details.get("status", "N/A")
            table_rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{test_name.replace('_', ' ').title()}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{value}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{status}</td>
                </tr>
            """

        table_html = f"""
        <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 10px 0; font-family: Arial, sans-serif;">
            {table_rows}
        </table>
        """
        logger.debug("Generated test data table for email/document")
        return table_html

    except Exception as e:
        logger.error(f"Failed to generate test data table: {str(e)}")
        return "<p>Error generating test data table.</p>"