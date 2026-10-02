from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.billing import Subscription
from app.models.report import Report, ReportType, ReportStatus
from app.models.user import User
from app.schemas.billing import DashboardStats, SubscriptionOut

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardStats)
def get_dashboard_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    def count_analysed(report_type: ReportType) -> int:
        return (
            db.query(func.count(Report.id))
            .filter(
                Report.owner_id == current_user.id,
                Report.report_type == report_type,
                Report.status == ReportStatus.READY_TO_USE,
            )
            .scalar()
            or 0
        )

    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    trial_days_left = 0
    if subscription and subscription.expires_at:
        delta = subscription.expires_at - datetime.utcnow()
        trial_days_left = max(delta.days, 0)

    return DashboardStats(
        bank_statements_analysed=count_analysed(ReportType.BSA),
        gst_analysed=count_analysed(ReportType.GST),
        itr_analysed=count_analysed(ReportType.ITR),
        trial_days_left=trial_days_left,
        subscription=SubscriptionOut.model_validate(subscription),
    )
