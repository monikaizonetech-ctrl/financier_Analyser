import json
from app.database import SessionLocal
from app.models.report import Report

db = SessionLocal()
reports = db.query(Report).order_by(Report.id.desc()).limit(5).all()
for r in reports:
    print("ID:", r.id, "Name:", r.name, "Type:", r.report_type, "Created:", r.created_at)
    if r.result_summary:
        print("Files analysed:", r.result_summary.get("files_analysed"))
        details = r.result_summary.get("details", [])
        for d in details:
            print("  Detail file_name:", d.get("file_name"))
            print("  Detail file_path:", d.get("file_path"))
            print("  Detail subtype:", d.get("subtype"))
            print("  Detail is_filing_statistics:", d.get("is_filing_statistics"))
            print("  Detail transactions count:", len(d.get("transactions", [])))
            if d.get("transactions"):
                print("  Sample txn:", d.get("transactions")[0])
    print("-" * 50)
db.close()
