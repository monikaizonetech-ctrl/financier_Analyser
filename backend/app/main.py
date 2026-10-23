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
