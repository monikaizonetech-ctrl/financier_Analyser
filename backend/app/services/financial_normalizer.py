"""
Universal Date and Financial Amount Normalization Engine.

Provides high-precision Decimal arithmetic, locale-aware number parsing
(Indian 12,34,567.89 and International 1,234,567.89), Dr/Cr indicator extraction,
and comprehensive date parsing with document-wide ambiguity resolution.
"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Optional, Tuple

import dateutil.parser


MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

# Regex patterns for date extraction
_DATE_DD_MM_YYYY = re.compile(r"^(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{2,4})$")
_DATE_YYYY_MM_DD = re.compile(r"^(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})$")
_DATE_TEXT_MONTH = re.compile(
    r"^(\d{1,2})[-/\s]([A-Za-z]{3,9})[-/\s](\d{2,4})$",
    re.IGNORECASE,
)
_DATE_MONTH_FIRST_TEXT = re.compile(
    r"^([A-Za-z]{3,9})[-/\s](\d{1,2})(?:st|nd|rd|th)?(?:,)?[-/\s](\d{2,4})$",
    re.IGNORECASE,
)

# Currency & noise cleaner regex
_CURRENCY_SYMBOLS = re.compile(r"[₹$€£\s\xa0]|rs\.?|inr", re.IGNORECASE)
_DR_CR_SUFFIX = re.compile(r"\s*\(?(dr|cr)\)?$", re.IGNORECASE)
_DR_CR_PREFIX = re.compile(r"^\(?(dr|cr)\)?\s*", re.IGNORECASE)


class UniversalDateNormalizer:
    """Normalizes arbitrary bank statement date strings into datetime.date objects.
    Uses document-wide context to resolve DD/MM vs MM/DD ambiguities.
    """

    def __init__(self, prefer_day_first: bool = True):
        self.prefer_day_first = prefer_day_first
        self.observed_day_first_evidence = 0
        self.observed_month_first_evidence = 0

    def feed_evidence(self, text: str) -> None:
        """Inspect date candidates across the document to build ambiguity resolution context."""
        if not text:
            return
        clean = text.strip()
        m = _DATE_DD_MM_YYYY.match(clean)
        if m:
            p1, p2, _ = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if p1 > 12 and p2 <= 12:
                self.observed_day_first_evidence += 1
            elif p2 > 12 and p1 <= 12:
                self.observed_month_first_evidence += 1

    @property
    def is_day_first(self) -> bool:
        if self.observed_day_first_evidence > self.observed_month_first_evidence:
            return True
        if self.observed_month_first_evidence > self.observed_day_first_evidence:
            return False
        return self.prefer_day_first

    def parse(self, val: Any) -> Tuple[Optional[date], bool, float]:
        """
        Parses input into (date, is_ambiguous, confidence).
        Confidence is 1.0 for named months / unambiguous days > 12,
        0.85 for context-resolved dates, and 0.5 for unresolved ambiguous dates.
        """
        if val is None or val == "":
            return None, False, 0.0

        if isinstance(val, date):
            if isinstance(val, datetime):
                return val.date(), False, 1.0
            return val, False, 1.0

        s = str(val).strip()
        if not s or s.lower() in ("nan", "none", "null", "-", "nil"):
            return None, False, 0.0

        # Strip time if present
        s = re.split(r"\s+(?:\d{1,2}:\d{2})", s)[0].strip()

        # 1. Check text month (e.g. 12-Jan-2026 or 12 Jan 2026) -> Unambiguous
        m_txt = _DATE_TEXT_MONTH.match(s)
        if m_txt:
            d_int = int(m_txt.group(1))
            mon_str = m_txt.group(2).lower()
            y_int = int(m_txt.group(3))
            if y_int < 100:
                y_int += 2000 if y_int < 50 else 1900
            m_int = MONTH_MAP.get(mon_str)
            if m_int:
                try:
                    return date(y_int, m_int, d_int), False, 1.0
                except ValueError:
                    pass

        # 2. Check month first text (e.g. Jan 12, 2026) -> Unambiguous
        m_txt_first = _DATE_MONTH_FIRST_TEXT.match(s)
        if m_txt_first:
            mon_str = m_txt_first.group(1).lower()
            d_int = int(m_txt_first.group(2))
            y_int = int(m_txt_first.group(3))
            if y_int < 100:
                y_int += 2000 if y_int < 50 else 1900
            m_int = MONTH_MAP.get(mon_str)
            if m_int:
                try:
                    return date(y_int, m_int, d_int), False, 1.0
                except ValueError:
                    pass

        # 3. Check ISO YYYY-MM-DD
        m_iso = _DATE_YYYY_MM_DD.match(s)
        if m_iso:
            y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
            try:
                return date(y, m, d), False, 1.0
            except ValueError:
                pass

        # 4. Check DD-MM-YYYY vs MM-DD-YYYY
        m_num = _DATE_DD_MM_YYYY.match(s)
        if m_num:
            p1, p2, p3 = int(m_num.group(1)), int(m_num.group(2)), int(m_num.group(3))
            if p3 < 100:
                p3 += 2000 if p3 < 50 else 1900

            # Strictly unambiguous if p1 > 12 (must be DD/MM)
            if p1 > 12 and p2 <= 12:
                try:
                    return date(p3, p2, p1), False, 1.0
                except ValueError:
                    pass
            # Strictly unambiguous if p2 > 12 (must be MM/DD)
            elif p2 > 12 and p1 <= 12:
                try:
                    return date(p3, p1, p2), False, 1.0
                except ValueError:
                    pass
            else:
                # Ambiguous: e.g. 03/04/2026. Use document evidence
                is_day_first = self.is_day_first
                confidence = 0.85 if (self.observed_day_first_evidence or self.observed_month_first_evidence) else 0.6
                try:
                    if is_day_first:
                        return date(p3, p2, p1), True, confidence
                    else:
                        return date(p3, p1, p2), True, confidence
                except ValueError:
                    pass

        # 5. Fallback to python-dateutil
        try:
            dt = dateutil.parser.parse(s, dayfirst=self.is_day_first, fuzzy=True)
            return dt.date(), True, 0.7
        except Exception:
            return None, False, 0.0


class UniversalAmountNormalizer:
    """Normalizes financial amounts to Decimal with 2 decimal places.
    Supports Indian (12,34,567.89) and International (1,234,567.89) grouping,
    negative parens (500.00), Dr/Cr tags, and currency symbols.
    """

    TWO_PLACES = Decimal("0.01")

    @classmethod
    def parse(
        cls,
        val: Any,
        default_direction: Optional[str] = None,
    ) -> Tuple[Optional[Decimal], Optional[str], bool, str]:
        """
        Parses val into:
        (amount: Decimal | None, direction: 'DR'|'CR'|None, is_valid: bool, raw_cleaned: str)
        Returns (Decimal("0.00"), ...) for genuine zeros and (None, ...) for missing values.
        """
        if val is None:
            return None, default_direction, True, ""

        if isinstance(val, (int, float, Decimal)):
            d_val = Decimal(str(val)).quantize(cls.TWO_PLACES, rounding=ROUND_HALF_UP)
            is_neg = d_val < Decimal("0")
            abs_val = abs(d_val)
            direction = default_direction
            if is_neg:
                direction = "DR"
            return abs_val, direction, True, str(val)

        s = str(val).strip()
        if not s or s.lower() in ("nan", "none", "null", "-", "nil", "--", "***"):
            return None, default_direction, True, s

        raw_original = s
        direction = default_direction

        # Detect Dr / Cr in string
        dr_cr_match = _DR_CR_SUFFIX.search(s) or _DR_CR_PREFIX.search(s)
        if dr_cr_match:
            marker = dr_cr_match.group(1).upper()
            direction = "DR" if marker == "DR" else "CR"
            s = _DR_CR_SUFFIX.sub("", s)
            s = _DR_CR_PREFIX.sub("", s).strip()

        # Detect parentheses negative: (1,250.00)
        is_negative = False
        paren_m = re.match(r"^\s*\(\s*(.*?)\s*\)\s*$", s)
        if paren_m:
            is_negative = True
            direction = "DR"
            s = paren_m.group(1).strip()
        elif s.startswith("-") or s.endswith("-"):
            is_negative = True
            direction = "DR"
            s = s.strip("-").strip()

        # Remove currency symbols and non-breaking spaces
        s = _CURRENCY_SYMBOLS.sub("", s).strip()

        # Remove internal noise characters
        s = s.replace(" ", "")

        if not s:
            return None, direction, False, raw_original

        # Indian / Western comma handling:
        # e.g. "12,34,567.89" -> commas are purely grouping separators
        # e.g. "1.234.567,89" (European) vs "1,234,567.89"
        if "," in s and "." in s:
            # If comma comes before period (e.g. 1,234.56 or 12,34,567.89), commas are grouping
            if s.rfind(",") < s.rfind("."):
                s = s.replace(",", "")
            else:
                # European style: 1.234,56
                s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            # Only commas present: if exactly 2 digits after last comma, might be European decimal
            # otherwise commas are thousand separators in whole numbers e.g. 50,000
            parts = s.split(",")
            if len(parts[-1]) == 2 and len(parts) == 2:
                s = parts[0] + "." + parts[1]
            else:
                s = s.replace(",", "")

        try:
            amount = Decimal(s).quantize(cls.TWO_PLACES, rounding=ROUND_HALF_UP)
            if is_negative:
                amount = abs(amount)
            return amount, direction, True, raw_original
        except (InvalidOperation, ValueError):
            return None, direction, False, raw_original


# Convenience singleton functions for easy imports
_default_normalizer = UniversalDateNormalizer()

def parse_date(val: Any) -> Optional[date]:
    d, _, _ = _default_normalizer.parse(val)
    return d

def clean_amount(val: Any) -> Optional[Decimal]:
    amt, _, _, _ = UniversalAmountNormalizer.parse(val)
    return amt

def clean_amount_float(val: Any) -> Optional[float]:
    amt = clean_amount(val)
    return float(amt) if amt is not None else None

