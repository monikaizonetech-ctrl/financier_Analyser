import concurrent.futures
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User, UserRole, UserStatus
from app.models.report import Report, ReportType, ReportReferenceCounter
from app.core.security import hash_password, create_access_token


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def test_users():
    db = SessionLocal()
    # Create User 1
    u1_id = str(uuid.uuid4())
    u1 = User(
        id=u1_id,
        email=f"ref_test_u1_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("password123"),
        name="Ref Test User 1",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    # Create User 2
    u2_id = str(uuid.uuid4())
    u2 = User(
        id=u2_id,
        email=f"ref_test_u2_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("password123"),
        name="Ref Test User 2",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db.add(u1)
    db.add(u2)
    db.commit()

    token1 = create_access_token(subject=u1_id, extra_claims={"role": u1.role.value})
    token2 = create_access_token(subject=u2_id, extra_claims={"role": u2.role.value})

    db.close()

    yield {
        "user1": {"id": u1_id, "token": token1, "headers": {"Authorization": f"Bearer {token1}"}},
        "user2": {"id": u2_id, "token": token2, "headers": {"Authorization": f"Bearer {token2}"}},
    }

    # Teardown
    cleanup_db = SessionLocal()
    cleanup_db.query(Report).filter(Report.owner_id.in_([u1_id, u2_id])).delete(synchronize_session=False)
    cleanup_db.query(ReportReferenceCounter).filter(ReportReferenceCounter.owner_id.in_([u1_id, u2_id])).delete(synchronize_session=False)
    cleanup_db.query(User).filter(User.id.in_([u1_id, u2_id])).delete(synchronize_session=False)
    cleanup_db.commit()
    cleanup_db.close()


def test_independent_reference_ids_per_user_and_type(client, test_users):
    u1_headers = test_users["user1"]["headers"]
    u2_headers = test_users["user2"]["headers"]

    # 1. User 1 creates GST report -> GST_001
    r1 = client.post("/api/v1/reports", json={"name": "U1 GST 1", "report_type": "GST"}, headers=u1_headers)
    assert r1.status_code == 201, r1.text
    assert r1.json()["reference_id"] == "GST_001"

    # 2. User 1 creates another GST report -> GST_002
    r2 = client.post("/api/v1/reports", json={"name": "U1 GST 2", "report_type": "GST"}, headers=u1_headers)
    assert r2.status_code == 201, r2.text
    assert r2.json()["reference_id"] == "GST_002"

    # 3. User 2 creates GST report -> GST_001 (Independent per user)
    r3 = client.post("/api/v1/reports", json={"name": "U2 GST 1", "report_type": "GST"}, headers=u2_headers)
    assert r3.status_code == 201, r3.text
    assert r3.json()["reference_id"] == "GST_001"

    # 4. User 1 creates BSA report -> BSA_001 (Independent per report type)
    r4 = client.post("/api/v1/reports", json={"name": "U1 BSA 1", "report_type": "BSA"}, headers=u1_headers)
    assert r4.status_code == 201, r4.text
    assert r4.json()["reference_id"] == "BSA_001"

    # 5. User 2 creates BSA report -> BSA_001
    r5 = client.post("/api/v1/reports", json={"name": "U2 BSA 1", "report_type": "BSA"}, headers=u2_headers)
    assert r5.status_code == 201, r5.text
    assert r5.json()["reference_id"] == "BSA_001"

    # 6. User 1 creates ITR report -> ITR_001
    r6 = client.post("/api/v1/reports", json={"name": "U1 ITR 1", "report_type": "ITR"}, headers=u1_headers)
    assert r6.status_code == 201, r6.text
    assert r6.json()["reference_id"] == "ITR_001"

    # 7. User 1 creates another ITR report -> ITR_002
    r7 = client.post("/api/v1/reports", json={"name": "U1 ITR 2", "report_type": "ITR"}, headers=u1_headers)
    assert r7.status_code == 201, r7.text
    assert r7.json()["reference_id"] == "ITR_002"


def test_preview_endpoint_does_not_advance_counter(client, test_users):
    u1_headers = test_users["user1"]["headers"]

    # Preview next GST for User 1 (should be GST_003 because GST_001 and GST_002 exist)
    prev1 = client.get("/api/v1/reports/next-id?report_type=GST", headers=u1_headers)
    assert prev1.status_code == 200
    assert prev1.json()["next_id"] == "GST_003"

    # Call preview again - must STILL be GST_003 (read-only, does not increment)
    prev2 = client.get("/api/v1/reports/next-id?report_type=GST", headers=u1_headers)
    assert prev2.status_code == 200
    assert prev2.json()["next_id"] == "GST_003"

    # Preview BSA for User 1 (should be BSA_002)
    prev_bsa = client.get("/api/v1/reports/next-id?report_type=BSA", headers=u1_headers)
    assert prev_bsa.status_code == 200
    assert prev_bsa.json()["next_id"] == "BSA_002"


def test_ignore_client_supplied_reference_id(client, test_users):
    u1_headers = test_users["user1"]["headers"]

    # User 1 tries to supply custom or duplicate reference_id
    res = client.post(
        "/api/v1/reports",
        json={"name": "U1 Spoofed", "report_type": "GST", "reference_id": "SPOOFED_999"},
        headers=u1_headers,
    )
    assert res.status_code == 201
    # Backend must assign the real sequential ID (GST_003), ignoring SPOOFED_999
    assert res.json()["reference_id"] == "GST_003"


def test_concurrency_no_duplicates(test_users):
    """
    Test concurrent creation of reports under high concurrency.
    PostgreSQL atomic UPSERT counter must serialize increments cleanly without duplicates.
    """
    u1_id = test_users["user1"]["id"]
    u1_token = test_users["user1"]["token"]

    def create_report_worker(idx):
        thread_client = TestClient(app)
        res = thread_client.post(
            "/api/v1/reports",
            json={"name": f"Concurrent GST {idx}", "report_type": "GST"},
            headers={"Authorization": f"Bearer {u1_token}"},
        )
        return res.status_code, res.json()

    # Fire 10 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_report_worker, i) for i in range(10)]
        results = [f.result() for f in futures]

    status_codes = [r[0] for r in results]
    assert all(code == 201 for code in status_codes), f"Some concurrent creations failed: {results}"

    ref_ids = [r[1]["reference_id"] for r in results]
    # Verify all generated reference IDs are completely distinct (no duplicates!)
    assert len(ref_ids) == len(set(ref_ids)), f"Duplicate reference IDs detected: {ref_ids}"
    # Verify they match the GST_XXX pattern
    for rid in ref_ids:
        assert rid.startswith("GST_")


def test_authorization_and_ownership(client, test_users):
    u1_headers = test_users["user1"]["headers"]
    u2_headers = test_users["user2"]["headers"]

    # Create report for User 1
    r1 = client.post("/api/v1/reports", json={"name": "Private Report", "report_type": "BSA"}, headers=u1_headers).json()
    u1_report_id = r1["id"]
    u1_ref_id = r1["reference_id"]

    # User 2 lists their reports - should NOT see User 1's report
    u2_reports = client.get("/api/v1/reports", headers=u2_headers).json()["items"]
    u2_report_ids = [r["id"] for r in u2_reports]
    assert u1_report_id not in u2_report_ids

    # User 2 attempts to get User 1's report directly by UUID
    unauth_res = client.get(f"/api/v1/reports/{u1_report_id}", headers=u2_headers)
    assert unauth_res.status_code in (403, 404)


