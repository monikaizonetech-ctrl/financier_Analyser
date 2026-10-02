import enum
import uuid
from datetime import datetime, timedelta

from sqlalchemy import String, DateTime, Enum, ForeignKey, Float, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class PlanType(str, enum.Enum):
    FREE_TRIAL = "Free Trial"
    PAID_TRIAL = "Paid Trial"
    STANDARD = "Standard"
    PRO = "Pro"
    ENTERPRISE = "Enterprise"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "Active"
    EXPIRED = "Expired"
    CANCELLED = "Cancelled"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)

    plan: Mapped[PlanType] = mapped_column(Enum(PlanType), default=PlanType.FREE_TRIAL)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)

    credits_total: Mapped[float] = mapped_column(Float, default=2.5)
    credits_used: Mapped[float] = mapped_column(Float, default=0.0)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=3))

    user = relationship("User", back_populates="subscription")

    @property
    def credits_left(self) -> float:
        return max(self.credits_total - self.credits_used, 0)


class TransactionType(str, enum.Enum):
    CREDIT_PURCHASE = "Credit Purchase"
    PLAN_UPGRADE = "Plan Upgrade"
    REFUND = "Refund"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    description: Mapped[str] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")
