import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
import sqlalchemy.exc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.billing import Subscription
from app.models.report import Report, ReportFile, ReportType, ReportStatus, FileStatus, FileAuthenticity
from app.models.user import User
from app.schemas.report import (
    ReportCreate,
    ReportOut,
    ReportDetailOut,
    ReportFileOut,
    PaginatedReports,
    PaginatedTeamReports,
    TeamReportOut,
)
from app.services.file_analysis_service import run_analysis, build_excel_report, build_pdf_report
from app.utils.pagination import paginate
from io import BytesIO

router = APIRouter(prefix="/reports", tags=["Reports"])


def _org_user_ids(db: Session, current_user: User) -> list[str]:
    """All user ids belonging to the same team/org as current_user."""
    org_owner_id = current_user.org_id
    rows = db.query(User.id).filter(
        or_(User.id == org_owner_id, User.added_by_id == org_owner_id)
    ).all()
    return [r[0] for r in rows]


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = Report(
        name=payload.name,
        report_type=payload.report_type,
        owner_id=current_user.id,
    )
    if payload.reference_id:
        report.reference_id = payload.reference_id
    db.add(report)
    try:
        db.commit()
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="A report with this Reference ID already exists."
        )
    db.refresh(report)
    return report


@router.get("", response_model=PaginatedReports)
def list_my_reports(
    search: str | None = Query(default=None, description="Search by report name"),
    sort_by: str = Query(default="created_at"),
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Report).filter(Report.owner_id == current_user.id)
    if search:
        query = query.filter(Report.name.ilike(f"%{search}%"))

    sort_col = getattr(Report, sort_by, Report.created_at)
    query = query.order_by(sort_col.desc())

    items, total, page, page_size = paginate(query, page, page_size)
    return PaginatedReports(items=items, total=total, page=page, page_size=page_size)


@router.get("/team", response_model=PaginatedTeamReports)
def list_team_reports(
    search_email: str | None = None,
    search_name: str | None = None,
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_ids = _org_user_ids(db, current_user)
    query = db.query(Report, User).join(User, Report.owner_id == User.id).filter(Report.owner_id.in_(org_ids))

    if search_email:
        query = query.filter(User.email.ilike(f"%{search_email}%"))
    if search_name:
        query = query.filter(Report.name.ilike(f"%{search_name}%"))

    query = query.order_by(Report.created_at.desc())

    total = query.count()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    items = [
        TeamReportOut(
            **ReportOut.model_validate(report).model_dump(),
            owner_email=owner.email,
            owner_name=owner.name,
        )
        for report, owner in rows
    ]
    return PaginatedTeamReports(items=items, total=total, page=page, page_size=page_size)


def _get_owned_report(report_id: str, current_user: User, db: Session) -> Report:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    org_ids = set(_org_user_ids(db, current_user))
    if report.owner_id not in org_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this report")
    return report


@router.get("/{report_id}", response_model=ReportDetailOut)
def get_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_owned_report(report_id, current_user, db)


@router.post("/{report_id}/files", response_model=ReportFileOut, status_code=status.HTTP_201_CREATED)
def upload_report_file(
    report_id: str,
    sub_type: str | None = None,
    year: str | None = None,
    password_protected: bool = False,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = _get_owned_report(report_id, current_user, db)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    contents = file.file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    report_dir = os.path.join(settings.UPLOAD_DIR, report.id)
    os.makedirs(report_dir, exist_ok=True)
    stored_path = os.path.join(report_dir, file.filename)
    with open(stored_path, "wb") as f:
        f.write(contents)

    next_s_no = (db.query(ReportFile).filter(ReportFile.report_id == report.id).count()) + 1
    report_file = ReportFile(
        report_id=report.id,
        s_no=next_s_no,
        file_name=file.filename,
        stored_path=stored_path,
        sub_type=sub_type,
        year=year,
        password_protected=password_protected,
        file_status=FileStatus.UPLOADED,
        authenticity=FileAuthenticity.PENDING,
    )
    db.add(report_file)

    if report.status == ReportStatus.NEED_TO_ANALYSE:
        pass  # stays "Need to analyse" until Analyse is triggered
    db.commit()
    db.refresh(report_file)
    return report_file


@router.delete("/{report_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report_file(
    report_id: str, file_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    report = _get_owned_report(report_id, current_user, db)
    report_file = db.query(ReportFile).filter(ReportFile.id == file_id, ReportFile.report_id == report.id).first()
    if not report_file:
        raise HTTPException(status_code=404, detail="File not found")
    if os.path.exists(report_file.stored_path):
        os.remove(report_file.stored_path)
    db.delete(report_file)
    db.commit()
    return None


@router.post("/{report_id}/analyse", response_model=ReportDetailOut)
def analyse_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = _get_owned_report(report_id, current_user, db)
    if not report.files:
        raise HTTPException(status_code=400, detail="Upload at least one file before analysing")

    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.org_id).first()
    if subscription and subscription.credits_left <= 0:
        raise HTTPException(status_code=402, detail="No credits left. Please upgrade your plan.")

    report.status = ReportStatus.PROCESSING
    db.commit()

    file_paths = [f.stored_path for f in report.files]
    summary = run_analysis(report.report_type, file_paths, account_holder=current_user.name)

    for f in report.files:
        f.file_status = FileStatus.PROCESSED
        f.authenticity = FileAuthenticity.VERIFIED

    report.result_summary = summary
    report.status = ReportStatus.READY_TO_USE
    report.analysed_at = datetime.utcnow()

    if subscription:
        subscription.credits_used = min(subscription.credits_used + 0.5, subscription.credits_total)

    db.commit()
    db.refresh(report)
    return report


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    file_format: str = Query(default="xlsx", pattern="^(xlsx|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = _get_owned_report(report_id, current_user, db)
    if report.status != ReportStatus.READY_TO_USE or not report.result_summary:
        raise HTTPException(status_code=400, detail="Report has not been analysed yet")

    if file_format == "xlsx":
        content = build_excel_report(report.name, report.report_type.value, report.result_summary)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{report.name}_{datetime.utcnow().strftime('%d_%b_%Y')}.xlsx"
    else:
        content = build_pdf_report(report.name, report.report_type.value, report.result_summary)
        media_type = "application/pdf"
        filename = f"{report.name}_{datetime.utcnow().strftime('%d_%b_%Y')}.pdf"

    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = _get_owned_report(report_id, current_user, db)
    report_dir = os.path.join(settings.UPLOAD_DIR, report.id)
    if os.path.isdir(report_dir):
        shutil.rmtree(report_dir, ignore_errors=True)
    db.delete(report)
    db.commit()
    return None
