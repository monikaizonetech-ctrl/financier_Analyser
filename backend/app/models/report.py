import enum
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum, ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ReportType(str, enum.Enum):
    BSA = "BSA"   # Bank Statement Analyser
    GST = "GST"   # GST Analyser
    ITR = "ITR"   # ITR Analyser


REPORT_TYPE_PREFIXES: dict[ReportType, str] = {
    ReportType.BSA: "BSA",
    ReportType.GST: "GST",
    ReportType.ITR: "ITR",
}


def get_report_type_prefix(report_type: ReportType | str) -> str:
    if isinstance(report_type, str):
        val = report_type.upper()
        if val in [e.value for e in ReportType]:
            report_type = ReportType(val)
        elif val == "BANK":
            report_type = ReportType.BSA
    return REPORT_TYPE_PREFIXES.get(report_type, str(report_type).upper())


def format_reference_id(report_type: ReportType | str, sequence_number: int) -> str:
    prefix = get_report_type_prefix(report_type)
    return f"{prefix}_{sequence_number:03d}"


class ReportStatus(str, enum.Enum):
    NEED_TO_ANALYSE = "Need to analyse"
    PROCESSING = "Processing"
    READY_TO_USE = "Ready to use"
    FAILED = "Failed"


class Report(Base):
    """A report/workspace created by a user, e.g. 'BANKSTATEMENT (BSA Reports)'."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    reference_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.NEED_TO_ANALYSE)

    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    analysed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    owner = relationship("User", back_populates="reports")
    files = relationship("ReportFile", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("owner_id", "report_type", "reference_id", name="uq_reports_owner_type_ref_id"),
    )


class ReportReferenceCounter(Base):
    """Tracks the latest sequential reference number per (owner_id, report_type)."""

    __tablename__ = "report_reference_counters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    last_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("owner_id", "report_type", name="uq_report_ref_counter_owner_type"),
    )



class FileStatus(str, enum.Enum):
    UPLOADED = "Uploaded"
    PASSWORD_REQUIRED = "Password required"
    UNLOCKED = "Unlocked"
    PROCESSING = "Processing"
    PROCESSED = "Processed"
    FAILED = "Failed"
    ERROR = "Failed"


class FileAuthenticity(str, enum.Enum):
    PENDING = "Pending"
    ORIGINAL = "Original"
    VERIFIED = "Original"
    SUSPICIOUS = "Suspicious"
    TAMPERED = "Tampered"
    UNVERIFIABLE = "Unverifiable"


class ReportFile(Base):
    """An uploaded source file (bank statement / GST / ITR document) attached to a report."""

    __tablename__ = "report_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), nullable=False)

    s_no: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sub_type: Mapped[str | None] = mapped_column(String(100), nullable=True)   # e.g. ITR Type / Bank name
    year: Mapped[str | None] = mapped_column(String(100), nullable=True)       # e.g. Statement period / Financial Year
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    account_holder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    masked_account_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    password_protected: Mapped[bool] = mapped_column(default=False)
    owner_restricted: Mapped[bool] = mapped_column(default=False)
    authenticity_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)

    file_status: Mapped[str] = mapped_column(String(50), default="Uploaded")
    authenticity: Mapped[str] = mapped_column(String(50), default="Pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="files")
