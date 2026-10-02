import enum
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    MANAGER = "Manager"
    MEMBER = "Member"


class UserStatus(str, enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)

    # Team/organization owner - the Admin who added this user. Null for the organization owner.
    added_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reports = relationship("Report", back_populates="owner", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")

    @property
    def org_id(self) -> str:
        """Team/organization id: the Admin's own id ties all members together."""
        return self.added_by_id or self.id
