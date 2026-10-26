"""
Robust PDF extraction layer for bank statements.

Extracts text, positioned word blocks, and reconstructs physical lines
independent of visual layout, borders, or column alignment.
Detects repeated headers, column headers, footers, and isolates
the candidate transaction region per page.
"""
from dataclasses import dataclass, field
from enum import Enum
import os
import re
from typing import Any

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


class LineType(str, Enum):
    HEADER = "HEADER"
    COLUMN_HEADER = "COLUMN_HEADER"
    FOOTER = "FOOTER"
    TRANSACTION_CANDIDATE = "TRANSACTION_CANDIDATE"
    METADATA = "METADATA"
    UNKNOWN = "UNKNOWN"


@dataclass
class ExtractedWord:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    width: float = 0.0
    height: float = 0.0

    def __post_init__(self):
        if not self.width:
            self.width = max(0.0, self.x1 - self.x0)
        if not self.height:
            self.height = max(0.0, self.bottom - self.top)


@dataclass
class ExtractedLine:
    line_number: int
    text: str
    y_top: float
    y_bottom: float
    words: list[ExtractedWord] = field(default_factory=list)
    line_type: LineType = LineType.UNKNOWN
    page_number: int = 1

    @property
    def is_transaction_candidate(self) -> bool:
        return self.line_type == LineType.TRANSACTION_CANDIDATE


@dataclass
class ExtractedPage:
    page_number: int
    width: float
    height: float
    raw_text: str
    character_count: int
    lines: list[ExtractedLine] = field(default_factory=list)
    header_lines: list[ExtractedLine] = field(default_factory=list)
    footer_lines: list[ExtractedLine] = field(default_factory=list)
    transaction_lines: list[ExtractedLine] = field(default_factory=list)
    raw_tables: list[list[list[str | None]]] = field(default_factory=list)
    is_scanned: bool = False


@dataclass
class ExtractedDocument:
    file_path: str
    file_name: str
    total_pages_in_pdf: int = 0
    pages_processed: int = 0
    is_valid: bool = True
    is_scanned: bool = False
    is_encrypted: bool = False
    error_message: str | None = None
    warning_messages: list[str] = field(default_factory=list)
    pages: list[ExtractedPage] = field(default_factory=list)
    raw_debug_text: str = ""
    bank_name: str = ""
    account_holder: str = ""
    account_no: str = ""
    masked_account_no: str = ""
    statement_period: str = ""
    opening_balance: float | None = None
    closing_balance: float | None = None
    currency: str = "INR"

    @property
    def number_of_pages(self) -> int:
        return self.total_pages_in_pdf or len(self.pages)

    @property
    def raw_text(self) -> str:
        return self.raw_debug_text

    @property
    def all_transaction_lines(self) -> list[ExtractedLine]:
        lines = []
        for p in self.pages:
            lines.extend(p.transaction_lines)
        return lines


# Common keywords for header and footer identification
_COLUMN_HEADER_KEYWORDS = [
    "date", "txn date", "trans date", "value date", "posting date",
    "particulars", "description", "narration", "remarks", "details", "transaction details",
    "chq", "cheque", "ref no", "reference", "utr", "instrument",
    "debit", "debits", "withdrawal", "withdrawals", "dr",
    "credit", "credits", "deposit", "deposits", "cr",
    "balance", "closing balance", "running balance"
]

_FOOTER_PATTERNS = [
    r"(?:page\s+)?\d+\s+(?:of|\/)\s+\d+",
    r"\b\d+\s*\/\s*\d+\s*$",
    r"continued\s+(?:on|to)\s+next\s+page",
    r"this\s+is\s+a\s+computer[\s-]generated\s+(?:statement|document|copy)",
    r"registered\s+office",
    r"corporate\s+office",
    r"end\s+of\s+statement",
    r"generated\s+(?:on|at)\s*:",
    r"cin\s*:",
    r"gstin\s*:",
    r"toll[\s-]free",
    r"www\.[a-z0-9\.\-_]+\.[a-z]{2,}",
    r"hdfc\s+bank\s+limited",
    r"\*?closing\s*balance\s*includes",
    r"contents\s*of\s*this\s*statement\s*will\s*be\s*considered",
    r"the\s*address\s*on\s*this\s*statement\s*is\s*that\s*on\s*record",
    r"state\s*account\s*branch\s*gstn",
    r"registered\s*office\s*address",
    r"this\s*is\s*a\s*computer[\s-]generated\s*statement",
    r"statement\s*summary\s*:-?",
    r"opening\s*balance\s+dr\s*count\s+cr\s*count",
    r"openingbalance\s+drcount\s+crcount",
    r"notrequiresignature",
    r"senapati\s*bapat\s*marg",
    r"^this\s*statement\.?",
    r"^thisstatement\.?",
    r"daysofrequesting",
]

_METADATA_HEADER_PATTERNS = [
    r"statement\s+of\s+account",
    r"account\s+statement",
    r"account\s+(?:number|no|#)",
    r"customer\s+(?:id|name)",
    r"account\s+holder",
    r"branch\s+name",
    r"ifsc\s*(?:code)?",
    r"micr\s*(?:code)?",
    r"statement\s+period",
]


_DATE_START_REGEX = re.compile(
    r"^\s*(?:\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}[-/\.\s][A-Za-z]{3}[-/\.\s]\d{2,4})"
)


def _starts_with_date(text: str) -> bool:
    """Return True if text begins with a date pattern."""
    return bool(_DATE_START_REGEX.search(text))


def _is_column_header_line(text: str) -> bool:
    """Check whether a line matches expected bank table column headers."""
    if _starts_with_date(text):
        return False
    lowered = text.lower()
    # Reject lines containing summary or account metadata labels
    if re.search(r"\b(?:account\s+number|account\s+no|total\s+credits|total\s+debits|opening\s+balance|ending\s+balance|closing\s+balance)\b", lowered):
        return False

    matches = sum(1 for kw in _COLUMN_HEADER_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", lowered))
    has_date = bool(re.search(r"\b(?:date|txn\s+date|value\s+date)\b", lowered))
    has_amount = bool(re.search(r"\b(?:debit|debits|credit|credits|withdrawal|withdrawals|deposit|deposits|balance|closing\s+balance)\b", lowered))
    return (matches >= 3) or (has_date and has_amount and len(lowered.split()) >= 3)


def _is_footer_line(text: str, y_top: float, page_height: float) -> bool:
    """Check if a line looks like a footer based on position and patterns."""
    lowered = text.lower().strip()
    if not lowered:
        return False
    # If in the bottom 18% of the page
    in_bottom_zone = y_top >= (page_height * 0.82)
    # Check regex patterns
    matches_pattern = any(re.search(pat, lowered, re.IGNORECASE) for pat in _FOOTER_PATTERNS)
    if matches_pattern:
        return True
    if in_bottom_zone:
        if any(w in lowered for w in ("thisstatement", "disclaimer", "hdfc bank", "senapati", "lower parel", "gstn", "closingbalance", "unclearedfunds", "earmarked")):
            return True
        # Check for simple page indicators like "Page 1" or single word disclaimers
        if re.search(r"^page\s+\d+", lowered) or "thank you for banking" in lowered:
            return True
    return False


def _reconstruct_lines_from_words(words: list[dict], page_height: float, y_tolerance: float = 3.0) -> list[ExtractedLine]:
    """
    Cluster positioned words into physical lines using vertical baseline clustering.
    Words with close vertical top/bottom coordinates are grouped together,
    then sorted horizontally (x0).
    """
    if not words:
        return []

    # Sort words primarily by vertical position (top), secondarily by x0
    sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))

    lines_raw: list[list[dict]] = []
    line_meta: list[dict] = []  # Running metadata per line: sum_top, sum_bottom, count

    for word in sorted_words:
        # Filter out empty or whitespace words
        t = word.get("text", "").strip()
        if not t:
            continue

        placed = False
        w_top = float(word["top"])
        w_bottom = float(word["bottom"])
        w_mid = (w_top + w_bottom) / 2.0

        # Since sorted_words is sorted by top, matching lines are almost always
        # at the very end of lines_raw. Check recent lines first (last 10).
        num_lines = len(lines_raw)
        search_start = max(0, num_lines - 10)

        for i in range(num_lines - 1, search_start - 1, -1):
            meta = line_meta[i]
            cnt = meta["count"]
            avg_top = meta["sum_top"] / cnt
            avg_bottom = meta["sum_bottom"] / cnt
            avg_mid = (avg_top + avg_bottom) / 2.0

            # Tolerant vertical overlap check
            if abs(w_mid - avg_mid) <= y_tolerance or (w_top >= avg_top - y_tolerance and w_bottom <= avg_bottom + y_tolerance):
                lines_raw[i].append(word)
                meta["sum_top"] += w_top
                meta["sum_bottom"] += w_bottom
                meta["count"] += 1
                placed = True
                break

        if not placed:
            lines_raw.append([word])
            line_meta.append({
                "sum_top": w_top,
                "sum_bottom": w_bottom,
                "count": 1,
            })

    # Sort lines by their average vertical top position
    lines_raw.sort(key=lambda group: sum(w["top"] for w in group) / len(group))

    reconstructed: list[ExtractedLine] = []
    for idx, group in enumerate(lines_raw, start=1):
        # Sort words in each line horizontally
        group.sort(key=lambda w: w["x0"])
        
        extracted_words = [
            ExtractedWord(
                text=w.get("text", ""),
                x0=float(w.get("x0", 0.0)),
                x1=float(w.get("x1", 0.0)),
                top=float(w.get("top", 0.0)),
                bottom=float(w.get("bottom", 0.0)),
            )
            for w in group
        ]

        # Join text preserving approximate relative space
        line_text = " ".join(w.text for w in extracted_words).strip()
        y_top = min(w.top for w in extracted_words)
        y_bottom = max(w.bottom for w in extracted_words)

        reconstructed.append(
            ExtractedLine(
                line_number=idx,
                text=line_text,
                y_top=round(y_top, 2),
                y_bottom=round(y_bottom, 2),
                words=extracted_words,
            )
        )

    return reconstructed


def extract_pdf_document(
    file_path: str,
    max_pages: int | None = None,
    password: str | None = None,
    progress_callback = None,
) -> ExtractedDocument:
    """
    Primary entry point: Validates and extracts bank statement PDF content
    up to max_pages (or all pages if None) without making layout or column assumptions.
    """
    file_name = os.path.basename(file_path)
    doc = ExtractedDocument(file_path=file_path, file_name=file_name)

    if not os.path.exists(file_path):
        doc.is_valid = False
        doc.error_message = f"File not found: {file_path}"
        return doc

    import hashlib
    import logging
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            file_hash = hashlib.sha256(file_bytes).hexdigest()
        logging.info(f"extracted from {file_name}, sha256={file_hash}")
    except Exception as e:
        logging.warning(f"Failed to hash {file_name}: {e}")

    if pdfplumber is None:
        doc.is_valid = False
        doc.error_message = "pdfplumber is not installed on the server"
        return doc

    try:
        with pdfplumber.open(file_path, password=password) as pdf:
            total_pages = len(pdf.pages)
            doc.total_pages_in_pdf = total_pages

            if total_pages == 0:
                doc.is_valid = False
                doc.error_message = "PDF document contains 0 pages"
                return doc

            if max_pages is not None and total_pages > max_pages:
                doc.warning_messages.append(
                    f"Statement has {total_pages} pages. Processing the first {max_pages} pages per configuration."
                )

            pages_to_process = min(total_pages, max_pages) if max_pages is not None else total_pages
            doc.pages_processed = pages_to_process

            debug_text_chunks = []
            total_chars = 0

            for page_idx in range(pages_to_process):
                page = pdf.pages[page_idx]
                page_num = page_idx + 1

                if progress_callback:
                    try:
                        progress_callback(page_num, pages_to_process, f"Processing page {page_num} of {pages_to_process}...")
                    except Exception:
                        pass
                p_width = float(page.width)
                p_height = float(page.height)

                raw_page_text = page.extract_text() or ""
                debug_text_chunks.append(f"--- PAGE {page_num} ---\n{raw_page_text}")
                char_count = len(raw_page_text.strip())
                total_chars += char_count

                # Extract positioned words
                words = page.extract_words(
                    x_tolerance=2,
                    y_tolerance=3,
                    keep_blank_chars=False,
                    use_text_flow=True,
                ) or []

                # Reconstruct structured lines
                lines = _reconstruct_lines_from_words(words, p_height)
                for line in lines:
                    line.page_number = page_num

                # Extract raw tables if pdfplumber detects any (useful auxiliary context)
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    tables = []

                extracted_page = ExtractedPage(
                    page_number=page_num,
                    width=p_width,
                    height=p_height,
                    raw_text=raw_page_text,
                    character_count=char_count,
                    lines=lines,
                    raw_tables=tables,
                    is_scanned=False,
                )

                # Classify lines on this page
                _classify_page_lines(extracted_page, page_num, pages_to_process)
                doc.pages.append(extracted_page)

            doc.raw_debug_text = "\n\n".join(debug_text_chunks)

            # Check if PDF appears to be a scanned document (insufficient selectable text)
            avg_chars_per_page = total_chars / max(1, pages_to_process)
            if avg_chars_per_page < 30:
                doc.is_scanned = True
                for p in doc.pages:
                    p.is_scanned = True
                doc.warning_messages.append(
                    "The PDF contains insufficient selectable text and may be a scanned image or protected document."
                )

    except Exception as exc:
        doc.is_valid = False
        doc.error_message = f"Failed to read PDF file: {str(exc)}"

    return doc


def _classify_page_lines(page: ExtractedPage, page_num: int, total_pages: int):
    """
    Classify reconstructed lines into HEADER, COLUMN_HEADER, FOOTER,
    and TRANSACTION_CANDIDATE regions.
    Guarantees that lines starting with transaction dates or continuing
    transaction narratives are not erroneously marked as footers.
    """
    lines = page.lines
    if not lines:
        return

    p_height = page.height
    header_zone_y = p_height * 0.35 if page_num == 1 else p_height * 0.20
    footer_zone_y = p_height * 0.88

    column_header_found = False
    column_header_idx = -1

    # First pass: identify column headers and explicit footers
    for idx, line in enumerate(lines):
        # 1. Footer check: Only if explicit footer pattern matches AND does not start with a date
        if _is_footer_line(line.text, line.y_top, p_height) and not _starts_with_date(line.text):
            line.line_type = LineType.FOOTER
            page.footer_lines.append(line)
            continue

        # 2. Column header check (usually in upper 40% of page)
        if not column_header_found and line.y_top <= header_zone_y * 1.6:
            if _is_column_header_line(line.text):
                line.line_type = LineType.COLUMN_HEADER
                page.header_lines.append(line)
                column_header_found = True
                column_header_idx = idx
                continue

        # 3. Bank metadata/title header in the top zone before column header
        if not column_header_found and line.y_top <= header_zone_y:
            # Browser print headers (about:blank, y <= 25 with timestamp) are always headers
            if ("about:blank" in line.text.lower() or line.y_top <= 25.0) and re.search(r"about:blank|\bhttps?://|\b\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}", line.text.lower()):
                line.line_type = LineType.HEADER
                page.header_lines.append(line)
                continue
            # On continuation pages without repeated column headers, a line starting with a date
            # is a transaction, not a header!
            if page_num > 1 and _starts_with_date(line.text):
                pass
            else:
                line.line_type = LineType.HEADER
                page.header_lines.append(line)
                continue

    # Second pass: classify remaining lines
    for idx, line in enumerate(lines):
        if line.line_type in (LineType.HEADER, LineType.COLUMN_HEADER, LineType.FOOTER):
            continue

        # Browser print headers are never transactions
        if ("about:blank" in line.text.lower() or line.y_top <= 25.0) and re.search(r"about:blank|\bhttps?://|\b\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}", line.text.lower()):
            line.line_type = LineType.HEADER
            page.header_lines.append(line)
            continue

        # Any line starting with a date is always a transaction candidate
        if _starts_with_date(line.text):
            line.line_type = LineType.TRANSACTION_CANDIDATE
            page.transaction_lines.append(line)
            continue


        if column_header_found:
            if idx > column_header_idx:
                # Check for explicit footer
                if _is_footer_line(line.text, line.y_top, p_height):
                    line.line_type = LineType.FOOTER
                    page.footer_lines.append(line)
                else:
                    line.line_type = LineType.TRANSACTION_CANDIDATE
                    page.transaction_lines.append(line)
            else:
                line.line_type = LineType.HEADER
                page.header_lines.append(line)
        else:
            # If no explicit column header line on this page
            if line.y_top <= header_zone_y:
                line.line_type = LineType.HEADER
                page.header_lines.append(line)
            elif _is_footer_line(line.text, line.y_top, p_height):
                line.line_type = LineType.FOOTER
                page.footer_lines.append(line)
            else:
                line.line_type = LineType.TRANSACTION_CANDIDATE
                page.transaction_lines.append(line)


_IFSC_BANK_MAP = {
    "IOBA": "INDIAN OVERSEAS BANK",
    "IDIB": "INDIAN BANK",
    "SBIN": "STATE BANK OF INDIA",
    "HDFC": "HDFC BANK",
    "ICIC": "ICICI BANK",
    "UTIB": "AXIS BANK",
    "KKBK": "KOTAK MAHINDRA BANK",
    "CNRB": "CANARA BANK",
    "BARB": "BANK OF BARODA",
    "PUNB": "PUNJAB NATIONAL BANK",
    "YESB": "YES BANK",
    "UBIN": "UNION BANK OF INDIA",
    "CBIN": "CENTRAL BANK OF INDIA",
    "BKID": "BANK OF INDIA",
    "MAHB": "BANK OF MAHARASHTRA",
    "PSIB": "PUNJAB & SIND BANK",
    "UCOB": "UCO BANK",
}


def extract_document_metadata(doc: ExtractedDocument) -> dict:
    """
    Extract account holder, account number, bank name, account type,
    statement period, opening balance, and closing balance from document lines.
    """
    meta = {
        "bank_name": "BANK",
        "account_holder": "",
        "account_no": "",
        "account_type": "Savings",
        "statement_period": "",
        "opening_balance": None,
        "closing_balance": None,
    }
    if not doc.pages:
        return meta

    p1 = doc.pages[0]

    # 0. Check for specific statement header patterns (e.g., ICICI Corporate / Detailed Statement)
    for line in (p1.header_lines + p1.lines[:15]):
        t = line.text.strip()
        m = re.search(r"Transactions\s+List\s*-\s*-?\s*([^(]+?)\s*\((?:INR|[A-Z]{3})\)\s*-\s*([0-9X]+)", t, re.IGNORECASE)
        if m:
            meta["account_holder"] = m.group(1).strip(" -")
            meta["account_no"] = m.group(2).strip()
            meta["bank_name"] = "ICICI BANK"
            meta["account_type"] = "Current"
            break

    # 1. First priority: Check IFSC code in page 1 header lines only (avoid counterparty IFSC in transaction rows)
    if meta["bank_name"] == "BANK":
        candidate_texts_for_ifsc = [l.text for l in p1.header_lines] + [l.text for l in p1.lines[:10] if "ifsc" in l.text.lower()]
        for text in candidate_texts_for_ifsc:
            ifsc_m = re.search(r"\b([A-Z]{4})0[A-Z0-9]{6}\b", text)
            if ifsc_m:
                code = ifsc_m.group(1).upper()
                if code in _IFSC_BANK_MAP:
                    meta["bank_name"] = _IFSC_BANK_MAP[code]
                    break

    # 2. If IFSC not found, scan header and footer lines across pages for known bank names
    if meta["bank_name"] == "BANK":
        known_banks = [
            (r"\bindian\s+overseas\s+bank\b|\biob\b", "INDIAN OVERSEAS BANK"),
            (r"\bindian\s+bank\b", "INDIAN BANK"),
            (r"\bstate\s+bank\s+of\s+india\b|\bsbi\b", "STATE BANK OF INDIA"),
            (r"\bhdfc\s+bank\b|\bhdfc\b", "HDFC BANK"),
            (r"\bicici\s+bank\b|\bicici\b", "ICICI BANK"),
            (r"\baxis\s+bank\b|\baxis\b", "AXIS BANK"),
            (r"\bkotak(?:\s+mahindra)?\s+bank\b", "KOTAK MAHINDRA BANK"),
            (r"\bcanara\s+bank\b", "CANARA BANK"),
            (r"\byes\s+bank\b", "YES BANK"),
            (r"\bbank\s+of\s+baroda\b|\bbob\b", "BANK OF BARODA"),
            (r"\bpunjab\s+national\s+bank\b|\bpnb\b", "PUNJAB NATIONAL BANK"),
            (r"\bunion\s+bank\s+of\s+india\b", "UNION BANK OF INDIA"),
        ]
        bank_found = False
        for p in doc.pages:
            for line in (p.header_lines + p.footer_lines):
                t = line.text.strip()
                lowered = t.lower()
                for pattern, canonical_name in known_banks:
                    if re.search(pattern, lowered):
                        meta["bank_name"] = canonical_name
                        bank_found = True
                        break
                if bank_found:
                    break
            if bank_found:
                break

        # Fallback: scan lines not containing UPI or account masks
        if not bank_found:
            for p in doc.pages:
                for line in p.lines:
                    t = line.text.strip()
                    lowered = t.lower()
                    if "/upi" in lowered or "/xxxx" in lowered or "@" in lowered:
                        continue
                    for pattern, canonical_name in known_banks:
                        if re.search(pattern, lowered):
                            meta["bank_name"] = canonical_name
                            bank_found = True
                            break
                    if bank_found:
                        break
                if bank_found:
                    break

        # Look for Bank Name in top header lines of page 1 if not already found
        if meta["bank_name"] == "BANK":
            for line in p1.header_lines[:4]:
                t = line.text.strip()
                if any(kw in t.lower() for kw in ("bank", "financial", "co-operative", "corporation")):
                    cleaned = re.sub(r"\s*[\u2013\-\|].*$", "", t).strip()
                    if cleaned:
                        meta["bank_name"] = cleaned.upper()
                        break

    # Look for account holder, account number, account type, balances across all header/metadata lines
    all_candidate_lines = [l.text for l in p1.header_lines] + [l.text for l in p1.lines[:25]]
    if p1.raw_tables:
        for tbl in p1.raw_tables[:2]:
            for r in tbl:
                for c in r:
                    if c:
                        all_candidate_lines.extend(str(c).split("\n"))

    for idx, text in enumerate(all_candidate_lines):
        lowered = text.lower()
        if ("account holder" in lowered or "customer name" in lowered or "name of account holder" in lowered) and not meta["account_holder"]:
            holder = ""
            # Case 1: previous line starts with ':' (e.g. IOB format where value was wrapped/split across columns)
            if idx > 0 and all_candidate_lines[idx - 1].strip().startswith(":"):
                p_text = re.sub(r"^:\s*", "", all_candidate_lines[idx - 1].strip())
                p_part = p_text.split(",")[0].strip().split()[0] if p_text else ""
                c_clean = re.sub(r"(?:name\s+of\s+account\s+holder|account\s+holder(?:\s+name)?|customer\s+name)[\s:]*", "", text, flags=re.IGNORECASE).strip()
                c_part = c_clean.split()[0] if c_clean else ""
                if p_part and c_part and not re.search(r"NAGAPATTINAM|TAMIL", c_part, re.IGNORECASE):
                    holder = f"{p_part} {c_part}"

            # Case 2: two-column separate label/value block (e.g. test_account_holder_raw)
            if not holder:
                cleaned = re.sub(r"(?:name\s+of\s+account\s+holder|account\s+holder(?:\s+name)?|customer\s+name)[\s:]*", "", text, flags=re.IGNORECASE).strip()
                if not cleaned:
                    label_lines = [l.strip() for l in all_candidate_lines if re.match(r"^(?:Customer\s+ID|Account\s+No|Account\s+Holder|Contact\s+No|Email\s+ID|IFS\s+Code)", l.strip(), re.IGNORECASE)]
                    colon_lines = [l.strip() for l in all_candidate_lines if l.strip().startswith(":")]
                    if text.strip() in label_lines and len(colon_lines) > label_lines.index(text.strip()):
                        c_idx = label_lines.index(text.strip())
                        val_line = colon_lines[c_idx]
                        val = re.sub(r"^:\s*", "", val_line).strip()
                        orig_pos = all_candidate_lines.index(val_line)
                        pos = orig_pos + 1
                        while pos < len(all_candidate_lines):
                            nxt = all_candidate_lines[pos].strip()
                            if not nxt or nxt.startswith(":") or any(kw in nxt.lower() for kw in ("contact", "email", "ifs", "branch", "account", "customer")):
                                break
                            if re.match(r"^[A-Za-z\s\.]+$", nxt):
                                val = f"{val} {nxt}".strip()
                            else:
                                break
                            pos += 1
                        holder = val.strip()
                else:
                    # Standard inline name
                    holder = cleaned
                    i = idx + 1
                    while i < len(all_candidate_lines):
                        nl = all_candidate_lines[i].strip()
                        if not nl or re.match(r"^(S/O|D/O|W/O|C/O|Address|Branch|Account|IFSC|Contact|Email|Phone|Mobile|Customer|Date|Status|Nominee|PAN|IFS)", nl, re.IGNORECASE) or nl.startswith((":", "-")):
                            break
                        if re.match(r"^[A-Za-z\s\.]+$", nl):
                            holder = (holder + " " + nl).strip()
                        else:
                            break
                        i += 1
                    holder = re.sub(r"^(?:name\s+)", "", holder, flags=re.IGNORECASE).strip()
                    holder = re.sub(r"\s+(?:S/O|D/O|W/O|C/O)\s+.*$", "", holder, flags=re.IGNORECASE).strip()
                    if re.search(r"NAGAPATTINAM|TAMIL NADU|S/O|\d{6}", holder, flags=re.IGNORECASE):
                        holder = ""

            if holder and not meta["account_holder"]:
                meta["account_holder"] = holder

        if ("account number" in lowered or "account no" in lowered or "a/c no" in lowered or "accountno" in lowered) and not meta["account_no"]:
            match = re.search(r"(?:account\s*no|account\s*number|a\/c\s*no)[\s:]*([0-9X\s\-]{8,25})", text, re.IGNORECASE)
            if match:
                digs = re.search(r"\b[0-9X]{8,20}\b", match.group(1).replace(" ", ""))
                if digs:
                    meta["account_no"] = digs.group(0)
                else:
                    meta["account_no"] = match.group(1).strip()

        if not meta["account_no"]:
            num_m = re.search(r"^:\s*(\d{11,18})\b", text.strip())
            if num_m:
                meta["account_no"] = num_m.group(1)

        if "product:" in lowered or "account type" in lowered or "accounttype" in lowered or "scheme:" in lowered:
            if re.search(r"\bca-|\bca\b|\bcurrent\b", lowered):
                meta["account_type"] = "Current"
            elif re.search(r"\bsb-|\bsb\b|\bsaving", lowered):
                meta["account_type"] = "Savings"
            elif re.search(r"\bod-|\bod\b|\boverdraft\b", lowered):
                meta["account_type"] = "Overdraft"

        if not meta["statement_period"]:
            m_from_to = re.search(r"from\s*:\s*([0-9A-Za-z\-\/\.]+)\s+to\s*:\s*([0-9A-Za-z\-\/\.]+)", text, re.IGNORECASE)
            if m_from_to:
                meta["statement_period"] = f"{m_from_to.group(1).strip()} to {m_from_to.group(2).strip()}"
            elif ("statement period" in lowered or "for the period of" in lowered):
                match = re.search(r"(?:statement\s+(?:for\s+the\s+)?period|for\s+the\s+period\s+of)[\s:]+(.*)$", text, re.IGNORECASE)
                if match:
                    meta["statement_period"] = match.group(1).strip()
            elif ("statement from" in lowered or "from date" in lowered):
                m_from = re.search(r"(?:statement\s+from|from\s+date)[\s:]*([0-9A-Za-z\-\/\.]+)", text, re.IGNORECASE)
                if m_from:
                    from_str = m_from.group(1).strip()
                    to_str = ""
                    m_to = re.search(r"\bto[\s:]*([0-9A-Za-z\-\/\.]+)", text, re.IGNORECASE)
                    if m_to and m_to.group(1).strip().lower() != from_str.lower():
                        to_str = m_to.group(1).strip()
                    else:
                        for next_line in all_candidate_lines[idx+1:idx+4]:
                            m_to2 = re.search(r"\bto[\s:]*([0-9A-Za-z\-\/\.]+)", next_line, re.IGNORECASE)
                            if m_to2 and m_to2.group(1).strip().lower() != from_str.lower():
                                to_str = m_to2.group(1).strip()
                                break
                    if from_str and to_str:
                        meta["statement_period"] = f"{from_str} to {to_str}"
                    elif from_str:
                        meta["statement_period"] = from_str


        if ("opening balance" in lowered or "brought forward" in lowered or "b/f" in lowered) and meta["opening_balance"] is None:
            match = re.search(r"(?:opening\s+balance|brought\s+forward|b\/f)[^\d]*([\d,]+\.?\d*)", text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(",", "")
                try:
                    meta["opening_balance"] = float(val_str)
                except ValueError:
                    pass

        if ("ending balance" in lowered or "closing balance" in lowered or "cleared balance" in lowered) and meta["closing_balance"] is None:
            match = re.search(r"(?:ending|closing|cleared)\s+balance[^\d]*([\d,]+\.?\d*)", text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(",", "")
                try:
                    meta["closing_balance"] = float(val_str)
                except ValueError:
                    pass


        if "statement total" in lowered:
            match = re.search(r"statement\s+total[^\d]*([\d,]+\.?\d*)[^\d]*([\d,]+\.?\d*)", text, re.IGNORECASE)
            if match:
                try:
                    # PDF prints debit first, then credit
                    meta["footer_total_debit"] = float(match.group(1).replace(",", ""))
                    meta["footer_total_credit"] = float(match.group(2).replace(",", ""))
                except ValueError:
                    pass

    # Fallback for label/value separation format: Account Holder Name ... : BAIRAVAPRAKASH \n PUGAZHENDHI
    # Uses word bounding boxes (pdfplumber) to handle text ordering and wrapping.
    word_set = {}
    for line in (p1.header_lines + p1.lines[:25]):
        for w in line.words:
            key = (round(w.x0, 2), round(w.top, 2), w.text)
            word_set[key] = w
    
    words = list(word_set.values())
    
    label_words = [w for w in words if w.x0 < 150]
    from collections import defaultdict
    label_lines_map = defaultdict(list)
    for w in label_words:
        label_lines_map[round(w.top / 3)].append(w)
        
    label_lines = []
    for k in sorted(label_lines_map.keys()):
        line_w = sorted(label_lines_map[k], key=lambda w: w.x0)
        text = ' '.join(w.text for w in line_w)
        label_lines.append({'text': text, 'top': min(w.top for w in line_w)})
        
    valid_labels = [l for l in label_lines if re.search(r'Customer\s+ID|Account\s+No|Account\s+Holder|Contact\s+No|Email\s+ID|IFS\s+Code|Branch\s+Code', l['text'], re.I)]
    
    colons = [w for w in words if w.text.strip() == ':' and 140 < w.x0 < 190]
    colons.sort(key=lambda w: w.top)
    
    for i, l in enumerate(valid_labels):
        if 'account holder' in l['text'].lower() and i < len(colons):
            c_curr = colons[i]
            c_next = colons[i+1] if i+1 < len(colons) else None
            
            top_min = c_curr.top - 2
            top_max = c_next.top - 2 if c_next else c_curr.top + 30
            
            val_words = [w for w in words if w.x0 >= c_curr.x0 - 5 and w.x0 < 250 and top_min <= w.top < top_max and w.text != ':']
            val_words.sort(key=lambda w: (w.top, w.x0))
            
            v = ' '.join(w.text for w in val_words).strip()
            if not meta["account_holder"]:
                if not re.search(r"Account|Holder|Name|Contact|Email|IFS|Branch|NAGAPATTINAM|TAMIL NADU|S/O", v, re.I):
                    meta["account_holder"] = v.strip()
            break

    # Fallback for account holder: Check lines immediately following STATEMENT OF ACCOUNT
    if not meta["account_holder"]:
        p2 = doc.pages[1] if len(doc.pages) > 1 else None
        for p in [p2, p1]:
            if not p:
                continue
            lines = [l.text.strip() for l in (p.header_lines + p.lines[:15])]
            for i, txt in enumerate(lines):
                if re.match(r"^STATEMENT\s+OF\s+ACCOUNT", txt, re.IGNORECASE):
                    if i + 1 < len(lines):
                        cand = lines[i + 1].strip()
                        cand_clean = re.sub(
                            r"\b(INDIAN\s+BANK|STATE\s+BANK\s+OF\s+INDIA|HDFC\s+BANK|ICICI\s+BANK|AXIS\s+BANK|CANARA\s+BANK|IOB|BOB).*",
                            "",
                            cand,
                            flags=re.IGNORECASE,
                        ).strip()
                        if cand_clean and not any(kw in cand_clean.lower() for kw in ["account no", "phone", "email", "ifsc", "date", "product", "limit", "branch code"]):
                            meta["account_holder"] = cand_clean
                            break

    # Fallback: scan for standard personal/business salutations (e.g. MR. GMOHAN -> MR. G MOHAN)
    if not meta["account_holder"] and doc.pages:
        p1 = doc.pages[0]
        cand_lines = [l.text.strip() for l in (p1.header_lines + p1.lines[:20])]
        for txt in cand_lines:
            m_sal = re.match(r"^(?:MR\.?|MRS\.?|MS\.?|DR\.?|M/S\.?)\s*([A-Za-z\s\.]+)", txt, re.IGNORECASE)
            if m_sal and len(m_sal.group(1).strip()) >= 3:
                name = m_sal.group(0).strip()
                name = re.sub(r"\b([A-Z])([A-Z][a-z]+)", r"\1 \2", name)
                name = re.sub(r"\s+(?:PLOT|NO|STREET|NAGAR|ROAD).*$", "", name, flags=re.IGNORECASE).strip()
                # Fix concatenated salutation+name: "MR. GMOHAN" -> "MR. G MOHAN"
                # Pattern: salutation + single letter + rest of name without spaces
                name = re.sub(
                    r"^(MR\.|MRS\.|MS\.|DR\.|M/S\.)\s*([A-Z])([A-Z][A-Z]+)",
                    lambda m: m.group(1) + " " + m.group(2) + " " + m.group(3),
                    name
                )
                meta["account_holder"] = name
                break

    # Also fix concatenated name if already set (e.g. "MR. GMOHAN" -> "MR. G MOHAN")
    if meta["account_holder"]:
        meta["account_holder"] = re.sub(
            r"^(MR\.|MRS\.|MS\.|DR\.|M/S\.)\s*([A-Z])([A-Z]{2,})",
            lambda m: m.group(1) + " " + m.group(2) + " " + m.group(3),
            meta["account_holder"]
        )
    # Scan ALL pages for Closing Balance and Statement Summary (HDFC and other formats)
    _stmt_summary_header_found = False
    _stmt_summary_header_cols = []
    _STMT_HDR_KEYS = [
        "openingbalance", "drcount", "crcount", "debits", "credits", "closingbal"
    ]

    for page in doc.pages:
        page_lines = page.lines
        for li, line in enumerate(page_lines):
            t = line.text.strip()

            # Pattern 1: Inline "Dr. Count: N Cr. Count: N DEBIT CREDIT" style
            m_sum_inline = re.search(
                r"Dr\.?\s*Count\s*:?\s*(\d+)\s+Cr\.?\s*Count\s*:?\s*(\d+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})",
                t, re.I
            )
            if m_sum_inline:
                try:
                    dr_cnt = int(m_sum_inline.group(1))
                    cr_cnt = int(m_sum_inline.group(2))
                    tot_dr = float(m_sum_inline.group(3).replace(",", ""))
                    tot_cr = float(m_sum_inline.group(4).replace(",", ""))
                    meta["statement_summary"] = {
                        "dr_count": dr_cnt, "cr_count": cr_cnt,
                        "total_debit": tot_dr, "total_credit": tot_cr,
                    }
                    meta["footer_total_debit"] = tot_dr
                    meta["footer_total_credit"] = tot_cr
                except ValueError:
                    pass

            # Pattern 2: HDFC-style 2-line summary
            # Header line: "OpeningBalance DrCount CrCount Debits Credits ClosingBal"
            # Value line:  "57,598.70 101 29 561,355.18 653,815.01 150,058.53"
            t_compact = re.sub(r"\s+", "", t).lower()
            if all(k in t_compact for k in _STMT_HDR_KEYS):
                _stmt_summary_header_found = True
                # Detect column order from header
                col_order = []
                for token in re.split(r"\s+", t):
                    tk = token.strip().lower().replace(".", "")
                    if re.fullmatch(r"opening(?:balance)?", tk):
                        col_order.append("opening")
                    elif re.fullmatch(r"drcount|dr\.?count|dr", tk):
                        col_order.append("dr_count")
                    elif re.fullmatch(r"crcount|cr\.?count|cr", tk):
                        col_order.append("cr_count")
                    elif re.fullmatch(r"debits?|withdrawal(?:s)?amt\.?|withdrawals?", tk):
                        col_order.append("total_debit")
                    elif re.fullmatch(r"credits?|deposits?amt\.?|deposits?", tk):
                        col_order.append("total_credit")
                    elif re.fullmatch(r"closing(?:balance|bal)?|closingbal", tk):
                        col_order.append("closing")
                _stmt_summary_header_cols = col_order
                continue

            if _stmt_summary_header_found and not _stmt_summary_header_cols:
                _stmt_summary_header_found = False

            if _stmt_summary_header_found and _stmt_summary_header_cols:
                # Grab the value row - should be all numbers/commas/dots with spaces
                vals = re.findall(r"[\d,]+\.\d{2}|\d+", t)
                if len(vals) >= 3:
                    mapping = {}
                    for i, col in enumerate(_stmt_summary_header_cols):
                        if i < len(vals):
                            try:
                                mapping[col] = float(vals[i].replace(",", ""))
                            except ValueError:
                                pass
                    if mapping:
                        if not meta.get("opening_balance") and "opening" in mapping:
                            meta["opening_balance"] = mapping["opening"]
                        if not meta.get("closing_balance") and "closing" in mapping:
                            meta["closing_balance"] = mapping["closing"]
                        if meta.get("statement_summary") is None:
                            stmt_sum = {}
                            if "dr_count" in mapping:
                                stmt_sum["dr_count"] = int(mapping["dr_count"])
                            if "cr_count" in mapping:
                                stmt_sum["cr_count"] = int(mapping["cr_count"])
                            if "total_debit" in mapping:
                                stmt_sum["total_debit"] = mapping["total_debit"]
                                meta["footer_total_debit"] = mapping["total_debit"]
                            if "total_credit" in mapping:
                                stmt_sum["total_credit"] = mapping["total_credit"]
                                meta["footer_total_credit"] = mapping["total_credit"]
                            if stmt_sum:
                                meta["statement_summary"] = stmt_sum
                _stmt_summary_header_found = False
                _stmt_summary_header_cols = []

            # Pattern 3: CLOSING BALANCE label in any line
            m_cb = re.search(r"CLOSING\s+BALANCE\s*[:\s]+([\d,]+\.\d{2})", t, re.I)
            if m_cb and not meta.get("closing_balance"):
                try:
                    meta["closing_balance"] = float(m_cb.group(1).replace(",", ""))
                except ValueError:
                    pass

    # Ensure Opening Balance is extracted from the FIRST Brought Forward line if not yet found
    if meta.get("opening_balance") is None and doc.pages:
        bf_pat = re.compile(r"Brought\s+Forward\s+([0-9,]+\.[0-9]{2})(Cr|Dr)?", re.I)
        for p in doc.pages:
            for l in p.lines:
                m_bf = bf_pat.search(l.text)
                if m_bf:
                    try:
                        meta["opening_balance"] = float(m_bf.group(1).replace(",", ""))
                        break
                    except ValueError:
                        pass
            if meta.get("opening_balance") is not None:
                break

    return meta


