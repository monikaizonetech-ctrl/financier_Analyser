import os
import shutil
import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status, Body
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
import sqlalchemy.exc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
import uuid

from app.core.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.billing import Subscription
from app.models.report import (
    Report,
    ReportFile,
    ReportType,
    ReportStatus,
    FileStatus,
    FileAuthenticity,
    ReportReferenceCounter,
    format_reference_id,
)
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
import threading

_large_pdf_semaphore = threading.Semaphore(1)


def _get_available_memory_mb() -> float | None:
    """Check available system memory in MB across Linux and Windows."""
    if os.path.exists("/proc/meminfo"):
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) / 1024.0
        except Exception:
            pass
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return stat.ullAvailPhys / (1024.0 * 1024.0)
    except Exception:
        pass
    return None


def _is_large_analysis(file_paths: list[str]) -> bool:
    for fp in file_paths:
        if fp.lower().endswith(".pdf") and os.path.exists(fp):
            try:
                # PDF >= 2MB is considered large and memory-sensitive
                if os.path.getsize(fp) >= 2 * 1024 * 1024:
                    return True
            except Exception:
                pass
    return False

router = APIRouter(prefix="/reports", tags=["Reports"])


def _normalize_report_type(report_type: ReportType | str) -> ReportType:
    if isinstance(report_type, ReportType):
        return report_type
    val = str(report_type).strip().upper()
    if val == "BANK":
        return ReportType.BSA
    if val in [e.value for e in ReportType]:
        return ReportType(val)
    return ReportType.BSA


def allocate_next_reference_id(db: Session, owner_id: str, report_type: ReportType | str) -> str:
    """
    Atomically allocates the next sequential reference ID for (owner_id, report_type)
    within the current transaction using PostgreSQL's ON CONFLICT DO UPDATE.
    Guarantees no race conditions or duplicates under concurrent creation.
    """
    rtype = _normalize_report_type(report_type)
    now = datetime.utcnow()
    stmt = (
        pg_insert(ReportReferenceCounter)
        .values(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            report_type=rtype,
            last_number=1,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["owner_id", "report_type"],
            set_={
                "last_number": ReportReferenceCounter.last_number + 1,
                "updated_at": now,
            },
        )
        .returning(ReportReferenceCounter.last_number)
    )
    result = db.execute(stmt)
    next_num = result.scalar_one()
    return format_reference_id(rtype, next_num)


def get_next_reference_id_preview(db: Session, owner_id: str, report_type: ReportType | str) -> str:
    """
    Read-only informational preview of the next reference ID for (owner_id, report_type).
    Does NOT increment or lock the counter table.
    """
    rtype = _normalize_report_type(report_type)
    counter = (
        db.query(ReportReferenceCounter)
        .filter(
            ReportReferenceCounter.owner_id == owner_id,
            ReportReferenceCounter.report_type == rtype,
        )
        .first()
    )
    next_num = (counter.last_number if counter else 0) + 1
    return format_reference_id(rtype, next_num)


def _org_user_ids(db: Session, current_user: User) -> list[str]:
    """All user ids belonging to the same team/org as current_user."""
    org_owner_id = current_user.org_id
    rows = db.query(User.id).filter(
        or_(User.id == org_owner_id, User.added_by_id == org_owner_id)
    ).all()
    return [r[0] for r in rows]


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # Generate reference ID atomically on backend; never trust frontend input
        ref_id = allocate_next_reference_id(db, current_user.id, payload.report_type)

        report = Report(
            name=payload.name,
            report_type=payload.report_type,
            owner_id=current_user.id,
            reference_id=ref_id,
        )
        db.add(report)
        db.commit()
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="A report with this Reference ID already exists."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not create report: {str(e)}"
        )
    db.refresh(report)
    return report


@router.get("/next-id")
def get_next_report_id(
    report_type: str = Query(default="BSA", description="Report type (BSA, GST, ITR)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rtype = _normalize_report_type(report_type)
    next_id = get_next_reference_id_preview(db, current_user.id, rtype)
    return {"next_id": next_id, "report_type": rtype.value}




@router.get("", response_model=PaginatedReports)
def list_my_reports(
    search: str | None = Query(default=None, description="Search by report name or reference id"),
    report_type: str | None = Query(default=None, description="Filter by report type (BSA, GST, ITR)"),
    sort_by: str = Query(default="created_at"),
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Report).filter(Report.owner_id == current_user.id)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Report.name.ilike(search_pattern),
                Report.reference_id.ilike(search_pattern),
            )
        )
    if report_type and report_type.upper() != "ALL":
        rtype = _normalize_report_type(report_type)
        query = query.filter(Report.report_type == rtype)

    sort_col = getattr(Report, sort_by, Report.created_at)
    query = query.order_by(sort_col.desc())

    items, total, page, page_size = paginate(query, page, page_size)
    return PaginatedReports(items=items, total=total, page=page, page_size=page_size)



@router.get("/team", response_model=PaginatedTeamReports)
def list_team_reports(
    search_email: str | None = None,
    search_name: str | None = None,
    report_type: str | None = Query(default=None, description="Filter by report type (BSA, GST, ITR)"),
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_ids = _org_user_ids(db, current_user)
    query = db.query(Report, User).join(User, Report.owner_id == User.id).filter(Report.owner_id.in_(org_ids))

    if search_email:
        query = query.filter(User.email.ilike(f"%{search_email.strip()}%"))
    if search_name:
        pattern = f"%{search_name.strip()}%"
        query = query.filter(
            or_(
                Report.name.ilike(pattern),
                Report.reference_id.ilike(pattern),
            )
        )
    if report_type and report_type.upper() != "ALL":
        rtype = _normalize_report_type(report_type)
        query = query.filter(Report.report_type == rtype)

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
    report_dir = os.path.join(settings.UPLOAD_DIR, report.id)
    os.makedirs(report_dir, exist_ok=True)
    stored_path = os.path.join(report_dir, file.filename)

    # Stream file to disk in 64KB chunks to avoid reading entire file into RAM
    total_bytes = 0
    with open(stored_path, "wb") as f:
        while True:
            chunk = file.file.read(65536)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                f.close()
                if os.path.exists(stored_path):
                    os.remove(stored_path)
                raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")
            f.write(chunk)

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
                    doc = extract_pdf_document(stored_path, max_pages=2)
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
    removed_name = report_file.file_name
    db.delete(report_file)

    if report.result_summary and isinstance(report.result_summary, dict):
        summary = dict(report.result_summary)
        details = summary.get("details", [])
        if details:
            summary["details"] = [d for d in details if d.get("file_name") != removed_name]
            summary["files_analysed"] = len(summary["details"])
            report.result_summary = summary
            flag_modified(report, "result_summary")

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

    target_file_id = payload.get("file_id") if payload and isinstance(payload, dict) else None
    if target_file_id:
        target_files = [f for f in report.files if f.id == target_file_id]
        if not target_files:
            raise HTTPException(status_code=404, detail="Selected file not found in report")
    else:
        target_files = report.files

    locked_files = [f for f in target_files if f.file_status == FileStatus.PASSWORD_REQUIRED]
    if locked_files:
        raise HTTPException(status_code=400, detail="Please unlock all password-protected files before starting analysis.")

    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.org_id).first()
    if subscription and subscription.credits_left <= 0:
        raise HTTPException(status_code=402, detail="No credits left. Please upgrade your plan.")

    report.status = ReportStatus.PROCESSING
    for f in target_files:
        f.file_status = FileStatus.PROCESSING
    db.commit()

    def update_progress(current: int, total: int, message: str):
        set_report_progress(report.id, current, total, message)

    file_paths = [f.stored_path for f in target_files]
    is_large = _is_large_analysis(file_paths)
    acquired_semaphore = False

    try:
        if is_large:
            avail_mb = _get_available_memory_mb()
            if avail_mb is not None and avail_mb < 150:
                import gc
                gc.collect()
                avail_mb = _get_available_memory_mb()
                if avail_mb is not None and avail_mb < 100:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Server memory is critically low. Please retry analysis in a moment."
                    )

            update_progress(0, 1, "Queued: Waiting for server capacity...")
            acquired_semaphore = _large_pdf_semaphore.acquire(timeout=600)
            if not acquired_semaphore:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Server is busy processing another large document. Please retry shortly."
                )

        update_progress(0, 1, "Initializing analysis...")

        summary = run_analysis(
            report.report_type,
            file_paths,
            account_holder=current_user.name,
            progress_callback=update_progress,
        )

        details_map = {d.get("file_name"): d for d in summary.get("details", [])}
        for f in target_files:
            detail = details_map.get(f.file_name, {})
            txns = detail.get("transactions", [])
            is_stats = bool(detail.get("is_filing_statistics"))
            if txns or is_stats:
                f.file_status = FileStatus.PROCESSED
                auth_res = detail.get("authenticity")
                if not auth_res:
                    auth_res = check_document_authenticity(
                        f.stored_path,
                        parsed_transactions=txns,
                        meta=detail,
                        is_password_protected=f.password_protected,
                        owner_restricted=f.owner_restricted,
                    )
                f.authenticity = auth_res.get("status", "Original")
                f.authenticity_reasons = auth_res.get("reasons", [])
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

        # Merge new/updated file details into existing report result_summary
        existing_summary = dict(report.result_summary or {})
        existing_details = existing_summary.get("details", [])
        
        # Build merged details list keyed by file_name so each file stays completely separate
        merged_details_dict = {d.get("file_name"): d for d in existing_details if d.get("file_name")}
        for d in summary.get("details", []):
            fname = d.get("file_name")
            if fname:
                merged_details_dict[fname] = d
        
        # Keep only details for files currently in the report
        current_names = {f.file_name for f in report.files}
        final_details = [d for fname, d in merged_details_dict.items() if fname in current_names]

        # Use new summary shell but with merged isolated file details
        final_summary = dict(summary)
        final_summary["details"] = final_details
        final_summary["files_analysed"] = len(final_details)
        final_summary["reference_id"] = report.reference_id

        report.result_summary = final_summary
        flag_modified(report, "result_summary")
        report.status = ReportStatus.READY_TO_USE
        report.analysed_at = datetime.utcnow()
        final_summary["analysed_at"] = report.analysed_at.isoformat()

        if subscription:
            subscription.credits_used = min(subscription.credits_used + 0.5, subscription.credits_total)

        update_progress(100, 100, "Analysis complete. Report ready!")
        db.commit()
        db.refresh(report)
        return report
    except Exception as e:
        report.status = ReportStatus.FAILED
        for f in target_files:
            if f.file_status == FileStatus.PROCESSING:
                f.file_status = FileStatus.FAILED
        try:
            db.commit()
        except Exception:
            db.rollback()

        set_report_progress(report.id, 0, 1, f"Analysis failed: {str(e)}", stage="error")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Analysis failed: {str(e)}"
        )
    finally:
        if acquired_semaphore:
            _large_pdf_semaphore.release()
        import gc
        gc.collect()


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

    summary_payload = dict(report.result_summary or {})
    summary_payload["reference_id"] = report.reference_id or summary_payload.get("reference_id")
    summary_payload["analysed_at"] = report.analysed_at.isoformat() if report.analysed_at else summary_payload.get("analysed_at")
    summary_payload["created_at"] = report.created_at.isoformat() if report.created_at else summary_payload.get("created_at")

    if file_format == "xlsx":
        content = build_excel_report(report.name, report.report_type.value, summary_payload)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{report.name}_{datetime.utcnow().strftime('%d_%b_%Y')}.xlsx"
    else:
        content = build_pdf_report(report.name, report.report_type.value, summary_payload)
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
