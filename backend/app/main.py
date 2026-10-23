from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import Base, engine
from app import models  # noqa: F401  (ensures models are registered before create_all)
from app.routers import auth, dashboard, reports, team, billing, support

from sqlalchemy import inspect, text

# Auto-create tables on startup. For production, use Alembic migrations instead.
Base.metadata.create_all(bind=engine)
try:
    insp = inspect(engine)
    if "report_files" in insp.get_table_names():
        existing_cols = {c["name"] for c in insp.get_columns("report_files")}
        with engine.begin() as conn:
            if "bank_name" not in existing_cols:
                conn.execute(text("ALTER TABLE report_files ADD COLUMN IF NOT EXISTS bank_name VARCHAR(100)"))
            if "account_holder" not in existing_cols:
                conn.execute(text("ALTER TABLE report_files ADD COLUMN IF NOT EXISTS account_holder VARCHAR(255)"))
            if "masked_account_no" not in existing_cols:
                conn.execute(text("ALTER TABLE report_files ADD COLUMN IF NOT EXISTS masked_account_no VARCHAR(50)"))
            if "owner_restricted" not in existing_cols:
                conn.execute(text("ALTER TABLE report_files ADD COLUMN IF NOT EXISTS owner_restricted BOOLEAN DEFAULT FALSE"))
            if "authenticity_reasons" not in existing_cols:
                conn.execute(text("ALTER TABLE report_files ADD COLUMN IF NOT EXISTS authenticity_reasons JSON"))

            # Ensure PostgreSQL ENUMs are converted to VARCHAR(50) and normalized
            if conn.dialect.name == "postgresql":
                try:
                    res = conn.execute(text(
                        "SELECT column_name, data_type FROM information_schema.columns "
                        "WHERE table_name = 'report_files' AND column_name IN ('file_status', 'authenticity')"
                    )).fetchall()
                    col_types = {row[0]: row[1].lower() for row in res}
                    if col_types.get("file_status") == "user-defined":
                        conn.execute(text("ALTER TABLE report_files ALTER COLUMN file_status DROP DEFAULT"))
                        conn.execute(text("ALTER TABLE report_files ALTER COLUMN file_status TYPE VARCHAR(50) USING file_status::text"))
                        conn.execute(text("ALTER TABLE report_files ALTER COLUMN file_status SET DEFAULT 'Uploaded'"))
                    if col_types.get("authenticity") == "user-defined":
                        conn.execute(text("ALTER TABLE report_files ALTER COLUMN authenticity DROP DEFAULT"))
                        conn.execute(text("ALTER TABLE report_files ALTER COLUMN authenticity TYPE VARCHAR(50) USING authenticity::text"))
                        conn.execute(text("ALTER TABLE report_files ALTER COLUMN authenticity SET DEFAULT 'Pending'"))
                except Exception:
                    pass

            try:
                conn.execute(text("UPDATE report_files SET file_status = 'Processed' WHERE file_status = 'PROCESSED'"))
                conn.execute(text("UPDATE report_files SET file_status = 'Uploaded' WHERE file_status = 'UPLOADED'"))
                conn.execute(text("UPDATE report_files SET file_status = 'Processing' WHERE file_status = 'PROCESSING'"))
                conn.execute(text("UPDATE report_files SET file_status = 'Failed' WHERE file_status IN ('FAILED', 'ERROR')"))
                conn.execute(text("UPDATE report_files SET file_status = 'Password required' WHERE file_status = 'PASSWORD_REQUIRED'"))
                conn.execute(text("UPDATE report_files SET file_status = 'Unlocked' WHERE file_status = 'UNLOCKED'"))

                conn.execute(text("UPDATE report_files SET authenticity = 'Original' WHERE authenticity IN ('VERIFIED', 'ORIGINAL')"))
                conn.execute(text("UPDATE report_files SET authenticity = 'Pending' WHERE authenticity = 'PENDING'"))
                conn.execute(text("UPDATE report_files SET authenticity = 'Suspicious' WHERE authenticity = 'SUSPICIOUS'"))
                conn.execute(text("UPDATE report_files SET authenticity = 'Tampered' WHERE authenticity = 'TAMPERED'"))
                conn.execute(text("UPDATE report_files SET authenticity = 'Unverifiable' WHERE authenticity = 'UNVERIFIABLE'"))
            except Exception:
                pass
except Exception:
    pass


app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
app.include_router(reports.router, prefix=api_prefix)
app.include_router(team.router, prefix=api_prefix)
app.include_router(billing.router, prefix=api_prefix)
app.include_router(support.router, prefix=api_prefix)


@app.get("/")
def root():
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
