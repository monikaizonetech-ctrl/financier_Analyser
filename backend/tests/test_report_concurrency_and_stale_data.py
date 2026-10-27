import tempfile
import os
import uuid
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.main import app
from app.database import SessionLocal
from app.models.user import User, UserRole, UserStatus
from app.models.report import Report, ReportType, ReportStatus, ReportFile, FileStatus, FileAuthenticity
from app.models.billing import Subscription, PlanType, SubscriptionStatus
from app.core.security import hash_password, create_access_token
from app.routers.reports import _active_reports, _active_reports_lock
from app.services.progress_service import get_report_progress


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="function")
def test_setup():
    db: Session = SessionLocal()
    user_id = str(uuid.uuid4())

    user = User(
        id=user_id,
        email=f"concurrency_test_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("password123"),
        name="Concurrency Tester",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db.add(user)

    subscription = Subscription(
        id=str(uuid.uuid4()),
        user_id=user_id,
        plan=PlanType.PRO,
        status=SubscriptionStatus.ACTIVE,
        credits_total=10.0,
        credits_used=0.0,
    )
    db.add(subscription)
    db.commit()

    token = create_access_token(subject=user_id, extra_claims={"role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    yield {"user_id": user_id, "headers": headers, "db": db}

    # Cleanup
    with _active_reports_lock:
        _active_reports.clear()

    cleanup_db: Session = SessionLocal()
    cleanup_db.query(ReportFile).filter(
        ReportFile.report_id.in_(
            cleanup_db.query(Report.id).filter(Report.owner_id == user_id)
        )
    ).delete(synchronize_session=False)
    cleanup_db.query(Report).filter(Report.owner_id == user_id).delete(synchronize_session=False)
    cleanup_db.query(Subscription).filter(Subscription.user_id == user_id).delete(synchronize_session=False)
    cleanup_db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    cleanup_db.commit()
    cleanup_db.close()
    db.close()


def _create_report_with_file(db: Session, user_id: str, num_files: int = 1) -> tuple[Report, list[ReportFile]]:
    report = Report(
        id=str(uuid.uuid4()),
        reference_id=f"BSA_{uuid.uuid4().hex[:4]}",
        name="Test Report",
        report_type=ReportType.BSA,
        status=ReportStatus.NEED_TO_ANALYSE,
        owner_id=user_id,
    )
    db.add(report)

    files = []
    temp_dir = tempfile.gettempdir()
    for i in range(num_files):
        dummy_path = os.path.join(temp_dir, f"dummy_concurrency_{uuid.uuid4().hex[:6]}_{i}.pdf")
        with open(dummy_path, "wb") as f:
            f.write(b"%PDF-1.4 dummy content")
        rf = ReportFile(
            id=str(uuid.uuid4()),
            report_id=report.id,
            s_no=i + 1,
            file_name=f"test_statement_{i}.pdf",
            stored_path=dummy_path,
            file_status=FileStatus.UPLOADED,
            password_protected=False,
            owner_restricted=False,
        )
        db.add(rf)
        files.append(rf)

    db.commit()
    db.refresh(report)
    for rf in files:
        db.refresh(rf)
    return report, files


def test_successful_analysis(client, test_setup):
    db = test_setup["db"]
    user_id = test_setup["user_id"]
    headers = test_setup["headers"]

    report, files = _create_report_with_file(db, user_id, num_files=1)
    file_rf = files[0]

    mock_summary = {
        "status": "success",
        "details": [{
            "file_name": file_rf.file_name,
            "account_holder": "John Doe",
            "statement_period": "2023-2024",
            "transactions": [{"date": "2023-01-01", "amount": 1000.0, "type": "CREDIT"}],
            "authenticity": {"status": "Original", "reasons": []},
        }],
        "analytics": {},
    }

    with patch("app.routers.reports.run_analysis", return_value=mock_summary):
        resp = client.post(f"/api/v1/reports/{report.id}/analyse", headers=headers)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == ReportStatus.READY_TO_USE.value

    # Verify DB state
    db.expire_all()
    updated_report = db.query(Report).filter(Report.id == report.id).first()
    assert updated_report.status == ReportStatus.READY_TO_USE
    assert updated_report.files[0].file_status == FileStatus.PROCESSED
    assert updated_report.files[0].authenticity == FileAuthenticity.ORIGINAL

    # Verify credits deducted
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    assert sub.credits_used == 0.5

    # Verify active report lock released
    with _active_reports_lock:
        assert report.id not in _active_reports


def test_concurrent_analysis_rejected(client, test_setup):
    db = test_setup["db"]
    user_id = test_setup["user_id"]
    headers = test_setup["headers"]

    report, _ = _create_report_with_file(db, user_id, num_files=1)

    # 1. Simulate active report in memory set
    with _active_reports_lock:
        _active_reports.add(report.id)

    resp = client.post(f"/api/v1/reports/{report.id}/analyse", headers=headers)
    assert resp.status_code == 409
    assert "Analysis is already in progress for this report." in resp.json()["detail"]

    with _active_reports_lock:
        _active_reports.discard(report.id)

    # 2. Simulate report having PROCESSING status in DB
    report.status = ReportStatus.PROCESSING
    db.commit()

    resp2 = client.post(f"/api/v1/reports/{report.id}/analyse", headers=headers)
    assert resp2.status_code == 409
    assert "Analysis is already in progress for this report." in resp2.json()["detail"]


def test_concurrent_operations_rejected_while_processing(client, test_setup):
    db = test_setup["db"]
    user_id = test_setup["user_id"]
    headers = test_setup["headers"]

    report, files = _create_report_with_file(db, user_id, num_files=1)
    file_id = files[0].id

    # Mark report as processing
    report.status = ReportStatus.PROCESSING
    db.commit()

    # 1. Attempt upload
    upload_resp = client.post(
        f"/api/v1/reports/{report.id}/files",
        files={"file": ("test.pdf", b"%PDF-1.4 sample", "application/pdf")},
        headers=headers,
    )
    assert upload_resp.status_code == 409
    assert "Cannot upload files while report analysis is in progress." in upload_resp.json()["detail"]

    # 2. Attempt unlock
    unlock_resp = client.post(
        f"/api/v1/reports/{report.id}/files/{file_id}/unlock",
        json={"password": "dummy"},
        headers=headers,
    )
    assert unlock_resp.status_code == 409
    assert "Cannot unlock files while report analysis is in progress." in unlock_resp.json()["detail"]

    # 3. Attempt file delete
    del_file_resp = client.delete(
        f"/api/v1/reports/{report.id}/files/{file_id}",
        headers=headers,
    )
    assert del_file_resp.status_code == 409
    assert "Cannot delete files while report analysis is in progress." in del_file_resp.json()["detail"]

    # 4. Attempt report delete
    del_report_resp = client.delete(
        f"/api/v1/reports/{report.id}",
        headers=headers,
    )
    assert del_report_resp.status_code == 409
    assert "Cannot delete report while analysis is in progress." in del_report_resp.json()["detail"]


def test_stale_data_prevention_on_concurrent_deleted_file(client, test_setup):
    """
    Simulate the exact StaleDataError scenario:
    A file is deleted from the DB during run_analysis().
    The analyse_report endpoint must reload live records, expunge deleted ones,
    and commit without raising StaleDataError.
    """
    db = test_setup["db"]
    user_id = test_setup["user_id"]
    headers = test_setup["headers"]

    report, files = _create_report_with_file(db, user_id, num_files=2)
    file1, file2 = files[0], files[1]
    file2_id = file2.id

    def mock_run_analysis_with_concurrent_delete(*args, **kwargs):
        # In a separate DB session, delete file2 while analysis is supposedly running
        del_db: Session = SessionLocal()
        f2_to_delete = del_db.query(ReportFile).filter(ReportFile.id == file2_id).first()
        if f2_to_delete:
            del_db.delete(f2_to_delete)
            del_db.commit()
        del_db.close()

        return {
            "status": "success",
            "details": [
                {
                    "file_name": file1.file_name,
                    "account_holder": "User 1",
                    "statement_period": "2023",
                    "transactions": [{"date": "2023-01-01", "amount": 100.0, "type": "CREDIT"}],
                    "authenticity": {"status": "Original", "reasons": []},
                },
                {
                    "file_name": file2.file_name,
                    "account_holder": "User 2",
                    "statement_period": "2023",
                    "transactions": [{"date": "2023-01-01", "amount": 200.0, "type": "CREDIT"}],
                    "authenticity": {"status": "Original", "reasons": []},
                },
            ],
            "analytics": {},
        }

    with patch("app.routers.reports.run_analysis", side_effect=mock_run_analysis_with_concurrent_delete):
        resp = client.post(f"/api/v1/reports/{report.id}/analyse", headers=headers)

    # Must succeed without StaleDataError!
    assert resp.status_code == 200, resp.text
    db.expire_all()
    updated_report = db.query(Report).filter(Report.id == report.id).first()
    assert updated_report.status == ReportStatus.READY_TO_USE

    # file1 must be PROCESSED
    f1_check = db.query(ReportFile).filter(ReportFile.id == file1.id).first()
    assert f1_check is not None
    assert f1_check.file_status == FileStatus.PROCESSED

    # file2 must no longer exist in DB
    f2_check = db.query(ReportFile).filter(ReportFile.id == file2_id).first()
    assert f2_check is None


def test_failure_recovery_and_no_pending_rollback_error(client, test_setup):
    """
    Simulate run_analysis failure.
    Must roll back immediately, reload records, update report to FAILED,
    and NOT raise PendingRollbackError.
    """
    db = test_setup["db"]
    user_id = test_setup["user_id"]
    headers = test_setup["headers"]

    report, files = _create_report_with_file(db, user_id, num_files=1)

    with patch("app.routers.reports.run_analysis", side_effect=RuntimeError("Extraction engine internal crash")):
        resp = client.post(f"/api/v1/reports/{report.id}/analyse", headers=headers)

    # Expected HTTP 422 with original error message preserved
    assert resp.status_code == 422
    assert "Analysis failed: Extraction engine internal crash" in resp.json()["detail"]

    # Verify DB was properly updated to FAILED and not stuck in PROCESSING
    db.expire_all()
    updated_report = db.query(Report).filter(Report.id == report.id).first()
    assert updated_report.status == ReportStatus.FAILED
    assert updated_report.files[0].file_status == FileStatus.FAILED

    # Verify progress state
    prog = get_report_progress(report.id)
    assert prog["stage"] == "error"
    assert "Extraction engine internal crash" in prog["message"]

    # Verify active report lock released
    with _active_reports_lock:
        assert report.id not in _active_reports


def test_failure_recovery_when_commit_fails(client, test_setup):
    """
    Simulate a database error during the success commit.
    The exception handler must call rollback immediately, avoiding PendingRollbackError,
    and successfully record FAILED status.
    """
    db = test_setup["db"]
    user_id = test_setup["user_id"]
    headers = test_setup["headers"]

    report, files = _create_report_with_file(db, user_id, num_files=1)
    file_rf = files[0]

    mock_summary = {
        "status": "success",
        "details": [{
            "file_name": file_rf.file_name,
            "transactions": [{"date": "2023-01-01", "amount": 100.0, "type": "CREDIT"}],
        }],
    }

    # Patch db.commit to raise an OperationalError on the success commit
    original_commit = Session.commit
    commit_call_count = 0

    def mock_commit(self):
        nonlocal commit_call_count
        commit_call_count += 1
        # The 1st commit is when marking report as PROCESSING.
        # The 2nd commit is the one trying to mark as READY_TO_USE (line 757).
        if commit_call_count == 2:
            # Emulate an ORM flush failure that puts session in pending rollback
            self.rollback()  # triggers broken transaction state if attempted again without rollback
            raise OperationalError("Simulated database failure during flush", params=None, orig=Exception("DB broke"))
        return original_commit(self)

    with patch("app.routers.reports.run_analysis", return_value=mock_summary):
        with patch.object(Session, "commit", mock_commit):
            resp = client.post(f"/api/v1/reports/{report.id}/analyse", headers=headers)

    assert resp.status_code == 422
    assert "Simulated database failure" in resp.json()["detail"]

    # Verify that in a clean check, report is FAILED, not PROCESSING
    cleanup_check = SessionLocal()
    rep = cleanup_check.query(Report).filter(Report.id == report.id).first()
    assert rep.status == ReportStatus.FAILED
    cleanup_check.close()
