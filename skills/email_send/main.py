import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def execute(to, subject, body, html=False, reply_to=None):
    """Send email via SMTP. Requires SMTP env vars or system settings."""
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    if not smtp_user or not smtp_pass:
        return {"error": "SMTP credentials not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD."}
    msg = MIMEMultipart("alternative")
    msg["From"] = smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    content_type = "html" if html else "plain"
    msg.attach(MIMEText(body, content_type, "utf-8"))
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return {"sent": True, "to": to, "subject": subject}
    except Exception as e:
        return {"error": f"Failed to send email: {e}"}
