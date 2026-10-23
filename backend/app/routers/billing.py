from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
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
def upgrade_plan(plan: str = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    plan_normalized = plan.strip().upper()
    plan_map = {
        "BASIC": PlanType.BASIC,
        "STANDARD": PlanType.STANDARD,
        "PREMIUM": PlanType.PREMIUM,
        "PRO": PlanType.PRO,
        "ENTERPRISE": PlanType.ENTERPRISE,
    }
    target_plan = plan_map.get(plan_normalized)
    if not target_plan:
        for p in PlanType:
            if p.value.upper() == plan_normalized:
                target_plan = p
                break
    if not target_plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan '{plan}' for upgrade")

    price_map = {
        PlanType.BASIC: 6999,
        PlanType.STANDARD: 13999,
        PlanType.PREMIUM: 27999,
        PlanType.PRO: 2999,
        PlanType.ENTERPRISE: 9999,
    }
    credits_map = {
        PlanType.BASIC: 69.99,
        PlanType.STANDARD: 139.99,
        PlanType.PREMIUM: 279.99,
        PlanType.PRO: 100,
        PlanType.ENTERPRISE: 500,
    }

    subscription.plan = target_plan
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.credits_total += credits_map[target_plan]
    subscription.expires_at = datetime.utcnow() + timedelta(days=365)

    db.add(
        Transaction(
            user_id=current_user.id,
            type=TransactionType.PLAN_UPGRADE,
            amount=price_map[target_plan],
            description=f"Upgraded to {target_plan.value} plan ({credits_map[target_plan]} Pro-Credits, Yearly)",
        )
    )
    db.commit()
    db.refresh(subscription)
    return subscription


