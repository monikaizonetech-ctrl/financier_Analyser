"""
Seed administrator user and initial data.
Run with: python seed.py
"""
from sqlalchemy import func
from app.database import Base, engine, SessionLocal
from app.models.user import User, UserRole, UserStatus
from app.models.billing import Subscription, PlanType, SubscriptionStatus
from app.core.security import hash_password
from seed_db import seed_database


def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(func.lower(User.email) == "admin@financier.com").first()
        if not admin:
            new_admin = User(
                email="admin@financier.com",
                hashed_password=hash_password("admin123"),
                name="System Administrator",
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
            )
            db.add(new_admin)
            db.flush()
            db.add(
                Subscription(
                    user_id=new_admin.id,
                    plan=PlanType.FREE_TRIAL,
                    status=SubscriptionStatus.ACTIVE,
                    credits_total=10.0,
                    credits_used=0,
                )
            )
            db.commit()
            print("Admin user (admin@financier.com) created successfully!")
        else:
            print("Admin user (admin@financier.com) already exists.")

        # Also seed the standard demonstration datasets
        seed_database()
    finally:
        db.close()


if __name__ == "__main__":
    seed_db()
