from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.billing import PlanType, SubscriptionStatus, TransactionType


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan: PlanType
    status: SubscriptionStatus
    credits_total: float
    credits_used: float
    started_at: datetime
    expires_at: datetime

    @property
    def credits_left(self) -> float:
        return max(self.credits_total - self.credits_used, 0)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: TransactionType
    amount: float
    description: str
    created_at: datetime


class BillingOut(BaseModel):
    subscription: SubscriptionOut
    transactions: list[TransactionOut]


class SupportRequestCreate(BaseModel):
    subject: str
    message: str


class DashboardStats(BaseModel):
    bank_statements_analysed: int
    gst_analysed: int
    itr_analysed: int
    trial_days_left: int
    subscription: SubscriptionOut
