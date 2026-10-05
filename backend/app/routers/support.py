from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.billing import SupportRequestCreate, ContactUsCreate
from app.core.config import Settings
import smtplib
from email.message import EmailMessage

router = APIRouter(prefix="/support", tags=["Support"])

CONTACT_INFO = {
    "phone": "+91 63743 45280",
    "email": "contact@proanalyser.in",
}


@router.get("/contact")
def get_contact_info():
    return CONTACT_INFO


@router.post("/requests", status_code=201)
def raise_support_request(payload: SupportRequestCreate, current_user: User = Depends(get_current_user)):
    try:
        current_settings = Settings()
        
        msg = EmailMessage()
        msg.set_content(f"Support Request from: {current_user.email}\nName: {current_user.full_name}\n\nSubject: {payload.subject}\n\nMessage:\n{payload.message}")
        msg["Subject"] = f"Support Request: {payload.subject}"
        msg["From"] = current_settings.SMTP_USER or "no-reply@proanalyser.in" 
        msg["To"] = "zara1031998@gmail.com"

        if current_settings.SMTP_SERVER and current_settings.SMTP_USER and current_settings.SMTP_PASSWORD:
            server = smtplib.SMTP(current_settings.SMTP_SERVER, current_settings.SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.login(current_settings.SMTP_USER, current_settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"Successfully sent support request email to zara1031998@gmail.com")
        else:
            return {"error": True, "message": "SMTP credentials missing in backend."}

    except Exception as e:
        print(f"Failed to send support request email: {e}")
        return {"error": True, "message": f"SMTP Error: {str(e)}"}

    return {
        "error": False,
        "message": "Your request has been raised. Our support team will reach out shortly.",
        "subject": payload.subject,
        "raised_by": current_user.email,
    }


@router.post("/contact-us")
def contact_us(payload: ContactUsCreate):
    try:
        # Re-instantiate settings to guarantee we catch any recent .env changes
        # without requiring a full server restart
        current_settings = Settings()
        
        msg = EmailMessage()
        msg.set_content(f"Name: {payload.fullName}\nEmail: {payload.email}\nPhone: {payload.phone}\n\nMessage:\n{payload.message}")
        msg["Subject"] = payload.subject or "Project Inquiry"
        msg["From"] = current_settings.SMTP_USER or "no-reply@proanalyser.in" 
        msg["To"] = "zara1031998@gmail.com"

        # Check if SMTP is configured
        if current_settings.SMTP_SERVER and current_settings.SMTP_USER and current_settings.SMTP_PASSWORD:
            server = smtplib.SMTP(current_settings.SMTP_SERVER, current_settings.SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.login(current_settings.SMTP_USER, current_settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"Successfully sent email to zara1031998@gmail.com via {current_settings.SMTP_SERVER}")
        else:
            return {"error": True, "message": "SMTP credentials are missing in the .env file. Please check your .env configuration."}

    except Exception as e:
        print(f"Failed to send email: {e}")
        return {"error": True, "message": f"SMTP Error: {str(e)}"}

    return {
        "error": False,
        "message": "Your message has been processed successfully.",
        "sent_to": "zara1031998@gmail.com",
    }
