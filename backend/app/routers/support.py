from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.billing import SupportRequestCreate

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
    # In production this would create a ticket record / notify the support team via email.
    return {
        "message": "Your request has been raised. Our support team will reach out shortly.",
        "subject": payload.subject,
        "raised_by": current_user.email,
    }
