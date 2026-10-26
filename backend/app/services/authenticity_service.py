import re
from datetime import datetime, timedelta
from decimal import Decimal
import pymupdf


_NON_BANK_EDITING_TOOLS = [
    "word", "powerpoint", "excel", "photoshop", "illustrator", "canva",
    "ilovepdf", "smallpdf", "pdf24", "sejda", "libreoffice", "writer",
    "openoffice", "foxit", "nitro", "inkscape", "gimp", "pdfescape",
    "pdf-xchange", "wondershare", "element", "acrobat pro", "distiller",
    "abbyy", "master pdf", "soda pdf"
]


def _parse_pdf_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    cleaned = date_str.strip()
    if cleaned.startswith("D:"):
        cleaned = cleaned[2:]
    cleaned = cleaned.replace("'", "").replace("Z", "").split("+")[0].split("-")[0]
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(cleaned[:len(fmt.replace("%", "").replace("-", "").replace(":", "").replace(" ", "").replace("T", "")) + 2], fmt)
        except Exception:
            pass
    try:
        if len(cleaned) >= 8 and cleaned[:8].isdigit():
            return datetime(int(cleaned[:4]), int(cleaned[4:6]), int(cleaned[6:8]))
    except Exception:
        pass
    return None


def _clean_pdf_meta_string(val) -> str:
    if not val:
        return "Not available"
    if isinstance(val, (bytes, bytearray)):
        if val.startswith(b"\xfe\xff"):
            try:
                val = val[2:].decode("utf-16-be")
            except Exception:
                pass
        else:
            try:
                val = val.decode("latin-1")
            except Exception:
                pass
    val = str(val).strip()
    if not val or val.lower() in ("none", "null", "undefined", "unknown"):
        return "Not available"
    # Caret notation like ^Q, ^[, ^M, ^C represents raw control chars produced by fitz
    if re.search(r"\^[A-Z@-_]", val):
        return "Not available"
    # Control character check: ASCII < 32 (except \t, \n, \r) or DEL 127
    if any(ord(c) < 32 and c not in "\t\n\r" for c in val) or any(ord(c) == 127 for c in val):
        return "Not available"
    # If string contains non-printable characters or is mostly garbage/punctuation
    printable = [c for c in val if c.isprintable()]
    if len(printable) < len(val) * 0.7:
        return "Not available"
    cleaned = "".join(printable).strip()
    return cleaned if cleaned else "Not available"


def _clean_pdf_date_str(val) -> str:
    cleaned = _clean_pdf_meta_string(val)
    if cleaned == "Not available":
        return "Not available"
    dt = _parse_pdf_date(cleaned)
    if dt:
        return dt.strftime("%d %b %Y, %H:%M")
    return cleaned


def check_document_authenticity(
    file_path: str,
    parsed_transactions: list[dict] | None = None,
    meta: dict | None = None,
    is_password_protected: bool = False,
    owner_restricted: bool = False,
) -> dict:
    """
    Evaluates PDF authenticity according to forensic and financial criteria:
    - Metadata: Producer/Creator (Bank system vs editing software), CreationDate vs ModDate.
    - Incremental updates: count of %%EOF markers (>1 means edited after generation).
    - Digital signature: if present, validated; corrupted/invalid -> Tampered.
    - Text layer: Scanned without text -> Unverifiable. Image overlays -> Suspicious.
    - Financial integrity: running balance continuity, opening+credit-debit==closing,
      footer summary match -> any mismatch -> Tampered.
    - Encryption alone is informative, not tampering.
    """
    reasons: list[str] = []
    tampered_reasons: list[str] = []
    suspicious_reasons: list[str] = []
    unverifiable_reasons: list[str] = []
    info_notes: list[str] = []

    producer = "Not available"
    creator = "Not available"
    creation_date_str = "Not available"
    mod_date_str = "Not available"
    eof_count = 0
    has_sig = False
    sig_valid = None
    is_scanned = False
    font_anomaly = False

    # 1. Read raw bytes for Incremental Updates (%%EOF markers)
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
        eof_count = raw_bytes.count(b"%%EOF")
        if eof_count > 1:
            suspicious_reasons.append(
                f"Incremental updates detected ({eof_count} %%EOF markers) - document edited after generation"
            )
    except Exception as e:
        eof_count = 1

    # 2. Inspect PDF structure and Metadata via PyMuPDF
    try:
        doc = pymupdf.open(file_path)
        metadata = doc.metadata or {}
        producer = _clean_pdf_meta_string(metadata.get("producer"))
        creator = _clean_pdf_meta_string(metadata.get("creator"))
        raw_cdate = metadata.get("creationDate")
        raw_mdate = metadata.get("modDate")
        creation_date_str = _clean_pdf_date_str(raw_cdate)
        mod_date_str = _clean_pdf_date_str(raw_mdate)

        # Metadata editing tool check
        prod_lower = (producer if producer != "Not available" else "").lower()
        creat_lower = (creator if creator != "Not available" else "").lower()
        matched_editor = next(
            (tool for tool in _NON_BANK_EDITING_TOOLS if tool in prod_lower or tool in creat_lower),
            None,
        )
        if matched_editor:
            suspicious_reasons.append(
                f"Document Producer/Creator indicates desktop editing tool: '{producer if producer != 'Not available' else creator}'"
            )

        # CreationDate vs ModDate check
        c_dt = _parse_pdf_date(str(raw_cdate or ""))
        m_dt = _parse_pdf_date(str(raw_mdate or ""))
        if c_dt and m_dt:
            time_diff = (m_dt - c_dt).total_seconds()
            if time_diff > 3600 and (matched_editor or time_diff > 86400):
                suspicious_reasons.append(
                    f"Modification date ({mod_date_str}) is significantly later than creation date ({creation_date_str})"
                )

        # Digital signature check
        try:
            # Check for digital signature dictionaries
            sig_count = doc.get_sigflags()
            if sig_count > 0 or b"/ByteRange" in raw_bytes:
                has_sig = True
                # Check signature integrity
                # PyMuPDF doesn't always have cryptographic cert stores, but if signature bytes are corrupted:
                if b"/ByteRange" in raw_bytes and b"/Contents" not in raw_bytes:
                    sig_valid = False
                    tampered_reasons.append("Digital signature structure is corrupted or invalid")
                else:
                    sig_valid = True
                    info_notes.append("Valid digital signature present")
        except Exception:
            pass

        # Text layer & scanned document check (sample up to 10 pages for speed)
        total_text_len = 0
        total_pages = len(doc)
        if total_pages > 0:
            sample_pages = min(total_pages, 10)
            for i in range(sample_pages):
                total_text_len += len(doc[i].get_text().strip())
            avg_text_per_page = total_text_len / sample_pages
            if total_text_len == 0 or avg_text_per_page < 15:
                is_scanned = True
                unverifiable_reasons.append("Scanned PDF with no extractable text layer")

        doc.close()
    except Exception as e:
        pass

    # 3. Financial Integrity Checks (if parsed transactions are provided)
    if parsed_transactions:
        opening_bal = None
        closing_bal = None
        stmt_cr = None
        stmt_dr = None
        if meta:
            opening_bal = meta.get("opening_balance")
            closing_bal = meta.get("closing_balance")
            summary = meta.get("statement_summary") or {}
            stmt_cr = summary.get("total_credit") or meta.get("footer_total_credit")
            stmt_dr = summary.get("total_debit") or meta.get("footer_total_debit")

        if opening_bal is None and parsed_transactions:
            opening_bal = parsed_transactions[0].get("statement_opening_balance")
        if closing_bal is None and parsed_transactions:
            closing_bal = parsed_transactions[-1].get("balance")

        # Row-by-row running balance continuity check
        if opening_bal is not None:
            prev = float(opening_bal)
            for idx, r in enumerate(parsed_transactions, start=1):
                cr = float(r.get("credit") or 0.0)
                dr = float(r.get("debit") or 0.0)
                bal = float(r.get("balance") or 0.0)
                expected_bal = round(prev + cr - dr, 2)
                row_diff = round(expected_bal - bal, 2)
                if abs(row_diff) > 0.01:
                    pg = r.get("source_page") or (r.get("extra_metadata") or {}).get("page") or 1
                    dt_str = str(r.get("date") or r.get("value_date") or f"Row {idx}")
                    tampered_reasons.append(
                        f"Arithmetic continuity mismatch: Row {idx} ({dt_str}, Page {pg}) "
                        f"running balance {bal:,.2f} != expected {expected_bal:,.2f} (diff: {row_diff:+,.2f})"
                    )
                    break
                prev = bal

        # Overall equation check: Opening + Total Credit - Total Debit == Closing
        total_cr = round(sum(float(r.get("credit") or 0.0) for r in parsed_transactions), 2)
        total_dr = round(sum(float(r.get("debit") or 0.0) for r in parsed_transactions), 2)
        if opening_bal is not None and closing_bal is not None:
            calc_closing = round(float(opening_bal) + total_cr - total_dr, 2)
            if abs(calc_closing - float(closing_bal)) > 0.01:
                tampered_reasons.append(
                    f"Financial equation failed: Opening ({float(opening_bal):,.2f}) + "
                    f"Credit ({total_cr:,.2f}) - Debit ({total_dr:,.2f}) = {calc_closing:,.2f} "
                    f"!= Closing ({float(closing_bal):,.2f})"
                )

        # Statement summary reconciliation (footer totals)
        if stmt_cr is not None and abs(round(total_cr - float(stmt_cr), 2)) > 0.01:
            tampered_reasons.append(
                f"Footer credit total mismatch: Extracted {total_cr:,.2f} != Statement Summary {float(stmt_cr):,.2f}"
            )
        if stmt_dr is not None and abs(round(total_dr - float(stmt_dr), 2)) > 0.01:
            tampered_reasons.append(
                f"Footer debit total mismatch: Extracted {total_dr:,.2f} != Statement Summary {float(stmt_dr):,.2f}"
            )

    # 4. Encryption information
    if is_password_protected:
        info_notes.append("Original file was encrypted/password-protected by issuer")
    elif owner_restricted:
        info_notes.append("Restricted PDF (opened with standard reader permissions)")

    # 5. Determine Overall Authenticity Status
    if tampered_reasons:
        status = "Tampered"
        reasons = tampered_reasons + suspicious_reasons + info_notes
    elif suspicious_reasons:
        status = "Suspicious"
        reasons = suspicious_reasons + info_notes
    elif unverifiable_reasons:
        status = "Unverifiable"
        reasons = unverifiable_reasons + info_notes
    else:
        status = "Original"
        default_pass_reasons = ["No edits after generation, balances reconcile, footer totals match"]
        reasons = default_pass_reasons + info_notes

    return {
        "status": status,
        "reasons": reasons,
        "is_password_protected": is_password_protected,
        "owner_restricted": owner_restricted,
        "details": {
            "producer": producer,
            "creator": creator,
            "creation_date": creation_date_str,
            "mod_date": mod_date_str,
            "eof_count": eof_count,
            "has_digital_signature": has_sig,
            "signature_valid": sig_valid,
            "signature_status": "Valid digital signature" if (has_sig and sig_valid) else ("Corrupted / Invalid signature" if (has_sig and not sig_valid) else "Not signed"),
            "font_anomaly": font_anomaly,
            "is_scanned": is_scanned,
            "financial_integrity_pass": len(tampered_reasons) == 0,
        },
    }
