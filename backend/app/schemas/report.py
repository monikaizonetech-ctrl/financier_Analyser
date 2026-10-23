from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.report import ReportType, ReportStatus, FileStatus, FileAuthenticity


class ReportCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    reference_id: str | None = None
    report_type: ReportType

    @field_validator('report_type', mode='before')
    @classmethod
    def map_report_type(cls, v):
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower == 'bank':
                return ReportType.BSA
            if v_lower == 'gst':
                return ReportType.GST
            if v_lower == 'itr':
                return ReportType.ITR
            # also handle uppercase aliases or original
            if v.upper() in [e.value for e in ReportType]:
                return ReportType(v.upper())
        return v


class ReportFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    s_no: int
    file_name: str
    sub_type: str | None = None
    year: str | None = None
    bank_name: str | None = None
    account_holder: str | None = None
    masked_account_no: str | None = None
    file_status: str
    authenticity: str
    password_protected: bool = False
    owner_restricted: bool = False
    authenticity_reasons: list[str] | None = None


class UnlockFileRequest(BaseModel):
    password: str


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
