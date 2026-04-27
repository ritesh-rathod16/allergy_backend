import os
import logging
from email.message import EmailMessage
import aiosmtplib
from dotenv import load_dotenv
from typing import List

load_dotenv()

BREVO_SMTP_LOGIN = os.getenv("BREVO_SMTP_LOGIN")
BREVO_SMTP_PASSWORD = os.getenv("BREVO_SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", "riteshrathod016@gmail.com")
SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587

logger = logging.getLogger(__name__)

async def send_broadcast_email(emails: List[str], subject: str, content: str, cta_text: str = None, cta_url: str = None):
    """Sends a professional HTML broadcast email to multiple users via Brevo."""
    if not BREVO_SMTP_LOGIN or not BREVO_SMTP_PASSWORD:
        return False

    message = EmailMessage()
    message["From"] = f"Allergy Detector Admin <{EMAIL_FROM}>"
    message["Subject"] = subject
    
    # CTA HTML Part
    cta_html = f'<br/><a href="{cta_url}" style="background:#2E7D32;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;">{cta_text}</a>' if cta_text and cta_url else ''

    html_content = f"""
    <html>
        <body style="font-family: sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 12px;">
                <h2 style="color: #2E7D32;">{subject}</h2>
                <p>{content}</p>
                {cta_html}
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;"/>
                <p style="font-size: 12px; color: #888;">You are receiving this because you are a registered user of Allergy Detector.</p>
            </div>
        </body>
    </html>
    """
    message.add_alternative(html_content, subtype="html")

    try:
        # For large lists, typically you would use a BCC or an email provider's batch API
        # but for this SaaS platform we loop or send as bulk.
        message["To"] = ", ".join(emails) 
        await aiosmtplib.send(
            message,
            hostname=SMTP_SERVER, port=SMTP_PORT,
            username=BREVO_SMTP_LOGIN, password=BREVO_SMTP_PASSWORD,
            start_tls=True
        )
        return True
    except Exception as e:
        logger.error(f"Broadcast Email Failed: {e}")
        return False

async def send_otp_email(email: str, otp: str) -> bool:
    # Existing OTP logic remains...
    pass
