from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.api import auth, reports

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FINANCIER ANALYZER API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])

@app.get("/")
def read_root():
    return {"message": "Welcome to FINANCIER ANALYZER API"}
