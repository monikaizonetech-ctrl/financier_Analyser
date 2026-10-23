from app.database import SessionLocal
from app.models.report import Report
import json

db = SessionLocal()
r = db.query(Report).filter(Report.id == 'c84379c7-9ffd-47e8-83b5-1a71b44cb6ea').first()
d = r.result_summary.get("details", [])[0]
print("File name:", d.get("file_name"))
print("File path:", d.get("file_path"))
print("Subtype:", d.get("subtype"))
print("is_filing_statistics:", d.get("is_filing_statistics"))
print("Transactions count:", len(d.get("transactions", [])))
print("Sample txns:", d.get("transactions", [])[:5])
db.close()
