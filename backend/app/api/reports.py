from io import BytesIO
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.core import Document, Applicant
from app.models.report import Report
from app.services.file_analysis_service import build_excel_report, build_pdf_report
from app.services.reports import excel_generator, pdf_generator

router = APIRouter()

@router.get("/history")
def get_reports_history(db: Session = Depends(get_db)):
    # Query real documents/applications if available
    documents = db.query(Document).all()
    items = []
    for doc in documents:
        app = doc.application
        applicant = app.applicant if app else None
        items.append({
            "id": doc.id,
            "applicant_id": applicant.id if applicant else (app.applicant_id if app else "UNKNOWN"),
            "applicant_name": applicant.name if applicant else (applicant.business_name if applicant and applicant.business_name else "Applicant"),
            "module": doc.type.lower() if doc.type else "document",
            "module_title": doc.name,
            "document_name": doc.name,
            "status": doc.processing_status,
            "score": (doc.extracted_data or {}).get("score", 0) if isinstance(doc.extracted_data, dict) else 0,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        })
    return {
        "status": "success",
        "total": len(items),
        "items": items
    }

@router.get("/{applicant_id}/{module}/excel")
def download_excel(applicant_id: str, module: str, db: Session = Depends(get_db)):
    module = module.lower()
    
    if module == "bank":
        report = db.query(Report).filter(
            (Report.id == applicant_id) | (Report.reference_id == applicant_id)
        ).first()
        if report and report.result_summary:
            content = build_excel_report(report.name, "BSA", report.result_summary)
            file_stream = BytesIO(content)
            filename = f"{report.name}.xlsx"
        else:
            doc = db.query(Document).filter(Document.id == applicant_id).first()
            if doc and doc.extracted_data:
                content = build_excel_report(doc.name, "BSA", doc.extracted_data)
                file_stream = BytesIO(content)
                filename = f"{doc.name}.xlsx"
            else:
                raise HTTPException(status_code=404, detail="Bank statement report not found or not analysed yet")
    elif module == "gst":
        file_stream = excel_generator.generate_gst_excel(applicant_id)
        filename = f"GST_Analysis_{applicant_id}.xlsx"
    elif module == "itr":
        file_stream = excel_generator.generate_itr_excel(applicant_id)
        filename = f"ITR_Analysis_{applicant_id}.xlsx"
    elif module == "loan":
        file_stream = excel_generator.generate_loan_excel(applicant_id)
        filename = f"Loan_Analysis_{applicant_id}.xlsx"
    else:
        raise HTTPException(status_code=400, detail="Invalid module specified")

    return StreamingResponse(
        file_stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/{applicant_id}/{module}/pdf")
def download_pdf(applicant_id: str, module: str, db: Session = Depends(get_db)):
    module = module.lower()
    
    if module == "bank":
        report = db.query(Report).filter(
            (Report.id == applicant_id) | (Report.reference_id == applicant_id)
        ).first()
        if report and report.result_summary:
            content = build_pdf_report(report.name, "BSA", report.result_summary)
            file_stream = BytesIO(content)
            filename = f"{report.name}.pdf"
        else:
            doc = db.query(Document).filter(Document.id == applicant_id).first()
            if doc and doc.extracted_data:
                content = build_pdf_report(doc.name, "BSA", doc.extracted_data)
                file_stream = BytesIO(content)
                filename = f"{doc.name}.pdf"
            else:
                raise HTTPException(status_code=404, detail="Bank statement report not found or not analysed yet")
    elif module == "gst":
        file_stream = pdf_generator.generate_gst_pdf(applicant_id)
        filename = f"GST_Analysis_{applicant_id}.pdf"
    elif module == "itr":
        file_stream = pdf_generator.generate_itr_pdf(applicant_id)
        filename = f"ITR_Analysis_{applicant_id}.pdf"
    elif module == "loan":
        file_stream = pdf_generator.generate_loan_pdf(applicant_id)
        filename = f"Loan_Analysis_{applicant_id}.pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid module specified")

    return StreamingResponse(
        file_stream, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
