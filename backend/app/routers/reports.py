import os
import shutil
import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status, Body
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
    UnlockFileRequest,
    PaginatedReports,
    PaginatedTeamReports,
    TeamReportOut,
)
from app.services.file_analysis_service import run_analysis, build_excel_report, build_pdf_report
from app.services.pdf_security_service import detect_pdf_encryption, unlock_pdf_file
from app.services.authenticity_service import check_document_authenticity
from app.services.pdf_extractor import extract_pdf_document, extract_document_metadata
from app.services.progress_service import set_report_progress, get_report_progress, clear_report_progress
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
    else:
        reports = db.query(Report.reference_id).all()
        max_id = 0
        for r in reports:
            if r[0] and r[0].isdigit():
                max_id = max(max_id, int(r[0]))
        report.reference_id = str(max_id + 1)

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


@router.get("/next-id")
def get_next_report_id(db: Session = Depends(get_db)):
    reports = db.query(Report.reference_id).all()
    max_id = 0
    for r in reports:
        if r[0] and r[0].isdigit():
            max_id = max(max_id, int(r[0]))
    return {"next_id": str(max_id + 1)}


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

    changed = False
    for f in report.files:
        if f.stored_path and os.path.exists(f.stored_path) and f.file_name.lower().endswith(".pdf"):
            try:
                enc = detect_pdf_encryption(f.stored_path)
                if enc["password_required"]:
                    if f.file_status != FileStatus.PASSWORD_REQUIRED or f.authenticity != FileAuthenticity.PENDING:
                        f.file_status = FileStatus.PASSWORD_REQUIRED
                        f.authenticity = FileAuthenticity.PENDING
                        f.password_protected = True
                        f.authenticity_reasons = ["Password required before authenticity check and text extraction"]
                        changed = True
                    if report.status == ReportStatus.READY_TO_USE:
                        report.status = ReportStatus.NEED_TO_ANALYSE
                        report.result_summary = None
                        changed = True
            except Exception:
                pass
    if changed:
        db.commit()
        db.refresh(report)

    return report


@router.get("/{report_id}", response_model=ReportDetailOut)
def get_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_owned_report(report_id, current_user, db)


def _mask_acc_no(acc_no: str | None) -> str:
    if not acc_no:
        return "-"
    clean = str(acc_no).strip()
    digits = "".join(ch for ch in clean if ch.isdigit())
    if not digits:
        return clean
    if len(digits) <= 4:
        return f"XXXX {digits}"
    masked_raw = ("X" * (len(digits) - 4)) + digits[-4:]
    pad = (4 - len(masked_raw) % 4) % 4
    masked_raw = "X" * pad + masked_raw
    chunks = [masked_raw[i:i + 4] for i in range(0, len(masked_raw), 4)]
    return " ".join(chunks)


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

    is_pdf = file.filename.lower().endswith(".pdf")
    owner_restricted = False
    password_required = False
    authenticity_reasons = []
    authenticity = FileAuthenticity.PENDING
    file_status = FileStatus.UPLOADED
    bank_name = "-"
    account_holder = "-"
    masked_account_no = "-"

    if is_pdf:
        enc_info = detect_pdf_encryption(stored_path)
        is_encrypted = enc_info["is_encrypted"]
        password_required = enc_info["password_required"]
        owner_restricted = enc_info["owner_restricted"]
        password_protected = is_encrypted

        if password_required:
            file_status = FileStatus.PASSWORD_REQUIRED
            authenticity = FileAuthenticity.PENDING
            authenticity_reasons = ["Password required before authenticity check and text extraction"]
            sub_type = sub_type or "-"
            year = year or "-"
        else:
            if owner_restricted:
                try:
                    unlock_pdf_file(stored_path, "")
                except Exception:
                    pass
            file_status = FileStatus.UPLOADED
            auth_res = check_document_authenticity(
                stored_path,
                is_password_protected=password_protected,
                owner_restricted=owner_restricted,
            )
            authenticity = auth_res["status"]
            authenticity_reasons = auth_res["reasons"]

            try:
                if report.report_type.value == "GST":
                    from app.services.file_analysis_service import detect_gstr_document_type
                    detected_sub, det_conf, det_reason = detect_gstr_document_type(
                        file_path=stored_path,
                        file_name=file.filename,
                        hint_subtype=sub_type if sub_type and sub_type not in ("-", "AUTO", "auto") else None
                    )
                    if detected_sub != "UNKNOWN":
                        sub_type = detected_sub
                else:
                    doc = extract_pdf_document(stored_path)
                    meta = extract_document_metadata(doc)
                    if meta.get("account_type"):
                        sub_type = meta["account_type"]
                    if meta.get("statement_period"):
                        year = meta["statement_period"]
                    bank_name = meta.get("bank_name") or "-"
                    account_holder = meta.get("account_holder") or "-"
                    masked_account_no = _mask_acc_no(meta.get("account_no"))
            except Exception:
                pass

    if report.report_type.value == "GST" and (not sub_type or sub_type in ("-", "AUTO", "auto")):
        try:
            from app.services.file_analysis_service import detect_gstr_document_type
            detected_sub, det_conf, det_reason = detect_gstr_document_type(
                file_path=stored_path,
                file_name=file.filename,
            )
            if detected_sub != "UNKNOWN":
                sub_type = detected_sub
        except Exception:
            pass

    next_s_no = (db.query(ReportFile).filter(ReportFile.report_id == report.id).count()) + 1
    report_file = ReportFile(
        report_id=report.id,
        s_no=next_s_no,
        file_name=file.filename,
        stored_path=stored_path,
        sub_type=sub_type or "-",
        year=year or "-",
        bank_name=bank_name,
        account_holder=account_holder,
        masked_account_no=masked_account_no,
        password_protected=password_protected,
        owner_restricted=owner_restricted,
        file_status=file_status,
        authenticity=authenticity,
        authenticity_reasons=authenticity_reasons,
    )
    db.add(report_file)
    db.commit()
    db.refresh(report_file)
    return report_file


@router.post("/{report_id}/files/{file_id}/unlock", response_model=ReportFileOut)
def unlock_report_file(
    report_id: str,
    file_id: str,
    payload: UnlockFileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = _get_owned_report(report_id, current_user, db)
    report_file = db.query(ReportFile).filter(ReportFile.id == file_id, ReportFile.report_id == report.id).first()
    if not report_file:
        raise HTTPException(status_code=404, detail="File not found")

    password = payload.password
    try:
        unlock_pdf_file(report_file.stored_path, password)
    except ValueError:
        # Never log or expose password
        raise HTTPException(status_code=400, detail="Incorrect password, try again")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not unlock file: {str(e)}")

    report_file.file_status = FileStatus.UNLOCKED
    
    auth_res = check_document_authenticity(
        report_file.stored_path,
        is_password_protected=True,
        owner_restricted=False,
    )
    report_file.authenticity = auth_res["status"]
    report_file.authenticity_reasons = auth_res["reasons"]

    try:
        if report.report_type.value == "GST":
            from app.services.file_analysis_service import detect_gstr_document_type
            detected_sub, det_conf, det_reason = detect_gstr_document_type(
                file_path=report_file.stored_path,
                file_name=report_file.file_name,
            )
            if detected_sub != "UNKNOWN":
                report_file.sub_type = detected_sub
        else:
            doc = extract_pdf_document(report_file.stored_path)
            meta = extract_document_metadata(doc)
            if meta.get("account_type"):
                report_file.sub_type = meta["account_type"]
            if meta.get("statement_period"):
                report_file.year = meta["statement_period"]
            report_file.bank_name = meta.get("bank_name") or "-"
            report_file.account_holder = meta.get("account_holder") or "-"
            report_file.masked_account_no = _mask_acc_no(meta.get("account_no"))
    except Exception:
        pass

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
def analyse_report(
    report_id: str,
    payload: dict = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = _get_owned_report(report_id, current_user, db)
    if not report.files:
        raise HTTPException(status_code=400, detail="Upload at least one file before analysing")

    locked_files = [f for f in report.files if f.file_status == FileStatus.PASSWORD_REQUIRED]
    if locked_files:
        raise HTTPException(status_code=400, detail="Please unlock all password-protected files before starting analysis.")

    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.org_id).first()
    if subscription and subscription.credits_left <= 0:
        raise HTTPException(status_code=402, detail="No credits left. Please upgrade your plan.")

    report.status = ReportStatus.PROCESSING
    for f in report.files:
        f.file_status = FileStatus.PROCESSING
    db.commit()

    def update_progress(current: int, total: int, message: str):
        set_report_progress(report.id, current, total, message)

    update_progress(0, 1, "Initializing analysis...")

    file_paths = [f.stored_path for f in report.files]

    try:
        summary = run_analysis(
            report.report_type,
            file_paths,
            account_holder=current_user.name,
            progress_callback=update_progress,
        )

        details_map = {d.get("file_name"): d for d in summary.get("details", [])}
        for f in report.files:
            detail = details_map.get(f.file_name, {})
            txns = detail.get("transactions", [])
            is_stats = bool(detail.get("is_filing_statistics"))
            if txns or is_stats:
                f.file_status = FileStatus.PROCESSED
                auth_res = check_document_authenticity(
                    f.stored_path,
                    parsed_transactions=txns,
                    meta=detail,
                    is_password_protected=f.password_protected,
                    owner_restricted=f.owner_restricted,
                )
                f.authenticity = auth_res["status"]
                f.authenticity_reasons = auth_res["reasons"]
                detail["authenticity"] = auth_res
                summary["authenticity"] = auth_res
                if "analytics" in summary and isinstance(summary["analytics"], dict):
                    summary["analytics"]["authenticity"] = auth_res
                if detail.get("account_holder") and (not f.account_holder or f.account_holder == "-"):
                    f.account_holder = detail["account_holder"]
                if detail.get("statement_period") and (not f.year or f.year == "-"):
                    f.year = detail["statement_period"]
            else:
                f.file_status = FileStatus.FAILED
                f.authenticity = FileAuthenticity.UNVERIFIABLE
                f.authenticity_reasons = [detail.get("note") or "No transactions extracted"]

        report.result_summary = summary
        report.status = ReportStatus.READY_TO_USE
        report.analysed_at = datetime.utcnow()

        if subscription:
            subscription.credits_used = min(subscription.credits_used + 0.5, subscription.credits_total)

        update_progress(100, 100, "Analysis complete. Report ready!")
        db.commit()
        db.refresh(report)
        return report
    except Exception as e:
        report.status = ReportStatus.FAILED
        for f in report.files:
            if f.file_status == FileStatus.PROCESSING:
                f.file_status = FileStatus.FAILED
        db.commit()
        set_report_progress(report.id, 0, 1, f"Analysis failed: {str(e)}", stage="error")
        raise


@router.get("/{report_id}/progress")
def get_report_progress_status(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = _get_owned_report(report_id, current_user, db)
    prog = get_report_progress(report.id)
    return {
        "report_id": report.id,
        "status": report.status.value,
        **prog
    }


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

    safe_filename = filename.replace('"', '').replace(',', '_')
    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
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
