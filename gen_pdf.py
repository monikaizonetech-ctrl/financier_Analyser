import datetime
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from app.services.file_analysis_service import analyse_bank_statement, build_pdf_report  # type: ignore
except (ImportError, ModuleNotFoundError):
    from backend.app.services.file_analysis_service import analyse_bank_statement, build_pdf_report  # type: ignore

# Use the available test statement fixture
file_path = os.path.join(backend_dir, 'tests', 'fixtures', 'iob_2026-08-23_2026-09-23.pdf')
if not os.path.exists(file_path):
    file_path = os.path.abspath(r'backend/tests/fixtures/icici_2026-04-01_2026-09-30.pdf')

result = analyse_bank_statement(file_path, os.path.basename(file_path))
summary = {
    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "analytics": result.get("analytics", {}),
    "details": [{"has_data": True}],
}

pdf_bytes = build_pdf_report("IOB Statement Analysis", "BSA", summary)

output_pdf = os.path.join(os.path.dirname(__file__), 'test_out_final.pdf')
with open(output_pdf, 'wb') as f:
    f.write(pdf_bytes)

print(f"PDF generated successfully at {output_pdf} (size: {len(pdf_bytes)} bytes).")
