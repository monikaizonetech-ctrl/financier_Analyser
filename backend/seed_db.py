"""
Seed the PostgreSQL database with sample users, subscriptions, and reports
so the application can be explored immediately after setup.

Run with:  python seed_db.py
"""
from datetime import datetime, timedelta

from app.core.security import hash_password
from app.database import Base, engine, SessionLocal
from app.models.billing import Subscription, Transaction, PlanType, SubscriptionStatus, TransactionType
from app.models.report import Report, ReportFile, ReportType, ReportStatus, FileStatus, FileAuthenticity
from app.models.user import User, UserRole, UserStatus

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    if db.query(User).filter(User.email == "monika@proanalyser.in").first():
        print("Seed data already present. Skipping.")
    else:
        admin = User(
            name="Monika",
            email="monika@proanalyser.in",
            phone="+919363778750",
            hashed_password=hash_password("Admin@123"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(admin)
        db.flush()

        manager = User(
            name="Ravi Kumar",
            email="ravi.manager@proanalyser.in",
            phone="+919876543210",
            hashed_password=hash_password("Manager@123"),
            role=UserRole.MANAGER,
            status=UserStatus.ACTIVE,
            added_by_id=admin.id,
        )
        member = User(
            name="Ananya Sharma",
            email="ananya.member@proanalyser.in",
            phone="+919876500000",
            hashed_password=hash_password("Member@123"),
            role=UserRole.MEMBER,
            status=UserStatus.ACTIVE,
            added_by_id=admin.id,
        )
        db.add_all([manager, member])
        db.flush()

        for user in (admin, manager, member):
            db.add(
                Subscription(
                    user_id=user.id,
                    plan=PlanType.FREE_TRIAL,
                    status=SubscriptionStatus.ACTIVE,
                    credits_total=2.5,
                    credits_used=0,
                    started_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=3),
                )
            )

        report1 = Report(
            name="BANK (BSA)",
            reference_id="20260820102702_A1B2",
            report_type=ReportType.BSA,
            status=ReportStatus.NEED_TO_ANALYSE,
            owner_id=admin.id,
        )
        report2 = Report(
            name="BANKSTATEMENT (BSA Reports)",
            reference_id="20260820103500_C3D4",
            report_type=ReportType.BSA,
            status=ReportStatus.READY_TO_USE,
            owner_id=admin.id,
            analysed_at=datetime.utcnow(),
            result_summary={
                "report_type": "BSA",
                "files_analysed": 1,
                "generated_at": datetime.utcnow().isoformat(),
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
        db.add_all([report1, report2])
        db.flush()

        db.add(
            ReportFile(
                report_id=report2.id,
                s_no=1,
                file_name="OTHER_BANKS_AND_FINANCIAL_INSTITUTIONS_4821.pdf",
                stored_path="uploads/seed/OTHER_BANKS_AND_FINANCIAL_INSTITUTIONS_4821.pdf",
                sub_type="Other Banks",
                year="2026",
                file_status=FileStatus.PROCESSED,
                authenticity=FileAuthenticity.VERIFIED,
            )
        )

        db.add(
            Transaction(
                user_id=admin.id,
                type=TransactionType.CREDIT_PURCHASE,
                amount=0,
                description="Free trial activated (2.5 credits)",
            )
        )

        db.commit()
        print("Seed data created successfully.")
        print("\nTest login credentials:")
        print("  Admin   -> monika@proanalyser.in / Admin@123")
        print("  Manager -> ravi.manager@proanalyser.in / Manager@123")
        print("  Member  -> ananya.member@proanalyser.in / Member@123")
finally:
    db.close()
