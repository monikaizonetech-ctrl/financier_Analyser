from app.database import SessionLocal
from app.models.report import Report

db = SessionLocal()
reports = db.query(Report).filter(Report.name.ilike('%gst%')).order_by(Report.id.desc()).all()
print(f"Found {len(reports)} reports with 'gst'")
for r in reports:
    print("ID:", r.id, "Name:", r.name, "Type:", r.report_type, "Created:", r.created_at)
    if r.result_summary:
        d = r.result_summary.get("details", [])
        print("  detail count:", len(d))
        for item in d:
            print("    file_name:", item.get("file_name"), "is_filing_statistics:", item.get("is_filing_statistics"), "txns:", len(item.get("transactions", [])))
db.close()
