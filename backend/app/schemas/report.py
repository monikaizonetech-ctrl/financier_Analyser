from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from app.models.report import ReportType, ReportStatus, FileStatus, FileAuthenticity


class ReportCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    reference_id: str | None = None
    report_type: ReportType


class ReportFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    s_no: int
    file_name: str
    sub_type: str | None = None
    year: str | None = None
    file_status: FileStatus
    authenticity: FileAuthenticity


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference_id: str
    name: str
    report_type: ReportType
    status: ReportStatus
    created_at: datetime
    analysed_at: datetime | None = None
    result_summary: dict | None = None


class ReportDetailOut(ReportOut):
    files: list[ReportFileOut] = []


class TeamReportOut(ReportOut):
    owner_email: str
    owner_name: str


class PaginatedReports(BaseModel):
    items: list[ReportOut]
    total: int
    page: int
    page_size: int


class PaginatedTeamReports(BaseModel):
    items: list[TeamReportOut]
    total: int
    page: int
    page_size: int
