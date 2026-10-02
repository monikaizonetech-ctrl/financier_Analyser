"""
Intelligent transaction extraction engine for bank statements.

Reconstructs canonical transaction records from extracted PDF content
(both structured tables and spatial text lines) independent of column order,
fixed coordinates, or bank-specific layouts.

Supports:
- 1-line and multi-line transactions (wrapped narrations and delayed amounts)
- Dynamic column ordering (e.g. Credit before Debit, Value Date vs Txn Date)
- Single Amount column with Dr/Cr or +/- indicator
- Strict number disambiguation (distinguishes amounts from account numbers,
  phone numbers, reference IDs, and dates)
- Filtering of repeated headers, sub-totals, and summary lines
- Preservation of raw text and source page for full auditability
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import re
from typing import Any

from app.services.pdf_extractor import (
    ExtractedDocument,
    ExtractedPage,
    ExtractedLine,
    ExtractedWord,
    LineType,
)


class ColumnRole(str, Enum):
    DATE = "DATE"
    VALUE_DATE = "VALUE_DATE"
    DESCRIPTION = "DESCRIPTION"
    REFERENCE = "REFERENCE"
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    BALANCE = "BALANCE"
    AMOUNT = "AMOUNT"
    TXN_TYPE = "TXN_TYPE"
    TRANSACTION_ID = "TRANSACTION_ID"
    SERIAL_NO = "SERIAL_NO"
    UNKNOWN = "UNKNOWN"


class TransactionType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class ColumnDef:
    role: ColumnRole
    header_name: str
    x0: float = 0.0
    x1: float = 0.0
    col_idx: int = -1


@dataclass
class CanonicalTransaction:
    date: date
    description: str
    reference: str = ""
    debit: float = 0.0
    credit: float = 0.0
    balance: float | None = None
    transaction_type: TransactionType = TransactionType.UNCERTAIN
    source_page: int = 1
    raw_text: str = ""
    is_uncertain: bool = False
    uncertain_reason: str = ""
    extra_metadata: dict[str, Any] = field(default_factory=dict)
    transaction_id: str = ""
    value_date: str = ""
    direction: str = ""
    serial_no: int | None = None

    def to_dict(self, file_name: str = "", meta: dict | None = None) -> dict:
        t_type = (
            self.transaction_type.value
            if isinstance(self.transaction_type, TransactionType)
            else str(self.transaction_type)
        )
        dir_val = self.direction or ("CR" if (self.credit or 0) > 0 else ("DR" if (self.debit or 0) > 0 else ""))
        v_date_str = self.value_date or (self.date.strftime("%d/%m/%Y") if self.date else "")
        data = {
            "transaction_id": self.transaction_id,
            "value_date": v_date_str,
            "date": self.date,
            "description": self.description.strip() or "Transaction",
            "reference": self.reference.strip() or self.transaction_id,
            "chq_no": self.reference.strip(),
            "direction": dir_val,
            "credit": round(self.credit, 2) if self.credit and self.credit > 0 else (0.0 if dir_val == "CR" else None),
            "debit": round(self.debit, 2) if self.debit and self.debit > 0 else (0.0 if dir_val == "DR" else None),
            "balance": round(self.balance, 2) if self.balance is not None else None,
            "transaction_type": t_type,
            "source_page": self.source_page,
            "raw_text": self.raw_text.strip(),
            "is_uncertain": self.is_uncertain,
            "uncertain_reason": self.uncertain_reason,
            "file_name": file_name,
        }
        if self.serial_no is not None:
            data["sno"] = self.serial_no
        if meta:
            data.update(meta)
        return data


def classify_transaction_direction(
    debit: float,
    credit: float,
    current_balance: float | None = None,
    previous_balance: float | None = None,
    indicator: str | None = None,
) -> tuple[TransactionType, float, float, bool, str]:
    """
    Classify transaction direction strictly using financial indicators:
    Credit / Deposit / CR / +  -> INCOME
    Debit / Withdrawal / DR / - -> EXPENSE

    Never relies on narration keywords to guess direction.
    Returns: (transaction_type, resolved_debit, resolved_credit, is_uncertain, reason)
    """
    resolved_debit = round(float(debit or 0.0), 2)
    resolved_credit = round(float(credit or 0.0), 2)

    # 1. Explicit Indicator check (CR / DR / +/-) takes highest priority
    if indicator:
        ind = indicator.upper().strip()
        amt = resolved_credit or resolved_debit
        if ind in ("CR", "C", "+") and amt > 0:
            return TransactionType.INCOME, 0.0, amt, False, ""
        elif ind in ("DR", "D", "-") and amt > 0:
            return TransactionType.EXPENSE, amt, 0.0, False, ""

    # 2. Unambiguous Credit / Income
    if resolved_credit > 0 and resolved_debit == 0:
        return TransactionType.INCOME, 0.0, resolved_credit, False, ""

    # 3. Unambiguous Debit / Expense
    if resolved_debit > 0 and resolved_credit == 0:
        return TransactionType.EXPENSE, resolved_debit, 0.0, False, ""

    # 4. Check Balance Delta if debit and credit are both zero
    if resolved_debit == 0 and resolved_credit == 0:
        if current_balance is not None and previous_balance is not None:
            delta = round(current_balance - previous_balance, 2)
            if delta > 0:
                return TransactionType.INCOME, 0.0, delta, False, "Derived from balance increase"
            elif delta < 0:
                return TransactionType.EXPENSE, abs(delta), 0.0, False, "Derived from balance decrease"
        if previous_balance is None and current_balance is not None:
            return TransactionType.UNCERTAIN, 0.0, 0.0, False, "Opening balance anchor"
        return TransactionType.UNCERTAIN, 0.0, 0.0, True, "Zero debit and credit amounts without balance movement"

    # 5. Ambiguous: both debit > 0 and credit > 0
    if resolved_debit > 0 and resolved_credit > 0:
        if current_balance is not None and previous_balance is not None:
            delta = round(current_balance - previous_balance, 2)
            if abs(delta - resolved_credit) < 0.05:
                return TransactionType.INCOME, 0.0, resolved_credit, False, "Resolved via balance delta matching credit"
            elif abs(abs(delta) - resolved_debit) < 0.05:
                return TransactionType.EXPENSE, resolved_debit, 0.0, False, "Resolved via balance delta matching debit"
        return TransactionType.UNCERTAIN, resolved_debit, resolved_credit, True, "Both debit and credit fields have positive amounts"

    return TransactionType.UNCERTAIN, resolved_debit, resolved_credit, True, "Direction cannot be reliably determined"




# --------------------------------------------------------------------------
# Date and Amount parsing helpers
# --------------------------------------------------------------------------
_DATE_PATTERNS = [
    r"^\s*(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b",           # 01-07-2026, 01/07/2026
    r"^\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\b",               # 01.07.2026
    r"^\s*(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b",           # 2026-07-01
    r"^\s*(\d{1,2})[-/\s]([A-Za-z]{3})[-/\s](\d{4})\b",   # 01-Jul-2026, 01 Jul 2026
    r"^\s*(\d{1,2})[-/\s]([A-Za-z]{3})[-/\s](\d{2})\b",     # 01-Jul-26
    r"^\s*(\d{1,2})[-/](\d{1,2})[-/](\d{2})\b",             # 01/07/26
]

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}


def parse_date(val: Any) -> date | None:
    """Parse date from string or datetime object with support for multiple formats."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "-", ""):
        return None

    # Check regex patterns
    # DD-MM-YYYY or DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(y, mo, d)
        except ValueError:
            pass

    # DD.MM.YYYY
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(y, mo, d)
        except ValueError:
            pass

    # YYYY-MM-DD
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(y, mo, d)
        except ValueError:
            pass

    # DD-Mon-YYYY or DD Mon YYYY
    m = re.match(r"^(\d{1,2})[-/\s]([A-Za-z]{3})[-/\s](\d{4})", s)
    if m:
        try:
            d, mon_str, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
            mo = _MONTH_MAP.get(mon_str[:3])
            if mo:
                return date(y, mo, d)
        except ValueError:
            pass

    # DD-Mon-YY or DD Mon YY
    m = re.match(r"^(\d{1,2})[-/\s]([A-Za-z]{3})[-/\s](\d{2})\b", s)
    if m:
        try:
            d, mon_str, yy = int(m.group(1)), m.group(2).lower(), int(m.group(3))
            y = 2000 + yy if yy < 70 else 1900 + yy
            mo = _MONTH_MAP.get(mon_str[:3])
            if mo:
                return date(y, mo, d)
        except ValueError:
            pass

    # Fallback standard formats
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            continue

    return None


def extract_direction_and_amount(val: Any, type_val: Any = None) -> tuple[float, str | None]:
    """
    Extract numeric amount and direction (CR / DR) with strict support for:
    - Attached CR/DR without whitespace: e.g. ICICIBankSBDR 10,000.00, SBDR 10,000.00, CADR 35,000.00
    - Explicit tokens: CR 3,00,000.00, DR 40,808.00
    - Cr/Dr column indicator: CR, DR, SBDR, CADR, etc.
    Returns: (numeric_amount, direction_indicator)
    The parser identifies the direction before extracting the amount.
    """
    if val is None and type_val is None:
        return 0.0, None

    s = str(val or "").strip()
    t = str(type_val or "").strip().upper()
    indicator = None

    # 1. Attached CR / DR before amount, without requiring whitespace before CR/DR
    # Matches: CR 3,00,000.00, DR 40,808.00, SBDR 10,000.00, CADR 35,000.00, ICICIBankSBDR 10,000.00
    m_attached = re.search(
        r"(?:[A-Za-z0-9_]*?)(CR|DR)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})|[0-9]+(?:\.[0-9]{2}))",
        s,
        re.IGNORECASE,
    )
    if m_attached:
        indicator = m_attached.group(1).upper()
        amt_str = m_attached.group(2).replace(",", "").strip()
        try:
            return round(float(amt_str), 2), indicator
        except (ValueError, TypeError):
            pass

    # 2. Check direction in type string / cell
    if t:
        m_t = re.search(r"(?:SB|CA)?(CR|DR)", t)
        if m_t:
            indicator = m_t.group(1).upper()
        elif t in ("C", "+"):
            indicator = "CR"
        elif t in ("D", "-"):
            indicator = "DR"

    amt, ind_val = clean_amount_str(s)
    if not indicator and ind_val:
        indicator = ind_val

    return amt, indicator


def clean_amount_str(val: Any) -> tuple[float, str | None]:
    """
    Parse monetary amount from string, handling currency symbols, commas,
    negative parentheses (1,200.00), and trailing or attached Dr/Cr flags.
    Returns: (numeric_amount, dr_cr_indicator)
    """
    if val is None:
        return 0.0, None
    if isinstance(val, (int, float)):
        return round(float(val), 2), None

    s = str(val).strip()
    if not s or s in ("-", "--", "---", "----", "NA", "null", "None", "nil"):
        return 0.0, None

    # Detect Dr / Cr indicator (including attached SBDR, CADR, etc.)
    indicator = None
    lowered = s.lower()
    if re.search(r"(?:sb|ca)?dr\b|\((?:sb|ca)?dr\)", lowered) or re.search(r"[a-z0-9_]*dr\s*\d", lowered):
        indicator = "DR"
    elif re.search(r"(?:sb|ca)?cr\b|\((?:sb|ca)?cr\)", lowered) or re.search(r"[a-z0-9_]*cr\s*\d", lowered):
        indicator = "CR"

    # Detect negative accounting parentheses: (1,250.00)
    if s.startswith("(") and s.endswith(")"):
        indicator = "DR"
        s = s[1:-1].strip()

    # Remove currency symbols, commas, trailing indicators
    s = re.sub(r"[₹$€£]|INR|Rs\.?|(?:SB|CA)?\bdr\b|(?:SB|CA)?\bcr\b|\((?:dr|cr)\)", "", s, flags=re.IGNORECASE).strip()
    if s.startswith("-"):
        if indicator is None:
            indicator = "DR"
        s = s[1:].strip()
    elif s.startswith("+"):
        if indicator is None:
            indicator = "CR"
        s = s[1:].strip()

    # If attached prefix like ICICIBankSBDR remains, extract the numeric portion
    digit_m = re.search(r"([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})|[0-9]+(?:\.[0-9]{2}))", s)
    if digit_m:
        s = digit_m.group(1)

    s = s.replace(",", "").strip()

    # Disambiguate: if it looks like an account number, phone number, or date, reject
    if re.match(r"^\d{10,}$", s) and "." not in s:
        # Long sequence of 10+ digits without decimal is likely phone / account / reference
        return 0.0, None

    try:
        amt = round(float(s), 2)
        if amt < 0:
            if indicator is None:
                indicator = "DR"
            amt = abs(amt)
        return amt, indicator
    except (ValueError, TypeError):
        return 0.0, None


def _is_summary_or_noise_line(text: str) -> bool:
    """Detect if a row/line is a subtotal, summary, or running header."""
    lowered = text.lower().strip()
    patterns = [
        r"^total\b",
        r"\bpage\s+total\b",
        r"\bgrand\s+total\b",
        r"\bbrought\s+forward\b",
        r"\bcarried\s+forward\b",
        r"\bb\/f\b",
        r"\bc\/f\b",
        r"\bstatement\s+summary\b",
        r"\bclosing\s+balance\b\s*$",
        r"\bend\s+of\s+statement\b",
        r"^page\s+\d+\s+of\s+\d+",
    ]
    return any(re.search(p, lowered) for p in patterns)


# --------------------------------------------------------------------------
# Semantic Header Role Identifier
# --------------------------------------------------------------------------
def identify_column_roles(header_row: list[str]) -> dict[ColumnRole, int]:
    """
    Given a list of column header strings, determine the 0-indexed column
    position for each semantic role using word-boundary matching.
    """
    mapping: dict[ColumnRole, int] = {}
    used_indices: set[int] = set()

    normalized = [str(c).lower().replace("\n", " ").strip() if c else "" for c in header_row]

    # 0. Serial Number & Transaction ID
    for i, h in enumerate(normalized):
        if re.search(r"^(?:no\.?|sl\.?\s*no\.?|sr\.?\s*no\.?|s\.?\s*no\.?)$", h) and ColumnRole.SERIAL_NO not in mapping:
            mapping[ColumnRole.SERIAL_NO] = i
            used_indices.add(i)
            break

    for i, h in enumerate(normalized):
        if i not in used_indices and re.search(r"\b(?:transactio\s*n\s*id|transaction\s*id|txn\s*id)\b", h) and ColumnRole.TRANSACTION_ID not in mapping:
            mapping[ColumnRole.TRANSACTION_ID] = i
            used_indices.add(i)
            break

    # 1. Date & Value Date
    for i, h in enumerate(normalized):
        if i not in used_indices and re.search(r"\bvalue\s+date\b", h) and ColumnRole.VALUE_DATE not in mapping:
            mapping[ColumnRole.VALUE_DATE] = i
            used_indices.add(i)
            break

    for i, h in enumerate(normalized):
        if i not in used_indices and re.search(r"\b(?:txn\s+posted\s+date|txn\s+date|trans\s+date|posting\s+date|date)\b", h):
            mapping[ColumnRole.DATE] = i
            used_indices.add(i)
            break

    # 2. Reference ID / Chq No
    for i, h in enumerate(normalized):
        if i not in used_indices and re.search(r"\b(?:reference|chq|cheque|ref\s*no|ref|utr|instrument)\b", h):
            mapping[ColumnRole.REFERENCE] = i
            used_indices.add(i)
            break

    # 3. Description / Narration / Particulars
    for i, h in enumerate(normalized):
        if i not in used_indices and re.search(r"\b(?:narration|description|particulars|details|remarks|transaction\s+details)\b", h):
            mapping[ColumnRole.DESCRIPTION] = i
            used_indices.add(i)
            break

    # 4. Txn Type / Dr-Cr indicator column (CHECK BEFORE Debit/Credit to avoid matching Cr/Dr as Debit)
    for i, h in enumerate(normalized):
        if i not in used_indices and re.search(r"\b(?:type|cr\s*/\s*dr|dr\s*/\s*cr|cr\s*dr|dr\s*cr|d\s*/\s*c)\b", h):
            mapping[ColumnRole.TXN_TYPE] = i
            used_indices.add(i)
            break

    # 5. Debit (Withdrawal / Dr)
    for i, h in enumerate(normalized):
        if i not in used_indices:
            if re.search(r"\b(?:withdrawal|withdrawals|debit|debits)\b", h) or (re.search(r"\bdr\b", h) and "/" not in h):
                mapping[ColumnRole.DEBIT] = i
                used_indices.add(i)
                break

    # 6. Credit (Deposit / Cr)
    for i, h in enumerate(normalized):
        if i not in used_indices:
            if re.search(r"\b(?:deposit|deposits|credit|credits)\b", h) or (re.search(r"\bcr\b", h) and "/" not in h):
                mapping[ColumnRole.CREDIT] = i
                used_indices.add(i)
                break

    # 7. Balance
    for i, h in enumerate(normalized):
        if i not in used_indices and re.search(r"\b(?:available\s+balance|balance|closing\s+balance|running\s+balance|bal)\b", h):
            mapping[ColumnRole.BALANCE] = i
            used_indices.add(i)
            break

    # 8. Single Amount column
    for i, h in enumerate(normalized):
        if i not in used_indices and re.search(r"\b(?:transaction\s+amount|txn\s+amount|amount)\b", h):
            mapping[ColumnRole.AMOUNT] = i
            used_indices.add(i)
            break

    # Fallback: if description not found, pick the first available unmapped column
    if ColumnRole.DESCRIPTION not in mapping:
        for i, h in enumerate(normalized):
            if i not in used_indices:
                mapping[ColumnRole.DESCRIPTION] = i
                used_indices.add(i)
                break

    # If VALUE_DATE was identified but no DATE column, VALUE_DATE serves as DATE
    if ColumnRole.DATE not in mapping and ColumnRole.VALUE_DATE in mapping:
        mapping[ColumnRole.DATE] = mapping[ColumnRole.VALUE_DATE]

    return mapping


# --------------------------------------------------------------------------
# Strategy A: Table-Based Extraction (Structured / Semi-Structured Tables)
# --------------------------------------------------------------------------
def parse_table_transactions(
    table: list[list[str | None]],
    page_num: int,
    file_name: str,
    meta: dict | None = None,
    fallback_col_mapping: dict[ColumnRole, int] | None = None,
    out_col_mapping: list[dict[ColumnRole, int]] | None = None,
) -> list[CanonicalTransaction]:
    """
    Intelligently extracts transactions from a 2D table grid.
    Handles multi-line continuation rows, arbitrary column order, and
    single-amount Dr/Cr columns. Inherits column definitions across continuation pages.
    Anchors transactions using Transaction ID or serial numbers as boundaries.
    """
    if not table or len(table) < 1:
        return []

    # Filter out empty rows (where all cells are None or blank)
    cleaned_table = [r for r in table if any(c is not None and str(c).strip() != "" for c in r)]
    if not cleaned_table:
        return []

    # Find the header row
    header_idx = -1
    col_mapping: dict[ColumnRole, int] = {}
    for r_idx in range(min(5, len(cleaned_table))):
        row = cleaned_table[r_idx]
        mapping = identify_column_roles([str(c or "").replace("\n", " ") for c in row])
        has_date = (ColumnRole.DATE in mapping or ColumnRole.VALUE_DATE in mapping)
        has_amt = (
            ColumnRole.DEBIT in mapping
            or ColumnRole.CREDIT in mapping
            or ColumnRole.AMOUNT in mapping
            or ColumnRole.BALANCE in mapping
        )
        if (has_date and has_amt) or (ColumnRole.TRANSACTION_ID in mapping and (has_amt or ColumnRole.BALANCE in mapping)):
            header_idx = r_idx
            if ColumnRole.DATE not in mapping and ColumnRole.VALUE_DATE in mapping:
                mapping[ColumnRole.DATE] = mapping[ColumnRole.VALUE_DATE]
            col_mapping = mapping
            if out_col_mapping is not None:
                out_col_mapping.clear()
                out_col_mapping.append(col_mapping)
            break

    if header_idx == -1:
        if fallback_col_mapping and len(cleaned_table) > 0:
            col_mapping = fallback_col_mapping
            header_idx = -1
        else:
            return []

    tid_col = col_mapping.get(ColumnRole.TRANSACTION_ID)
    sno_col = col_mapping.get(ColumnRole.SERIAL_NO)
    date_col = col_mapping.get(ColumnRole.DATE)
    val_date_col = col_mapping.get(ColumnRole.VALUE_DATE)
    desc_col = col_mapping.get(ColumnRole.DESCRIPTION)
    ref_col = col_mapping.get(ColumnRole.REFERENCE)
    debit_col = col_mapping.get(ColumnRole.DEBIT)
    credit_col = col_mapping.get(ColumnRole.CREDIT)
    bal_col = col_mapping.get(ColumnRole.BALANCE)
    amt_col = col_mapping.get(ColumnRole.AMOUNT)
    type_col = col_mapping.get(ColumnRole.TXN_TYPE)

    txns: list[CanonicalTransaction] = []
    current_txn: CanonicalTransaction | None = None

    for row_idx in range(header_idx + 1, len(cleaned_table)):
        row = cleaned_table[row_idx]
        if not row:
            continue

        raw_row_text = " | ".join(str(c).strip() for c in row if c is not None and str(c).strip())
        if not raw_row_text or _is_summary_or_noise_line(raw_row_text):
            continue

        # Check for anchor tokens on this row
        raw_tid = str(row[tid_col]).strip() if tid_col is not None and tid_col < len(row) and row[tid_col] else ""
        raw_sno = str(row[sno_col]).strip() if sno_col is not None and sno_col < len(row) and row[sno_col] else ""
        raw_date_cell = str(row[date_col]).strip() if date_col is not None and date_col < len(row) and row[date_col] else ""
        raw_val_date_cell = str(row[val_date_col]).strip() if val_date_col is not None and val_date_col < len(row) and row[val_date_col] else ""

        d = parse_date(raw_date_cell) or parse_date(raw_val_date_cell)

        # Detect transaction boundary:
        # A transaction boundary is identified by:
        # 1. Transaction ID present (e.g. S10070637)
        # 2. Numbered transaction row (e.g. 1, 2, ... 660)
        # 3. Date present
        is_new_txn = False
        if raw_tid and re.search(r"^[A-Za-z0-9_-]{4,}$", raw_tid) and not raw_tid.lower().startswith("total"):
            is_new_txn = True
        elif raw_sno.isdigit():
            is_new_txn = True
        elif d is not None:
            is_new_txn = True

        if is_new_txn:
            # Anchor found: EXACTLY ONE CANONICAL TRANSACTION
            desc = str(row[desc_col]).strip() if desc_col is not None and desc_col < len(row) and row[desc_col] else ""
            if desc.lower() in ("nan", "none"):
                desc = ""
            ref = str(row[ref_col]).strip() if ref_col is not None and ref_col < len(row) and row[ref_col] else ""
            if ref.lower() in ("nan", "none"):
                ref = ""

            debit_val = 0.0
            credit_val = 0.0
            indicator_found = None

            if debit_col is not None and credit_col is not None and (debit_col < len(row) or credit_col < len(row)):
                debit_val, debit_ind = clean_amount_str(row[debit_col]) if debit_col < len(row) else (0.0, None)
                credit_val, credit_ind = clean_amount_str(row[credit_col]) if credit_col < len(row) else (0.0, None)
                indicator_found = debit_ind or credit_ind
            elif amt_col is not None and amt_col < len(row):
                amt_cell = row[amt_col]
                type_cell = row[type_col] if type_col is not None and type_col < len(row) else ""
                parsed_amt, parsed_dir = extract_direction_and_amount(amt_cell, type_cell)
                if parsed_dir == "CR":
                    credit_val = parsed_amt
                    indicator_found = "CR"
                elif parsed_dir == "DR":
                    debit_val = parsed_amt
                    indicator_found = "DR"
                else:
                    indicator_found = parsed_dir
                    credit_val = parsed_amt

            bal_raw = str(row[bal_col]).replace(",", "").strip() if bal_col is not None and bal_col < len(row) and row[bal_col] else ""
            bal_val = None
            if bal_raw and bal_raw not in ("-", "--", "", "nan", "none"):
                try:
                    bal_val = float(bal_raw)
                except (ValueError, TypeError):
                    bal_val, _ = clean_amount_str(bal_raw)

            sno_val = int(raw_sno) if raw_sno.isdigit() else None
            val_date_str = raw_val_date_cell or (d.strftime("%d/%m/%Y") if d else "")

            new_txn = CanonicalTransaction(
                date=d or date.today(),
                description=desc,
                reference=ref or raw_tid,
                debit=debit_val,
                credit=credit_val,
                balance=bal_val,
                source_page=page_num,
                raw_text=raw_row_text,
                transaction_id=raw_tid,
                value_date=val_date_str,
                direction=indicator_found or ("CR" if credit_val > 0 else ("DR" if debit_val > 0 else "")),
                serial_no=sno_val,
                extra_metadata={"indicator": indicator_found} if indicator_found else {},
            )
            txns.append(new_txn)
            current_txn = new_txn
        else:
            # Continuation row: append multiline description
            if not any(ch.isalpha() for ch in raw_row_text) and not any(ch.isdigit() for ch in raw_row_text):
                continue
            if current_txn is not None:
                continuation_text = str(row[desc_col]).strip() if desc_col is not None and desc_col < len(row) and row[desc_col] else ""
                if continuation_text and continuation_text.lower() not in ("nan", "none", "-"):
                    current_txn.description = f"{current_txn.description} {continuation_text}".strip()

                if not current_txn.reference and ref_col is not None and ref_col < len(row) and row[ref_col]:
                    r_val = str(row[ref_col]).strip()
                    if r_val.lower() not in ("nan", "none", "-"):
                        current_txn.reference = r_val

                # Check for delayed debit/credit on continuation row if current_txn has 0 amounts
                if current_txn.debit == 0.0 and current_txn.credit == 0.0:
                    if debit_col is not None and credit_col is not None:
                        c_dr, c_dr_ind = clean_amount_str(row[debit_col]) if debit_col < len(row) else (0.0, None)
                        c_cr, c_cr_ind = clean_amount_str(row[credit_col]) if credit_col < len(row) else (0.0, None)
                        if c_dr > 0 or c_cr > 0:
                            current_txn.debit = c_dr
                            current_txn.credit = c_cr
                            if c_dr_ind or c_cr_ind:
                                current_txn.direction = c_dr_ind or c_cr_ind
                    elif amt_col is not None and amt_col < len(row):
                        amt_cell = row[amt_col]
                        type_cell = row[type_col] if type_col is not None and type_col < len(row) else ""
                        p_amt, p_dir = extract_direction_and_amount(amt_cell, type_cell)
                        if p_dir == "CR":
                            current_txn.credit = p_amt
                            current_txn.direction = "CR"
                        elif p_dir == "DR":
                            current_txn.debit = p_amt
                            current_txn.direction = "DR"
                        elif p_amt > 0:
                            current_txn.debit = p_amt

                if (current_txn.balance is None or current_txn.balance == 0.0) and bal_col is not None and bal_col < len(row):
                    b_val = str(row[bal_col]).replace(",", "").strip() if row[bal_col] else ""
                    if b_val and b_val not in ("-", "--", ""):
                        try:
                            current_txn.balance = float(b_val)
                        except (ValueError, TypeError):
                            b_amt, _ = clean_amount_str(b_val)
                            if b_amt:
                                current_txn.balance = b_amt

                current_txn.raw_text = f"{current_txn.raw_text}\n{raw_row_text}"

    # Classify direction across all extracted table transactions
    prev_balance = None
    for txn in txns:
        ind = txn.direction or txn.extra_metadata.get("indicator")
        t_type, resolved_dr, resolved_cr, is_unc, reason = classify_transaction_direction(
            debit=txn.debit,
            credit=txn.credit,
            current_balance=txn.balance,
            previous_balance=prev_balance,
            indicator=ind,
        )
        txn.transaction_type = t_type
        if txn.direction == "CR":
            txn.credit = resolved_cr or txn.credit or resolved_dr
            txn.debit = 0.0
            txn.transaction_type = TransactionType.INCOME
        elif txn.direction == "DR":
            txn.debit = resolved_dr or txn.debit or resolved_cr
            txn.credit = 0.0
            txn.transaction_type = TransactionType.EXPENSE
        else:
            txn.debit = resolved_dr
            txn.credit = resolved_cr

        if is_unc and not txn.is_uncertain:
            txn.is_uncertain = is_unc
            txn.uncertain_reason = reason
        if txn.balance is not None:
            prev_balance = txn.balance

    return txns

    return txns


# --------------------------------------------------------------------------
# Strategy B: Spatial / Line-Based Extraction (Borderless Statements)
# --------------------------------------------------------------------------
_PLACEHOLDER_WORDS = {"-", "--", "---", "----", "nil", "none", "na", "null"}
_CURRENCY_CODES_AND_SYMBOLS = {"inr", "rs", "rs.", "₹", "usd", "eur", "gbp", "$", "€", "£"}


def _starts_with_date(text: str) -> bool:
    return bool(re.search(r"^\s*(?:\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}[-/\.][A-Za-z]{3}[-/\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4})", text))


def _is_amount_or_placeholder(word_text: str) -> bool:
    t = word_text.strip()
    if not t:
        return False
    low = t.lower()
    if low in _PLACEHOLDER_WORDS or low in _CURRENCY_CODES_AND_SYMBOLS:
        return True
    clean_t = re.sub(r"[₹$€£,]", "", t).strip()
    clean_t = re.sub(r"(?i)\b(?:cr|dr|inr|rs)\b|\((?:cr|dr)\)", "", clean_t).strip()
    if clean_t.startswith("-") or clean_t.startswith("+"):
        clean_t = clean_t[1:].strip()
    if not clean_t:
        return False
    try:
        float(clean_t)
        return True
    except ValueError:
        return False


def extract_header_columns(header_line: ExtractedLine) -> list[ColumnDef]:
    """
    Cluster adjacent words in a column header line into semantic column definitions
    with exact horizontal spans [x0, x1].
    """
    if not header_line.words:
        return []

    sorted_words = sorted(header_line.words, key=lambda w: w.x0)
    clusters: list[list[ExtractedWord]] = []
    curr: list[ExtractedWord] = [sorted_words[0]]

    for w in sorted_words[1:]:
        if w.x0 - curr[-1].x1 <= 20.0:
            curr.append(w)
        else:
            clusters.append(curr)
            curr = [w]
    clusters.append(curr)

    col_defs: list[ColumnDef] = []
    used_roles: set[ColumnRole] = set()

    for idx, c in enumerate(clusters):
        phrase = " ".join(w.text for w in c).strip()
        lowered = phrase.lower()
        role = ColumnRole.UNKNOWN

        if ColumnRole.VALUE_DATE not in used_roles and re.search(r"\bvalue\s+date\b", lowered):
            role = ColumnRole.VALUE_DATE
        elif ColumnRole.DATE not in used_roles and re.search(r"\b(?:txn\s+date|trans\s+date|posting\s+date|date)\b", lowered):
            role = ColumnRole.DATE
        elif ColumnRole.REFERENCE not in used_roles and re.search(r"\b(?:reference|chq|cheque|ref\s+no|ref|utr|instrument)\b", lowered):
            role = ColumnRole.REFERENCE
        elif ColumnRole.DESCRIPTION not in used_roles and re.search(r"\b(?:narration|description|particulars|details|remarks|transaction\s+details)\b", lowered):
            role = ColumnRole.DESCRIPTION
        elif ColumnRole.DEBIT not in used_roles and re.search(r"\b(?:withdrawal|withdrawals|debit|debits|dr)\b", lowered):
            role = ColumnRole.DEBIT
        elif ColumnRole.CREDIT not in used_roles and re.search(r"\b(?:deposit|deposits|credit|credits|cr)\b", lowered):
            role = ColumnRole.CREDIT
        elif ColumnRole.BALANCE not in used_roles and re.search(r"\b(?:balance|closing\s+balance|running\s+balance|bal)\b", lowered):
            role = ColumnRole.BALANCE
        elif ColumnRole.AMOUNT not in used_roles and re.search(r"\b(?:amount|txn\s+amount)\b", lowered):
            role = ColumnRole.AMOUNT

        if role != ColumnRole.UNKNOWN:
            used_roles.add(role)
            col_defs.append(ColumnDef(role=role, header_name=phrase, x0=c[0].x0, x1=c[-1].x1, col_idx=idx))

    col_defs.sort(key=lambda col: col.x0)
    return col_defs


def _match_word_to_column(w: ExtractedWord, col_defs: list[ColumnDef]) -> ColumnRole:
    if not col_defs:
        return ColumnRole.UNKNOWN
    # Check direct horizontal overlap first
    for col in col_defs:
        if (col.x0 - 5.0) <= w.x0 <= (col.x1 + 5.0) or (col.x0 - 5.0) <= w.x1 <= (col.x1 + 5.0):
            return col.role

    # Otherwise find nearest column center
    w_mid = (w.x0 + w.x1) / 2.0
    best_role = ColumnRole.UNKNOWN
    best_dist = float("inf")
    for col in col_defs:
        col_mid = (col.x0 + col.x1) / 2.0
        dist = abs(w_mid - col_mid)
        if dist < best_dist:
            best_dist = dist
            best_role = col.role
    return best_role


def parse_spatial_line_transactions(
    page: ExtractedPage,
    file_name: str,
    meta: dict | None = None,
    fallback_col_defs: list[ColumnDef] | None = None,
    out_col_defs: list[ColumnDef] | None = None,
    initial_txn: CanonicalTransaction | None = None,
    out_last_txn: list[CanonicalTransaction] | None = None,
) -> list[CanonicalTransaction]:
    """
    Extracts transactions from borderless text lines where column positions
    are detected from spatial word positions.
    """
    if not page.transaction_lines:
        return []

    # Check for column header line to determine column positions
    col_headers = [l for l in page.header_lines if l.line_type == LineType.COLUMN_HEADER]
    col_defs: list[ColumnDef] = []

    if col_headers:
        col_defs = extract_header_columns(col_headers[-1])

    # Fallback to previously discovered columns if this page has no explicit header
    if not col_defs and fallback_col_defs:
        col_defs = fallback_col_defs

    txns: list[CanonicalTransaction] = []
    current_txn: CanonicalTransaction | None = initial_txn
    prev_balance: float | None = initial_txn.balance if initial_txn else None

    for line in page.transaction_lines:
        text = line.text.strip()
        if not text:
            continue

        # Header/noise check (lines starting with a date are never summary lines)
        if not _starts_with_date(text) and _is_summary_or_noise_line(text):
            continue

        # Look for leading date or date token
        date_match = re.search(
            r"\b(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}[-/\.][A-Za-z]{3}[-/\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4})\b",
            text,
        )

        d = parse_date(date_match.group(1)) if (date_match and date_match.start() < 25) else None

        if d is not None:
            # Anchor found: START OF NEW TRANSACTION
            debit_val = 0.0
            credit_val = 0.0
            bal_val = None
            indicator = None

            if line.words and col_defs:
                # Group words on this line by matched column role
                amount_words_by_role: dict[ColumnRole, list[ExtractedWord]] = {
                    ColumnRole.DEBIT: [],
                    ColumnRole.CREDIT: [],
                    ColumnRole.BALANCE: [],
                    ColumnRole.AMOUNT: [],
                }
                desc_words: list[ExtractedWord] = []
                ref_words: list[ExtractedWord] = []

                # Determine which words belong to date anchor
                d_str = date_match.group(1)

                for w in line.words:
                    w_txt = w.text.strip()
                    if not w_txt:
                        continue
                    # Skip date tokens
                    if w_txt in d_str or d_str in w_txt:
                        continue
                    # Skip empty column placeholders (e.g. '-')
                    if w_txt in _PLACEHOLDER_WORDS:
                        continue

                    if _is_amount_or_placeholder(w_txt):
                        matched_role = _match_word_to_column(w, col_defs)
                        if matched_role in amount_words_by_role:
                            amount_words_by_role[matched_role].append(w)
                        elif matched_role == ColumnRole.REFERENCE:
                            ref_words.append(w)
                        else:
                            desc_words.append(w)
                    else:
                        matched_role = _match_word_to_column(w, col_defs)
                        if matched_role == ColumnRole.REFERENCE:
                            ref_words.append(w)
                        else:
                            desc_words.append(w)

                narration = " ".join(w.text for w in desc_words).strip()
                reference = " ".join(w.text for w in ref_words).strip()

                # Extract DEBIT
                if amount_words_by_role[ColumnRole.DEBIT]:
                    debit_str = " ".join(w.text for w in amount_words_by_role[ColumnRole.DEBIT])
                    amt, ind = clean_amount_str(debit_str)
                    if amt > 0:
                        debit_val = amt
                        if ind:
                            indicator = ind

                # Extract CREDIT
                if amount_words_by_role[ColumnRole.CREDIT]:
                    credit_str = " ".join(w.text for w in amount_words_by_role[ColumnRole.CREDIT])
                    amt, ind = clean_amount_str(credit_str)
                    if amt > 0:
                        credit_val = amt
                        if ind:
                            indicator = ind

                # Extract BALANCE
                if amount_words_by_role[ColumnRole.BALANCE]:
                    bal_str = " ".join(w.text for w in amount_words_by_role[ColumnRole.BALANCE])
                    amt, _ = clean_amount_str(bal_str)
                    if amt > 0:
                        bal_val = amt

                # Extract single AMOUNT column
                if amount_words_by_role[ColumnRole.AMOUNT]:
                    amt_str = " ".join(w.text for w in amount_words_by_role[ColumnRole.AMOUNT])
                    amt, ind = clean_amount_str(amt_str)
                    if amt > 0:
                        if ind == "CR":
                            credit_val = amt
                            indicator = "CR"
                        elif ind == "DR":
                            debit_val = amt
                            indicator = "DR"
                        elif bal_val is not None and prev_balance is not None:
                            delta = round(bal_val - prev_balance, 2)
                            if delta > 0:
                                credit_val = amt
                                indicator = "CR"
                            elif delta < 0:
                                debit_val = amt
                                indicator = "DR"
                            else:
                                debit_val = amt
                        else:
                            debit_val = amt

            else:
                # Fallback token extraction when words/cols not available
                amount_matches = list(re.finditer(r"\b\d{1,3}(?:,\d{2,3})*(?:\.\d{2})\b|\b\d+(?:\.\d{2})\b", text))
                amounts_found = []
                for am in amount_matches:
                    amt, ind = clean_amount_str(am.group(0))
                    if amt > 0:
                        amounts_found.append((amt, am.start(), am.end(), ind))

                narration = text[date_match.end():].strip()
                reference = ""

                if len(amounts_found) >= 2:
                    bal_val = amounts_found[-1][0]
                    txn_amts = amounts_found[:-1]
                    if len(txn_amts) == 1:
                        amt, _, _, ind = txn_amts[0]
                        if ind == "CR":
                            credit_val = amt
                            indicator = "CR"
                        else:
                            debit_val = amt
                            indicator = ind or "DR"
                    elif len(txn_amts) >= 2:
                        debit_val = txn_amts[0][0]
                        credit_val = txn_amts[1][0]
                elif len(amounts_found) == 1:
                    amt, _, _, ind = amounts_found[0]
                    if ind == "CR":
                        credit_val = amt
                        indicator = "CR"
                    else:
                        debit_val = amt
                        indicator = ind or "DR"

            # Clean trailing placeholder characters from narration
            narration = re.sub(r"\s*[-–—]{1,3}\s*$", "", narration).strip()

            # Special check: Opening / Initial Balance line
            is_opening_bal = bool(
                re.search(
                    r"\b(?:opening\s+balance|initial\s+balance|brought\s+forward|b\/f|bal\s+b\/d)\b",
                    narration,
                    re.I,
                )
            )
            if is_opening_bal:
                if bal_val is None:
                    if debit_val > 0 and credit_val == 0.0:
                        bal_val = debit_val
                        debit_val = 0.0
                    elif credit_val > 0 and debit_val == 0.0:
                        bal_val = credit_val
                        credit_val = 0.0
                else:
                    debit_val = 0.0
                    credit_val = 0.0

            new_txn = CanonicalTransaction(
                date=d,
                description=narration or "Transaction",
                reference=reference,
                debit=debit_val,
                credit=credit_val,
                balance=bal_val,
                source_page=page.page_number,
                raw_text=text,
                extra_metadata={"indicator": indicator} if indicator else {},
            )
            txns.append(new_txn)
            current_txn = new_txn
            if bal_val is not None:
                prev_balance = bal_val

        else:
            # Continuation line (no leading date)
            if current_txn is not None:
                # Check for delayed amounts or references on continuation row
                if line.words and col_defs:
                    clean_words = []
                    for w in line.words:
                        w_txt = w.text.strip()
                        if not w_txt or w_txt in _PLACEHOLDER_WORDS:
                            continue
                        if _is_amount_or_placeholder(w_txt):
                            m_role = _match_word_to_column(w, col_defs)
                            amt, ind = clean_amount_str(w_txt)
                            if amt > 0:
                                if m_role == ColumnRole.DEBIT and current_txn.debit == 0.0:
                                    current_txn.debit = amt
                                elif m_role == ColumnRole.CREDIT and current_txn.credit == 0.0:
                                    current_txn.credit = amt
                                elif m_role == ColumnRole.BALANCE and current_txn.balance is None:
                                    current_txn.balance = amt
                                    prev_balance = amt
                                elif m_role in (ColumnRole.DESCRIPTION, ColumnRole.REFERENCE):
                                    clean_words.append(w_txt)
                            elif m_role in (ColumnRole.DESCRIPTION, ColumnRole.REFERENCE):
                                clean_words.append(w_txt)
                        else:
                            clean_words.append(w_txt)
                    if clean_words:
                        current_txn.description = f"{current_txn.description} {' '.join(clean_words)}".strip()
                else:
                    amount_matches = list(re.finditer(r"\b\d{1,3}(?:,\d{2,3})*(?:\.\d{2})\b|\b\d+(?:\.\d{2})\b", text))
                    line_clean = text
                    if amount_matches:
                        for am in amount_matches:
                            amt, ind = clean_amount_str(am.group(0))
                            if amt > 0:
                                if current_txn.debit == 0.0 and current_txn.credit == 0.0:
                                    if ind == "CR":
                                        current_txn.credit = amt
                                    else:
                                        current_txn.debit = amt
                                elif current_txn.balance is None:
                                    current_txn.balance = amt
                                    prev_balance = amt
                            line_clean = line_clean.replace(am.group(0), "").strip()
                    if line_clean:
                        current_txn.description = f"{current_txn.description} {line_clean}".strip()

                current_txn.raw_text = f"{current_txn.raw_text}\n{text}"

    # Classify direction across all extracted spatial line transactions
    run_bal = None
    for txn in txns:
        t_type, resolved_dr, resolved_cr, is_unc, reason = classify_transaction_direction(
            debit=txn.debit,
            credit=txn.credit,
            current_balance=txn.balance,
            previous_balance=run_bal,
            indicator=txn.extra_metadata.get("indicator"),
        )
        txn.transaction_type = t_type
        txn.debit = resolved_dr
        txn.credit = resolved_cr
        if is_unc and not txn.is_uncertain:
            txn.is_uncertain = is_unc
            txn.uncertain_reason = reason
        if txn.balance is not None:
            run_bal = txn.balance

    if out_col_defs is not None and col_defs:
        out_col_defs.extend(col_defs)

    if out_last_txn is not None:
        out_last_txn.clear()
        if current_txn:
            out_last_txn.append(current_txn)

    return txns


# --------------------------------------------------------------------------
# Main Orchestration Function
# --------------------------------------------------------------------------
def parse_document_transactions(
    doc: ExtractedDocument,
    file_name: str,
    meta: dict | None = None,
) -> list[dict]:
    """
    Orchestrates transaction extraction across all pages of an ExtractedDocument.
    Uses hybrid strategy: Table-based extraction if structured tables are present,
    falling back to spatial line extraction for borderless pages.
    Emits canonical transaction dictionaries.
    """
    all_txns: list[CanonicalTransaction] = []
    discovered_cols: list[ColumnDef] | None = None
    last_spatial_txn: list[CanonicalTransaction] = []
    discovered_table_mapping: list[dict[ColumnRole, int]] = []

    for page in doc.pages:
        page_txns: list[CanonicalTransaction] = []

        # 1. Try table-based extraction if pdfplumber extracted valid tables
        if page.raw_tables:
            for tbl in page.raw_tables:
                fb_map = discovered_table_mapping[0] if discovered_table_mapping else None
                txns = parse_table_transactions(
                    tbl,
                    page.page_number,
                    file_name,
                    meta,
                    fallback_col_mapping=fb_map,
                    out_col_mapping=discovered_table_mapping,
                )
                if txns:
                    page_txns.extend(txns)

        # 2. If no table transactions found on this page, fall back to spatial line parser
        if not page_txns and page.transaction_lines:
            cols: list[ColumnDef] = []
            init_txn = last_spatial_txn[0] if last_spatial_txn else None
            page_txns = parse_spatial_line_transactions(
                page,
                file_name,
                meta,
                fallback_col_defs=discovered_cols,
                out_col_defs=cols,
                initial_txn=init_txn,
                out_last_txn=last_spatial_txn,
            )
            if cols:
                discovered_cols = cols

        all_txns.extend(page_txns)

    # If transactions have serial numbers (e.g. 1..660), sort by serial_no to preserve exact statement order
    if all_txns and any(t.serial_no is not None for t in all_txns):
        all_txns.sort(key=lambda t: (t.serial_no if t.serial_no is not None else 9999999, t.date or date.min))
    else:
        # Detect if statement was originally printed in descending (newest-first) order
        if len(all_txns) >= 2 and all_txns[0].date > all_txns[-1].date:
            all_txns.reverse()
        # Sort all extracted transactions chronologically
        all_txns.sort(key=lambda t: t.date or date.min)

    # Classify direction (Income / Expense / Uncertain) carrying balance forward
    prev_balance = None
    for txn in all_txns:
        ind = txn.direction or txn.extra_metadata.get("indicator")
        t_type, resolved_dr, resolved_cr, is_unc, reason = classify_transaction_direction(
            debit=txn.debit,
            credit=txn.credit,
            current_balance=txn.balance,
            previous_balance=prev_balance,
            indicator=ind,
        )
        txn.transaction_type = t_type
        if txn.direction == "CR":
            txn.credit = resolved_cr or txn.credit or resolved_dr
            txn.debit = 0.0
            txn.transaction_type = TransactionType.INCOME
        elif txn.direction == "DR":
            txn.debit = resolved_dr or txn.debit or resolved_cr
            txn.credit = 0.0
            txn.transaction_type = TransactionType.EXPENSE
        else:
            txn.debit = resolved_dr
            txn.credit = resolved_cr

        if is_unc and not txn.is_uncertain:
            txn.is_uncertain = is_unc
            txn.uncertain_reason = reason
        if txn.balance is not None:
            prev_balance = txn.balance

    # Format to canonical dictionary structure
    return [t.to_dict(file_name=file_name, meta=meta) for t in all_txns]
