from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.billing import Subscription, Transaction, PlanType, SubscriptionStatus, TransactionType
from app.models.user import User
from app.schemas.billing import BillingOut, SubscriptionOut, TransactionOut

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("", response_model=BillingOut)
def get_billing(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return BillingOut(
        subscription=SubscriptionOut.model_validate(subscription),
        transactions=[TransactionOut.model_validate(t) for t in transactions],
    )


@router.post("/avail-paid-trial", response_model=SubscriptionOut)
def avail_paid_trial(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    subscription.plan = PlanType.PAID_TRIAL
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.credits_total += 10
    subscription.expires_at = datetime.utcnow() + timedelta(days=14)
    db.add(
        Transaction(
            user_id=current_user.id,
            type=TransactionType.PLAN_UPGRADE,
            amount=0,
            description="Activated Paid Trial (14 days, +10 credits)",
        )
    )
    db.commit()
    db.refresh(subscription)
    return subscription


@router.post("/upgrade", response_model=SubscriptionOut)
def upgrade_plan(plan: PlanType, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    price_map = {
        PlanType.STANDARD: 999,
        PlanType.PRO: 2999,
        PlanType.ENTERPRISE: 9999,
    }
    credits_map = {
        PlanType.STANDARD: 25,
        PlanType.PRO: 100,
        PlanType.ENTERPRISE: 500,
    }
    if plan not in price_map:
        raise HTTPException(status_code=400, detail="Invalid plan for upgrade")

    subscription.plan = plan
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.credits_total += credits_map[plan]
    subscription.expires_at = datetime.utcnow() + timedelta(days=30)

    db.add(
        Transaction(
            user_id=current_user.id,
            type=TransactionType.PLAN_UPGRADE,
            amount=price_map[plan],
            description=f"Upgraded to {plan.value} plan",
        )
    )
    db.commit()
    db.refresh(subscription)
    return subscription
