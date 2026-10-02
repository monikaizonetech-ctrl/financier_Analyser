import enum
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def gen_reference_id() -> str:
    now = datetime.utcnow()
    return f"{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"


class ReportType(str, enum.Enum):
    BSA = "BSA"   # Bank Statement Analyser
    GST = "GST"   # GST Analyser
    ITR = "ITR"   # ITR Analyser


class ReportStatus(str, enum.Enum):
    NEED_TO_ANALYSE = "Need to analyse"
    PROCESSING = "Processing"
    READY_TO_USE = "Ready to use"
    FAILED = "Failed"


class Report(Base):
    """A report/workspace created by a user, e.g. 'BANKSTATEMENT (BSA Reports)'."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    reference_id: Mapped[str] = mapped_column(String(64), unique=True, default=gen_reference_id)
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


class FileStatus(str, enum.Enum):
    UPLOADED = "Uploaded"
    PROCESSING = "Processing"
    PROCESSED = "Processed"
    ERROR = "Error"


class FileAuthenticity(str, enum.Enum):
    PENDING = "Pending"
    VERIFIED = "Verified"
    SUSPICIOUS = "Suspicious"


class ReportFile(Base):
    """An uploaded source file (bank statement / GST / ITR document) attached to a report."""

    __tablename__ = "report_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), nullable=False)

    s_no: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sub_type: Mapped[str | None] = mapped_column(String(50), nullable=True)   # e.g. ITR Type / Bank name
    year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_protected: Mapped[bool] = mapped_column(default=False)

    file_status: Mapped[FileStatus] = mapped_column(Enum(FileStatus), default=FileStatus.UPLOADED)
    authenticity: Mapped[FileAuthenticity] = mapped_column(Enum(FileAuthenticity), default=FileAuthenticity.PENDING)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="files")
