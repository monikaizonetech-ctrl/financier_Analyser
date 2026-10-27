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
from decimal import Decimal, ROUND_HALF_UP
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
            "description": strip_footer_bleed(self.description) or "Transaction",
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


def calculate_transaction_confidence(txn: CanonicalTransaction) -> float:
    """Calculate extraction confidence score (0.0 to 1.0) for a canonical transaction."""
    score = 0.0
    if txn.date:
        score += 0.25
    if txn.description and txn.description.strip():
        score += 0.25
    if (txn.debit and txn.debit > 0) or (txn.credit and txn.credit > 0):
        score += 0.25
    if txn.balance is not None:
        score += 0.25

    if score < 0.60:
        txn.is_uncertain = True
        if not txn.uncertain_reason:
            txn.uncertain_reason = "Low confidence transaction data"
    else:
        txn.is_uncertain = False
        txn.uncertain_reason = ""
    return round(score, 2)


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

    # First check for fused 2-digit dates, e.g. "01/09/2501/09/25..."
    m_fused = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{2})(\d{1,2})[-/](\d{1,2})[-/](\d{2})", s)
    if m_fused:
        try:
            d, mo, yy = int(m_fused.group(1)), int(m_fused.group(2)), int(m_fused.group(3))
            y = 2000 + yy if yy < 70 else 1900 + yy
            if 1950 <= y <= 2040:
                return date(y, mo, d)
        except ValueError:
            pass

    # Check regex patterns
    # DD-MM-YYYY or DD/MM/YYYY (strictly 4-digit year, not followed by another digit)
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?!\d)", s)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1950 <= y <= 2040:
                return date(y, mo, d)
        except ValueError:
            pass

    # DD.MM.YYYY
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)", s)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1950 <= y <= 2040:
                return date(y, mo, d)
        except ValueError:
            pass

    # YYYY-MM-DD
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?!\d)", s)
    if m:
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1950 <= y <= 2040:
                return date(y, mo, d)
        except ValueError:
            pass

    # DD-Mon-YYYY or DD Mon YYYY
    m = re.match(r"^(\d{1,2})[-/\s]([A-Za-z]{3})[-/\s](\d{4})(?!\d)", s)
    if m:
        try:
            d, mon_str, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
            if 1950 <= y <= 2040:
                mo = _MONTH_MAP.get(mon_str[:3])
                if mo:
                    return date(y, mo, d)
        except ValueError:
            pass

    # Mon DD, YYYY or Month DD, YYYY (e.g. Jun 12, 2026)
    m = re.match(r"^([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})(?!\d)", s)
    if m:
        try:
            mon_str, d, y = m.group(1).lower()[:3], int(m.group(2)), int(m.group(3))
            if 1950 <= y <= 2040:
                mo = _MONTH_MAP.get(mon_str)
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

    # DD-MM-YY or DD/MM/YY
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{2})\b", s)
    if m:
        try:
            d, mo, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
            y = 2000 + yy if yy < 70 else 1900 + yy
            return date(y, mo, d)
        except ValueError:
            pass

    # DD.MM.YY
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{2})\b", s)
    if m:
        try:
            d, mo, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
            y = 2000 + yy if yy < 70 else 1900 + yy
            return date(y, mo, d)
        except ValueError:
            pass

    # Fallback standard formats
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%m/%d/%Y", "%d-%m-%y", "%d/%m/%y", "%d.%m.%y", "%d.%m.%Y"):
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

    # Remove currency symbols, trailing indicators, and spaces (but NEVER the decimal point)
    s = re.sub(r"INR|Rs\.?|[$€£\s]|(?:SB|CA)?\bdr\b|(?:SB|CA)?\bcr\b|\((?:dr|cr)\)", "", s, flags=re.IGNORECASE).strip()
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
        r"\bclosing\s+balance\b",
        r"\bcleared\s+balance\b",
        r"\bdr\.\s*count\b",
        r"\bcr\.\s*count\b",
        r"about:blank",
        r"end\s+of\s+statement",
        r"in\s+case\s+your\s+account\s+is\s+operated",
        r"^page\s+\d+\s+of\s+\d+",
        r"statement\s+of\s+account",
        r"from\s*:\s*\d{2}/\d{2}/\d{4}",
        r"rtgs/neftifsc:",
        r"branchcode\s*:",
        r"nomination:\s*registered",
        r"accountstatus\s*:",
        r"accountbranch\s*:",
        r"cust\s*id\s*:",
        r"accountno\s*:",
        r"odlimit\s*:",
        r"hdfc\s+bank\s+limited",
        r"\*?closing\s*balance\s*includes",
        r"contents\s*of\s*this\s*statement\s*will\s*be\s*considered",
        r"the\s*address\s*on\s*this\s*statement\s*is\s*that\s*on\s*record",
        r"state\s*account\s*branch\s*gstn",
        r"registered\s*office\s*address",
        r"this\s*is\s*a\s*computer[\s-]generated\s*statement",
        r"opening\s*balance\s+dr\s*count\s+cr\s*count",
        r"openingbalance\s+drcount\s+crcount",
        r"notrequiresignature",
        r"senapati\s*bapat\s*marg",
    ]
    return any(re.search(p, lowered) for p in patterns)


def strip_footer_bleed(text: str) -> str:
    """Strip page-footer text fragments before building narrations."""
    if not text:
        return ""
    patterns = [
        r"HDFC\s+BANK\s+LIMITED",
        r"\*?Closing\s*balance\s*includes[^\n]*",
        r"\*?Closingbalanceincludes[^\n]*",
        r"Contents\s*of\s*this\s*statement\s*will\s*be\s*considered[^\n]*",
        r"Contentsofthisstatementwillbeconsidered[^\n]*",
        r"The\s*address\s*on\s*this\s*statement\s*is\s*that\s*on\s*record[^\n]*",
        r"Theaddressonthisstatementisthatonrecord[^\n]*",
        r"State\s*account\s*branch\s*GSTN\s*:[^\n]*",
        r"StateaccountbranchGSTN:[^\n]*",
        r"Registered\s*Office\s*Address\s*:[^\n]*",
        r"RegisteredOfficeAddress:[^\n]*",
        r"This\s*is\s*a\s*computer[\s-]generated\s*statement[^\n]*",
        r"Thisisacomputergeneratedstatement[^\n]*",
        r"Note:\s*This\s*is\s*a\s*computer[\s-]generated\s*(?:report|statement)[^\n]*",
        r"Computer[\s-]generated\s*(?:entry|statement|report)[^\n]*",
        r"does\s+not\s+require\s+(?:any\s+)?signature[^\n]*",
        r"Acronyms\s+used\s+in\s+the\s+statement[^\n]*",
        r"Opening\s*Balance\s+Dr\s*Count\s+Cr\s*Count[^\n]*",
        r"OpeningBalance\s+DrCount\s+CrCount[^\n]*",
        r"STATEMENT\s*SUMMARY\s*:-?[^\n]*",
        r"GeneratedOn:[^\n]*",
        r"notrequiresignature\.?",
        r"HDFCBankGSTINnumberdetails[^\n]*",
        r"Senapati\s*Bapat\s*Marg[^\n]*",
        r"\bthisstatement\.?\b",
        r"daysofrequesting[^\n]*",
    ]
    cleaned = text
    for pat in patterns:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned



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

    # Find the header row (search up to 35 rows dynamically to handle long customer/branch headers)
    header_idx = -1
    col_mapping: dict[ColumnRole, int] = {}
    for r_idx in range(min(35, len(cleaned_table))):
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
_CURRENCY_CODES_AND_SYMBOLS = {"inr", "rs", "rs.", "Rs. ", "usd", "eur", "gbp", "$", "€", "£"}


def _starts_with_date(text: str) -> bool:
    return bool(re.search(r"^\s*(?:\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}[-/\.][A-Za-z]{3}[-/\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4})", text))


def _is_amount_or_placeholder(word_text: str) -> bool:
    t = word_text.strip()
    if not t:
        return False
    low = t.lower()
    if low in _PLACEHOLDER_WORDS or low in _CURRENCY_CODES_AND_SYMBOLS:
        return True
    clean_t = re.sub(r"[Rs. $€£,]", "", t).strip()
    clean_t = re.sub(r"(?i)(?:cr|dr|inr|rs)\b|\((?:cr|dr)\)", "", clean_t).strip()
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

    distinct_keywords = {"debit", "credit", "balance", "amount", "chq", "chq.no.", "details", "particulars", "description", "deposit", "withdrawal"}

    for w in sorted_words[1:]:
        gap = w.x0 - curr[-1].x1
        w_low = w.text.lower().strip()
        is_distinct_start = any(kw in w_low for kw in distinct_keywords)
        if gap <= 12.0 and not is_distinct_start:
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

        if ColumnRole.VALUE_DATE not in used_roles and re.search(r"(?:value\s*dt|value\s*date|val\s*dt)", lowered):
            role = ColumnRole.VALUE_DATE
        elif ColumnRole.DATE not in used_roles and re.search(r"\b(?:txn\s+date|trans\s+date|posting\s+date|date)\b", lowered):
            role = ColumnRole.DATE
        elif ColumnRole.REFERENCE not in used_roles and re.search(r"(?:reference|chq|cheque|ref\s*no|ref|utr|instrument)", lowered):
            role = ColumnRole.REFERENCE
        elif ColumnRole.DESCRIPTION not in used_roles and re.search(r"(?:narration|description|particulars|details|remarks|transaction\s*details)", lowered):
            role = ColumnRole.DESCRIPTION
        elif ColumnRole.DEBIT not in used_roles and re.search(r"(?:withdrawal|withdrawals|debit|debits|dr)", lowered):
            role = ColumnRole.DEBIT
        elif ColumnRole.CREDIT not in used_roles and re.search(r"(?:deposit|deposits|credit|credits|cr)", lowered):
            role = ColumnRole.CREDIT
        elif ColumnRole.BALANCE not in used_roles and re.search(r"(?:balance|closing\s*balance|running\s*balance|bal)", lowered):
            role = ColumnRole.BALANCE
        elif ColumnRole.AMOUNT not in used_roles and re.search(r"(?:amount|txn\s*amount)", lowered):
            role = ColumnRole.AMOUNT

        if role != ColumnRole.UNKNOWN:
            used_roles.add(role)
            col_defs.append(ColumnDef(role=role, header_name=phrase, x0=c[0].x0, x1=c[-1].x1, col_idx=idx))

    col_defs.sort(key=lambda col: col.x0)
    return col_defs


def _match_word_to_column(w: ExtractedWord, col_defs: list[ColumnDef]) -> ColumnRole:
    if not col_defs:
        return ColumnRole.UNKNOWN

    # Direct horizontal overlap check
    for col in col_defs:
        if w.x0 >= col.x0 - 2.0 and w.x1 <= col.x1 + 2.0:
            return col.role

    w_mid = (w.x0 + w.x1) / 2.0
    # Voronoi/interval partition between adjacent columns
    for i, col in enumerate(col_defs):
        left_bound = 0.0 if i == 0 else (col_defs[i - 1].x1 + col.x0) / 2.0
        right_bound = float("inf") if i == len(col_defs) - 1 else (col.x1 + col_defs[i + 1].x0) / 2.0
        if left_bound <= w_mid < right_bound:
            return col.role

    return ColumnRole.UNKNOWN



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

    # Fallback to previously discovered columns if this page has no explicit header or fewer columns
    if fallback_col_defs and (not col_defs or len(col_defs) < len(fallback_col_defs)):
        col_defs = fallback_col_defs

    txns: list[CanonicalTransaction] = []
    current_txn: CanonicalTransaction | None = initial_txn
    prev_balance: float | None = initial_txn.balance if initial_txn else None
    pending_ref: str = ""

    date_col = next((c for c in col_defs if c.role == ColumnRole.DATE), None) if col_defs else None
    date_col_right = 9999.0
    if col_defs and date_col:
        date_idx = col_defs.index(date_col)
        if date_idx + 1 < len(col_defs):
            date_col_right = (date_col.x1 + col_defs[date_idx + 1].x0) / 2.0
        else:
            date_col_right = date_col.x1 + 15.0

    for idx, line in enumerate(page.transaction_lines):
        text = line.text.strip()
        if not text:
            continue

        # Header/noise check
        if _is_summary_or_noise_line(text):
            continue

        # Look for leading date or date token
        date_match = re.search(
            r"\b(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}[-/\.][A-Za-z]{3}[-/\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4})\b",
            text,
        )

        d = None
        if date_match and date_match.start() < 25:
            prefix = text[:date_match.start()].lower()
            if not any(kw in prefix for kw in ("from", "to", "statement", "date:", "dated:", "branch")):
                if line.words and date_col:
                    d_word = next((w for w in line.words if date_match.group(1) in w.text or w.text in date_match.group(1)), None)
                    if d_word and (d_word.x0 + d_word.x1) / 2.0 > date_col_right:
                        d = None
                    else:
                        d = parse_date(date_match.group(1))
                else:
                    d = parse_date(date_match.group(1))

        # Check for standalone reference row preceding a new transaction
        if d is None and idx + 1 < len(page.transaction_lines) and line.words and len(line.words) <= 2:
            next_l = page.transaction_lines[idx + 1]
            if next_l.words:
                is_ref_only = all(
                    _match_word_to_column(w, col_defs) == ColumnRole.REFERENCE or re.match(r"^\d{6,16}$", w.text.strip())
                    for w in line.words
                )
                if is_ref_only:
                    nm = re.search(r"\b(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}[-/\.][A-Za-z]{3}[-/\.]\d{2,4})\b", next_l.text)
                    if nm:
                        first_w = next_l.words[0]
                        if (first_w.x0 + first_w.x1) / 2.0 <= date_col_right:
                            pending_ref = " ".join(w.text.strip() for w in line.words)
                            continue

        if d is not None:
            # Anchor found: START OF NEW TRANSACTION
            debit_val = 0.0
            credit_val = 0.0
            bal_val = None
            indicator = None
            val_date_str = ""

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

                    matched_role = _match_word_to_column(w, col_defs)
                    if _is_amount_or_placeholder(w_txt):
                        if matched_role in amount_words_by_role:
                            amount_words_by_role[matched_role].append(w)
                        elif matched_role == ColumnRole.REFERENCE:
                            ref_words.append(w)
                        elif matched_role == ColumnRole.VALUE_DATE:
                            val_date_str = w_txt
                        else:
                            desc_words.append(w)
                    elif matched_role == ColumnRole.REFERENCE:
                        ref_words.append(w)
                    elif matched_role == ColumnRole.VALUE_DATE:
                        val_date_str = w_txt
                    elif matched_role == ColumnRole.DATE and re.match(r"^\d{2}:\d{2}", w_txt):
                        pass
                    else:
                        desc_words.append(w)

                narration = " ".join(w.text for w in desc_words).strip()
                reference = " ".join(w.text for w in ref_words).strip()
                if pending_ref and not reference:
                    reference = pending_ref
                    pending_ref = ""

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
                reference = pending_ref or ""
                pending_ref = ""

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

            # Clean trailing placeholder characters from narration and strip footer bleed
            narration = re.sub(r"\s*[-–—]{1,3}\s*$", "", narration).strip()
            narration = strip_footer_bleed(narration)

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
                if bal_val is not None:
                    prev_balance = bal_val
                if meta is not None and meta.get("opening_balance") is None and bal_val is not None:
                    meta["opening_balance"] = bal_val

            new_txn = CanonicalTransaction(
                date=d,
                description=narration or "Transaction",
                reference=reference,
                debit=debit_val,
                credit=credit_val,
                balance=bal_val,
                value_date=val_date_str,
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
                if _is_summary_or_noise_line(text):
                    continue
                # Check for delayed amounts or references on continuation row
                if line.words and col_defs:
                    clean_words = []
                    for w in line.words:
                        w_txt = w.text.strip()
                        if not w_txt or w_txt in _PLACEHOLDER_WORDS:
                            continue
                        m_role = _match_word_to_column(w, col_defs)
                        if _is_amount_or_placeholder(w_txt):
                            amt, ind = clean_amount_str(w_txt)
                            if amt > 0:
                                if m_role == ColumnRole.DEBIT and current_txn.debit == 0.0:
                                    current_txn.debit = amt
                                elif m_role == ColumnRole.CREDIT and current_txn.credit == 0.0:
                                    current_txn.credit = amt
                                elif m_role == ColumnRole.BALANCE and current_txn.balance is None:
                                    current_txn.balance = amt
                                    prev_balance = amt
                                elif m_role in (ColumnRole.DESCRIPTION,):
                                    clean_words.append(w_txt)
                        elif m_role == ColumnRole.VALUE_DATE and not current_txn.value_date:
                            current_txn.value_date = w_txt
                        elif m_role == ColumnRole.REFERENCE:
                            if not current_txn.reference:
                                current_txn.reference = w_txt
                            elif w_txt not in current_txn.reference:
                                current_txn.reference = f"{current_txn.reference} {w_txt}"
                        elif m_role == ColumnRole.DATE and re.match(r"^\d{2}:\d{2}", w_txt):
                            pass
                        else:
                            clean_words.append(w_txt)
                    if clean_words:
                        addition = strip_footer_bleed(" ".join(clean_words))
                        if addition and len(current_txn.description) < 600:
                            current_txn.description = strip_footer_bleed(f"{current_txn.description} {addition}").strip()[:600]
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
                    line_clean = strip_footer_bleed(line_clean)
                    if line_clean:
                        if len(current_txn.description) < 600:
                            current_txn.description = strip_footer_bleed(f"{current_txn.description} {line_clean}").strip()[:600]

                if len(current_txn.raw_text) < 2000:
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
# Indian Bank Dedicated Text-Stream Parser
# --------------------------------------------------------------------------
# Indian Bank statements use a very specific layout:
#   - Every transaction starts with a line matching  dd/mm/yy dd/mm/yy <narration>
#   - If that line ends with  <amount> <balance>Cr  it is a complete single-line row.
#   - Otherwise, continuation lines are accumlated as narration until the line
#     that ends with  <amount> <balance>Cr.  Nothing after that line is ever
#     attached to the current transaction.
#   - Certain continuation prefixes (OWN DELINK, TRANSFER TO/FROM, INW_CLG, …)
#     are prefix narration for the *next* date line, not the current one.
#   - Zero-amount rows (e.g. OWN DELINK … 0.00) are silently dropped.

_IB_DATE_START = re.compile(
    r"^(?:(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})|(\d{2}/\d{2}/\d{2})(\d{2}/\d{2}/\d{2}))"
)
_IB_AMT_BAL = re.compile(r"([\d,]+\.\d{2})\s+([\d,]+\.\d{2})Cr$", re.IGNORECASE)
_IB_NOISE = [
    re.compile(r"^\s*Statement\s*$", re.I),
    re.compile(r"^\s*Summary\s*$", re.I),
    re.compile(r"^\s*(?:Dr\.|Cr\.)\s*Count:", re.I),
    re.compile(r"In Case Your Account", re.I),
    re.compile(r"With Extra Care", re.I),
    re.compile(r"Carried Forward", re.I),
    re.compile(r"Brought Forward", re.I),
    re.compile(r"CLOSING\s+BALANCE\s*:", re.I),
    re.compile(r"\*\*\*\s*END OF STATEMENT\s*\*\*\*", re.I),
    re.compile(r"about:blank", re.I),
    re.compile(r"STATEMENT OF ACCOUNT", re.I),
    re.compile(r"Post Date\s+Value Date\s+Details", re.I),
    re.compile(r"Post Date\s+Details", re.I),
    re.compile(r"^\s*Date\s*$", re.I),
    re.compile(r"^\s*Value\s*$", re.I),
    re.compile(r"^\s*Account No\s*:", re.I),
    re.compile(r"^\s*Statement From\s*:", re.I),
    re.compile(r"^\s*To\s*:\s*\d{2}-[A-Za-z]{3}-\d{4}", re.I),
    re.compile(r"Branch Code\s*:", re.I),
    re.compile(r"Product\s*:", re.I),
    re.compile(r"Currency\s*:", re.I),
    re.compile(r"Int Rate\s*:", re.I),
    re.compile(r"Limit\s*:", re.I),
    re.compile(r"Drawing Power\s*:", re.I),
    re.compile(r"Cleared Balance\s*:", re.I),
    re.compile(r"Uncleared Amount\s*:", re.I),
    re.compile(r"Ckyc ID\s*:", re.I),
    re.compile(r"Nominee", re.I),
]
# Lines that start a *prefix* block for the NEXT transaction (not narration of current)
_IB_PREFIX_STARTERS = [
    re.compile(r"^TRANSFER TO\b", re.I),
    re.compile(r"^TRANSFER FROM\b", re.I),
    re.compile(r"^INW_CLG\b", re.I),
    re.compile(r"^CASH DEP\b", re.I),
    re.compile(r"^Txn\s*Amt\b", re.I),
    re.compile(r"OWN DELINK\b", re.I),
]


def _ib_is_noise(text: str) -> bool:
    return any(p.search(text) for p in _IB_NOISE)


def _ib_is_prefix_start(text: str) -> bool:
    return any(p.search(text) for p in _IB_PREFIX_STARTERS)


def parse_indian_bank_text_transactions(
    doc: ExtractedDocument,
    file_name: str,
    meta: dict | None = None,
) -> list[dict]:
    """
    Dedicated spatial parser for Indian Bank (IDIB) text-layout statements.

    Uses vertical gap clustering on each page's transaction table area
    (bounded between 'Brought Forward' and 'Carried Forward' / 'CLOSING BALANCE :')
    to isolate each transaction row block without narration bleed.
    Extracts Post Date, Value Date, Cheque/Reference Number, Debit, Credit,
    Running Balance, and complete multi-line descriptions accurately.
    Zero-amount administrative delink rows are silently dropped.
    """
    # 0. Extract Brought Forward balance from the FIRST "Brought Forward" line before any transaction
    opening_balance_dec: Decimal | None = None
    for page in doc.pages:
        for line in page.lines:
            m_bf = re.search(r"Brought\s+Forward\s+([\d,]+\.?\d*)", line.text, re.I)
            if m_bf:
                opening_balance_dec = Decimal(m_bf.group(1).replace(",", "")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                break
        if opening_balance_dec is not None:
            break

    if opening_balance_dec is None and meta and meta.get("opening_balance") is not None:
        opening_balance_dec = Decimal(str(meta["opening_balance"])).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    if meta is not None and opening_balance_dec is not None:
        meta["opening_balance"] = float(opening_balance_dec)

    raw_txns: list[dict] = []

    for page in doc.pages:
        pno = page.page_number
        in_txn = False
        txn_lines: list[ExtractedLine] = []

        # Isolate transaction table lines between Brought Forward and Carried Forward / Closing Balance
        for line in page.lines:
            text_lower = line.text.lower()
            if "brought forward" in text_lower:
                in_txn = True
                continue
            if "carried forward" in text_lower or "closing balance" in text_lower:
                in_txn = False
                break
            if in_txn:
                txn_lines.append(line)

        # Cluster lines into transaction blocks based on vertical gap (> 10.5 pt)
        blocks: list[list[ExtractedLine]] = []
        curr_block: list[ExtractedLine] = []
        prev_y: float | None = None

        for line in txn_lines:
            if prev_y is not None and (line.y_top - prev_y) > 10.5:
                if curr_block:
                    blocks.append(curr_block)
                curr_block = [line]
            else:
                curr_block.append(line)
            prev_y = line.y_top

        if curr_block:
            blocks.append(curr_block)

        for b in blocks:
            block_text = " ".join(l.text for l in b)
            # Skip administrative delink records (0.00 with no balance)
            if "0.00" in block_text and not re.search(r"[\d,]+\.\d{2}\s*(?:Cr|Dr)", block_text, re.I):
                continue

            # Identify the line containing transaction dates
            date_line_idx = -1
            for idx, l in enumerate(b):
                if _IB_DATE_START.search(l.text):
                    date_line_idx = idx
                    break

            if date_line_idx == -1:
                continue

            dl = b[date_line_idx]
            dt = dl.text
            d_m = _IB_DATE_START.search(dt)
            if not d_m:
                continue

            post_date_str = d_m.group(1) or d_m.group(3)
            val_date_str = d_m.group(2) or d_m.group(4)

            post_date = parse_date(post_date_str)
            val_date = parse_date(val_date_str) if val_date_str else post_date
            val_date_formatted = val_date.strftime("%d/%m/%Y") if val_date else ""

            # Extract Running Balance
            bal_dec: Decimal | None = None
            bal_words = [w for w in dl.words if w.x0 >= 485]
            for bw in bal_words:
                m = re.search(r"([\d,]+\.\d{2})(?:Cr|Dr)", bw.text, re.I)
                if m:
                    bal_dec = Decimal(m.group(1).replace(",", "")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    break
            if bal_dec is None:
                m = re.search(r"([\d,]+\.\d{2})\s*(?:Cr|Dr)", dt, re.I)
                if m:
                    bal_dec = Decimal(m.group(1).replace(",", "")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )

            if bal_dec is None:
                continue

            # Extract Amount (Debit: ~370-432, Credit: ~432-485)
            amt_dec: Decimal | None = None
            amt_words = [w for w in dl.words if 370 <= w.x0 < 485]
            for aw in amt_words:
                m = re.search(r"([\d,]+\.\d{2})", aw.text)
                if m:
                    amt_dec = Decimal(m.group(1).replace(",", "")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    break
            if amt_dec is None:
                matches = list(re.finditer(r"([\d,]+\.\d{2})", dt))
                if len(matches) >= 2:
                    amt_dec = Decimal(matches[-2].group(1).replace(",", "")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )

            # Extract Cheque Number (318 <= x < 375, or ChqNo: in text)
            chq_str = ""
            chq_words = [w for w in dl.words if 318 <= w.x0 < 375 and re.match(r"^\d{4,10}$", w.text.strip())]
            if chq_words:
                chq_str = chq_words[0].text.strip()
            else:
                # Handle merged token boundary (e.g. JUNCTION329683)
                merged_words = [w for w in dl.words if 310 <= w.x1 < 375 and re.search(r"([A-Za-z/]+)(\d{5,8})$", w.text.strip())]
                if merged_words:
                    m = re.search(r"([A-Za-z/]+)(\d{5,8})$", merged_words[0].text.strip())
                    chq_str = m.group(2) if m else ""
                else:
                    m_chq = re.search(r"ChqNo\s*:\s*(\d+)", block_text, re.I)
                    if m_chq:
                        chq_str = m_chq.group(1)

            # Assemble description words across all lines belonging exclusively to this transaction
            desc_parts: list[str] = []
            for idx, l in enumerate(b):
                if idx == date_line_idx:
                    line_desc_words: list[str] = []
                    for w in l.words:
                        w_txt = w.text.strip()
                        if w.x0 < 130:
                            continue  # Date columns
                        if w.x0 >= 375:
                            continue  # Amount / Balance columns
                        if chq_str and w_txt == chq_str:
                            continue  # Cheque column
                        if chq_str and w_txt.endswith(chq_str) and len(w_txt) > len(chq_str):
                            w_txt = w_txt[:-len(chq_str)].strip()
                        if w_txt:
                            line_desc_words.append(w_txt)
                    if line_desc_words:
                        desc_parts.append(" ".join(line_desc_words))
                else:
                    line_words = [w.text.strip() for w in l.words if w.x0 < 375]
                    if line_words:
                        desc_parts.append(" ".join(line_words))

            description = re.sub(r"\s+", " ", " ".join(desc_parts).strip())

            raw_txns.append({
                "page": pno,
                "date": post_date,
                "value_date_str": val_date_formatted,
                "description": description,
                "chq_no": chq_str,
                "amt": amt_dec,
                "bal": bal_dec,
                "raw_lines": [l.text for l in b],
            })

        # Promptly release page-level data structures to conserve memory
        try:
            page.lines.clear()
            page.transaction_lines.clear()
            page.header_lines.clear()
            page.footer_lines.clear()
            page.raw_tables.clear()
            page.raw_text = ""
        except Exception:
            pass

    # Convert to CanonicalTransaction dicts using balance-difference method
    result: list[dict] = []
    prev_bal = opening_balance_dec
    parse_errors = []

    for idx, t in enumerate(raw_txns, start=1):
        d = t["date"]
        if d is None:
            continue

        bal_dec = t["bal"]
        amt_dec = t["amt"]

        if prev_bal is not None:
            diff = bal_dec - prev_bal
            if diff > 0:
                credit_dec = diff
                debit_dec = Decimal("0.00")
                indicator = "CR"
                t_type = TransactionType.INCOME
            elif diff < 0:
                debit_dec = abs(diff)
                credit_dec = Decimal("0.00")
                indicator = "DR"
                t_type = TransactionType.EXPENSE
            else:
                credit_dec = Decimal("0.00")
                debit_dec = Decimal("0.00")
                indicator = "NC"
                t_type = TransactionType.UNCERTAIN

            if amt_dec is not None and abs(diff) != amt_dec:
                err_msg = (
                    f"Row {idx} ({d}): parsed amount {amt_dec} != |balance delta| {abs(diff)} "
                    f"(prev_bal={prev_bal}, bal={bal_dec}, desc={t['description'][:50]})"
                )
                parse_errors.append(err_msg)
        else:
            credit_dec = Decimal("0.00")
            debit_dec = amt_dec or Decimal("0.00")
            indicator = "DR"
            t_type = TransactionType.EXPENSE

        prev_bal = bal_dec

        txn = CanonicalTransaction(
            date=d,
            description=t["description"] or "Transaction",
            reference=t["chq_no"],
            debit=float(debit_dec),
            credit=float(credit_dec),
            balance=float(bal_dec),
            source_page=t["page"],
            raw_text="\n".join(t["raw_lines"])[:2000],
            transaction_type=t_type,
            value_date=t["value_date_str"],
            extra_metadata={"indicator": indicator} if indicator else {},
        )
        t_dict = txn.to_dict(file_name=file_name, meta=meta)
        if opening_balance_dec is not None:
            t_dict["statement_opening_balance"] = float(opening_balance_dec)
        result.append(t_dict)

    if parse_errors:
        raise ValueError(
            f"Transaction parsing errors detected:\n" + "\n".join(parse_errors[:10])
        )

    return result


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
    # --- Indian Bank: use dedicated stream parser ONLY if text-stream layout matches ---
    bank = (meta or {}).get("bank_name", "").upper()
    if bank == "INDIAN BANK":
        has_ib_stream = any(
            _IB_DATE_START.match(line.text.strip())
            for page in doc.pages
            for line in page.transaction_lines
        )
        if has_ib_stream:
            return parse_indian_bank_text_transactions(doc, file_name, meta)

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
            if cols and (not discovered_cols or len(cols) >= len(discovered_cols) or len(cols) >= 5):
                discovered_cols = cols

        all_txns.extend(page_txns)

        # Promptly release page-level data structures to free RAM
        try:
            page.raw_tables.clear()
            page.lines.clear()
            page.transaction_lines.clear()
            page.header_lines.clear()
            page.footer_lines.clear()
            page.raw_text = ""
        except Exception:
            pass

    # Deduplicate only true duplicate records (e.g. repeated table rows or duplicated page reads)
    deduped = []
    seen = set()
    for txn in all_txns:
        key = (
            txn.source_page,
            txn.date,
            round(txn.debit or 0.0, 2),
            round(txn.credit or 0.0, 2),
            round(txn.balance or 0.0, 2) if txn.balance is not None else None,
            txn.reference.strip().lower() if txn.reference else "",
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(txn)
    all_txns = deduped


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
    prev_balance = meta.get("opening_balance") if meta else None
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
