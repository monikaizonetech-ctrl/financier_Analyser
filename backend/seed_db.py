"""
Seed the PostgreSQL database with sample users, subscriptions, and reports
so the application can be explored immediately after setup.

Run with:  python seed_db.py
"""
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy import func, inspect
from app.core.security import hash_password
from app.database import Base, engine, SessionLocal
from app.models.billing import Subscription, Transaction, PlanType, SubscriptionStatus, TransactionType
from app.models.report import Report, ReportFile, ReportType, ReportStatus, FileStatus, FileAuthenticity
from app.models.user import User, UserRole, UserStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_schema():
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    if "report_files" in insp.get_table_names():
        existing_cols = {c["name"] for c in insp.get_columns("report_files")}
        with engine.begin() as conn:
            if "bank_name" not in existing_cols:
                conn.execute(sa.text("ALTER TABLE report_files ADD COLUMN IF NOT EXISTS bank_name VARCHAR(100)"))
            if "account_holder" not in existing_cols:
                conn.execute(sa.text("ALTER TABLE report_files ADD COLUMN IF NOT EXISTS account_holder VARCHAR(255)"))
            if "masked_account_no" not in existing_cols:
                conn.execute(sa.text("ALTER TABLE report_files ADD COLUMN IF NOT EXISTS masked_account_no VARCHAR(50)"))
            if "owner_restricted" not in existing_cols:
                conn.execute(sa.text("ALTER TABLE report_files ADD COLUMN IF NOT EXISTS owner_restricted BOOLEAN DEFAULT FALSE"))
            if "authenticity_reasons" not in existing_cols:
                conn.execute(sa.text("ALTER TABLE report_files ADD COLUMN IF NOT EXISTS authenticity_reasons JSON"))

            # Convert PostgreSQL ENUMs to VARCHAR(50) if present
            if conn.dialect.name == "postgresql":
                try:
                    res = conn.execute(sa.text(
                        "SELECT column_name, data_type FROM information_schema.columns "
                        "WHERE table_name = 'report_files' AND column_name IN ('file_status', 'authenticity')"
                    )).fetchall()
                    col_types = {row[0]: row[1].lower() for row in res}
                    if col_types.get("file_status") == "user-defined":
                        conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN file_status DROP DEFAULT"))
                        conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN file_status TYPE VARCHAR(50) USING file_status::text"))
                        conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN file_status SET DEFAULT 'Uploaded'"))
                    if col_types.get("authenticity") == "user-defined":
                        conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN authenticity DROP DEFAULT"))
                        conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN authenticity TYPE VARCHAR(50) USING authenticity::text"))
                        conn.execute(sa.text("ALTER TABLE report_files ALTER COLUMN authenticity SET DEFAULT 'Pending'"))
                except Exception:
                    pass

            # Normalize uppercase enum values to Python string values
            try:
                conn.execute(sa.text("UPDATE report_files SET file_status = 'Processed' WHERE file_status = 'PROCESSED'"))
                conn.execute(sa.text("UPDATE report_files SET file_status = 'Uploaded' WHERE file_status = 'UPLOADED'"))
                conn.execute(sa.text("UPDATE report_files SET file_status = 'Processing' WHERE file_status = 'PROCESSING'"))
                conn.execute(sa.text("UPDATE report_files SET file_status = 'Failed' WHERE file_status IN ('FAILED', 'ERROR')"))
                conn.execute(sa.text("UPDATE report_files SET file_status = 'Password required' WHERE file_status = 'PASSWORD_REQUIRED'"))
                conn.execute(sa.text("UPDATE report_files SET file_status = 'Unlocked' WHERE file_status = 'UNLOCKED'"))

                conn.execute(sa.text("UPDATE report_files SET authenticity = 'Original' WHERE authenticity IN ('VERIFIED', 'ORIGINAL')"))
                conn.execute(sa.text("UPDATE report_files SET authenticity = 'Pending' WHERE authenticity = 'PENDING'"))
                conn.execute(sa.text("UPDATE report_files SET authenticity = 'Suspicious' WHERE authenticity = 'SUSPICIOUS'"))
                conn.execute(sa.text("UPDATE report_files SET authenticity = 'Tampered' WHERE authenticity = 'TAMPERED'"))
                conn.execute(sa.text("UPDATE report_files SET authenticity = 'Unverifiable' WHERE authenticity = 'UNVERIFIABLE'"))
            except Exception:
                pass


def get_available_reference_id(db_session, preferred_ref: str) -> str:
    if not db_session.query(Report).filter(Report.reference_id == preferred_ref).first():
        return preferred_ref
    from app.models.report import gen_reference_id
    return gen_reference_id()


def seed_database():
    ensure_schema()
    db = SessionLocal()

    try:
        sysadmin_email = "admin@financier.com"
        admin_email = "monika@izoneanalyzer.in"
        manager_email = "ravi.manager@izoneanalyzer.in"
        member_email = "ananya.member@izoneanalyzer.in"

        # 0. System Administrator (Generic fallback)
        sysadmin = db.query(User).filter(func.lower(User.email) == sysadmin_email.lower()).first()
        if not sysadmin:
            sysadmin = User(
                name="System Administrator",
                email=sysadmin_email,
                phone="+919000000000",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
            )
            db.add(sysadmin)
            db.flush()
            print(f"Created System Admin user: {sysadmin.email}")
        else:
            print(f"System Admin user already exists: {sysadmin.email}")

        # 1. Admin User
        admin = db.query(User).filter(func.lower(User.email) == admin_email.lower()).first()
        if not admin:
            admin = User(
                name="Monika",
                email=admin_email,
                phone="+919363778750",
                hashed_password=hash_password("Admin@123"),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
            )
            db.add(admin)
            db.flush()
            print(f"Created Admin user: {admin.email}")
        else:
            print(f"Admin user already exists: {admin.email}")

        # 2. Manager User
        manager = db.query(User).filter(func.lower(User.email) == manager_email.lower()).first()
        if not manager:
            manager = User(
                name="Ravi Kumar",
                email=manager_email,
                phone="+919876543210",
                hashed_password=hash_password("Manager@123"),
                role=UserRole.MANAGER,
                status=UserStatus.ACTIVE,
                added_by_id=admin.id,
            )
            db.add(manager)
            db.flush()
            print(f"Created Manager user: {manager.email}")
        else:
            print(f"Manager user already exists: {manager.email}")

        # 3. Member User
        member = db.query(User).filter(func.lower(User.email) == member_email.lower()).first()
        if not member:
            member = User(
                name="Ananya Sharma",
                email=member_email,
                phone="+919876500000",
                hashed_password=hash_password("Member@123"),
                role=UserRole.MEMBER,
                status=UserStatus.ACTIVE,
                added_by_id=admin.id,
            )
            db.add(member)
            db.flush()
            print(f"Created Member user: {member.email}")
        else:
            print(f"Member user already exists: {member.email}")

        # 4. Subscriptions
        now = utc_now()
        for user in (sysadmin, admin, manager, member):
            sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            if not sub:
                credits = 10.0 if user.id == sysadmin.id else 2.5
                db.add(
                    Subscription(
                        user_id=user.id,
                        plan=PlanType.FREE_TRIAL,
                        status=SubscriptionStatus.ACTIVE,
                        credits_total=credits,
                        credits_used=0,
                        started_at=now,
                        expires_at=now + timedelta(days=3),
                    )
                )
                print(f"Created Free Trial subscription for user: {user.email}")

        # 5. Sample Reports
        report1 = db.query(Report).filter(Report.name == "BANK (BSA)", Report.owner_id == admin.id).first()
        if not report1:
            ref1 = get_available_reference_id(db, "1")
            report1 = Report(
                name="BANK (BSA)",
                reference_id=ref1,
                report_type=ReportType.BSA,
                status=ReportStatus.NEED_TO_ANALYSE,
                owner_id=admin.id,
            )
            db.add(report1)
            db.flush()
            print(f"Created sample report 1: {report1.name} (Ref: {report1.reference_id})")

        report2 = db.query(Report).filter(Report.name == "BANKSTATEMENT (BSA Reports)", Report.owner_id == admin.id).first()
        if not report2:
            ref2 = get_available_reference_id(db, "2")
            report2 = Report(
                name="BANKSTATEMENT (BSA Reports)",
                reference_id=ref2,
                report_type=ReportType.BSA,
                status=ReportStatus.READY_TO_USE,
                owner_id=admin.id,
                analysed_at=now,
                result_summary={
                    "report_type": "BSA",
                    "files_analysed": 1,
                    "generated_at": now.isoformat(),
                    "details": [
                        {
                            "transactions_found": 128,
                            "total_credits": 452300.0,
                            "total_debits": 398250.0,
                            "closing_balance": 54050.0,
                            "net_cash_flow": 54050.0,
                        }
                    ],
                },
            )
            db.add(report2)
            db.flush()
            print(f"Created sample report 2: {report2.name} (Ref: {report2.reference_id})")

        # Report file attached to report 2
        existing_file = db.query(ReportFile).filter(
            ReportFile.report_id == report2.id,
            ReportFile.file_name == "OTHER_BANKS_AND_FINANCIAL_INSTITUTIONS_4821.pdf",
        ).first()
        if not existing_file:
            db.add(
                ReportFile(
                    report_id=report2.id,
                    s_no=1,
                    file_name="OTHER_BANKS_AND_FINANCIAL_INSTITUTIONS_4821.pdf",
                    stored_path="uploads/seed/OTHER_BANKS_AND_FINANCIAL_INSTITUTIONS_4821.pdf",
                    sub_type="Other Banks",
                    year="2026",
                    file_status=FileStatus.PROCESSED.value,
                    authenticity=FileAuthenticity.VERIFIED.value,
                )
            )
            db.flush()
            print(f"Created seed file for report: {report2.name}")
        else:
            # Ensure proper values if existing record had outdated values
            updated = False
            if existing_file.file_status != FileStatus.PROCESSED.value:
                existing_file.file_status = FileStatus.PROCESSED.value
                updated = True
            if existing_file.authenticity != FileAuthenticity.VERIFIED.value:
                existing_file.authenticity = FileAuthenticity.VERIFIED.value
                updated = True
            if updated:
                db.flush()

        # 6. Sample Transaction
        existing_tx = db.query(Transaction).filter(
            Transaction.user_id == admin.id,
            Transaction.type == TransactionType.CREDIT_PURCHASE
        ).first()
        if not existing_tx:
            db.add(
                Transaction(
                    user_id=admin.id,
                    type=TransactionType.CREDIT_PURCHASE,
                    amount=0,
                    description="Free trial activated (2.5 credits)",
                )
            )

        db.commit()
        print("\nSeed data check/creation completed successfully.")
        print("\nTest login credentials:")
        print("  SysAdmin-> admin@financier.com / admin123")
        print("  Admin   -> monika@izoneanalyzer.in / Admin@123")
        print("  Manager -> ravi.manager@izoneanalyzer.in / Manager@123")
        print("  Member  -> ananya.member@izoneanalyzer.in / Member@123")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
