import sqlite3
import json

conn = sqlite3.connect('izone_finance.db')
cur = conn.cursor()
cur.execute("SELECT id, name, report_type, created_at, result_summary FROM reports ORDER BY id DESC LIMIT 5")
for r in cur.fetchall():
    print("ID:", r[0], "Name:", r[1], "Type:", r[2], "Created:", r[3])
    if r[4]:
        try:
            data = json.loads(r[4])
            print("Files analysed:", data.get("files_analysed"))
            details = data.get("details", [])
            for d in details:
                print("  Detail file_name:", d.get("file_name"))
                print("  Detail file_path:", d.get("file_path"))
                print("  Detail subtype:", d.get("subtype"))
                print("  Detail is_filing_statistics:", d.get("is_filing_statistics"))
                print("  Detail transactions count:", len(d.get("transactions", [])))
                if d.get("transactions"):
                    print("  First txn:", d.get("transactions")[0])
        except Exception as e:
            print("Error parsing json:", e)
    print("-" * 50)
