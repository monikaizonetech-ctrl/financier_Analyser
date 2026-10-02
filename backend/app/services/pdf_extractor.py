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
    for word in sorted_words:
        # Filter out empty or whitespace words
        t = word.get("text", "").strip()
        if not t:
            continue

        placed = False
        w_top = word["top"]
        w_bottom = word["bottom"]
        w_mid = (w_top + w_bottom) / 2.0

        for line_group in lines_raw:
            # Check if word aligns vertically with this line's average position
            avg_top = sum(w["top"] for w in line_group) / len(line_group)
            avg_bottom = sum(w["bottom"] for w in line_group) / len(line_group)
            avg_mid = (avg_top + avg_bottom) / 2.0

            # Tolerant vertical overlap check
            if abs(w_mid - avg_mid) <= y_tolerance or (w_top >= avg_top - y_tolerance and w_bottom <= avg_bottom + y_tolerance):
                line_group.append(word)
                placed = True
                break

        if not placed:
            lines_raw.append([word])

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


def extract_pdf_document(file_path: str, max_pages: int | None = None) -> ExtractedDocument:
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

    if pdfplumber is None:
        doc.is_valid = False
        doc.error_message = "pdfplumber is not installed on the server"
        return doc

    try:
        with pdfplumber.open(file_path) as pdf:
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
                p_width = float(page.width)
                p_height = float(page.height)

                raw_page_text = page.extract_text() or ""
                debug_text_chunks.append(f"--- PAGE {page_num} ---\n{raw_page_text}")
                char_count = len(raw_page_text.strip())
                total_chars += char_count

                # Extract positioned words
                words = page.extract_words(
                    x_tolerance=3,
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

    for text in all_candidate_lines:
        lowered = text.lower()
        if ("account holder" in lowered or "customer name" in lowered) and not meta["account_holder"]:
            match = re.search(r"(?:account\s+holder(?:\s+name)?|customer\s+name)[\s:]+([A-Za-z\s\.]+)", text, re.IGNORECASE)
            if match:
                holder = match.group(1).strip()
                holder = re.sub(r"^(?:name\s+)", "", holder, flags=re.I).strip()
                if holder:
                    meta["account_holder"] = holder

        if "account number" in lowered or "account no" in lowered or "a/c no" in lowered:
            match = re.search(r"(?:account\s+(?:number|no)|a\/c\s+no)[\s:]+([0-9X\s\-]+)", text, re.IGNORECASE)
            if match and len(match.group(1).strip()) >= 6:
                meta["account_no"] = match.group(1).strip()

        if not meta["account_no"]:
            num_m = re.search(r"^:\s*(\d{11,18})\b", text.strip())
            if num_m:
                meta["account_no"] = num_m.group(1)

        if "account type" in lowered:
            if "current" in lowered:
                meta["account_type"] = "Current"
            elif "savings" in lowered:
                meta["account_type"] = "Savings"
            elif "overdraft" in lowered or "od" in lowered:
                meta["account_type"] = "Overdraft"

        if ("statement period" in lowered or "for the period of" in lowered) and not meta["statement_period"]:
            match = re.search(r"(?:statement\s+(?:for\s+the\s+)?period|for\s+the\s+period\s+of)[\s:]+(.*)$", text, re.IGNORECASE)
            if match:
                meta["statement_period"] = match.group(1).strip()

        if "opening balance" in lowered and meta["opening_balance"] is None:
            match = re.search(r"opening\s+balance[^\d]*([\d,]+\.?\d*)", text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(",", "")
                try:
                    meta["opening_balance"] = float(val_str)
                except ValueError:
                    pass

        if ("ending balance" in lowered or "closing balance" in lowered) and meta["closing_balance"] is None:
            match = re.search(r"(?:ending|closing)\s+balance[^\d]*([\d,]+\.?\d*)", text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(",", "")
                try:
                    meta["closing_balance"] = float(val_str)
                except ValueError:
                    pass

    return meta


