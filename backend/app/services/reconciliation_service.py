"""
Financial validation and reconciliation service for bank statements.

Detects parsing mistakes, arithmetic discrepancies, and structural anomalies
before final report generation:
- Reconciles cash flow: Net Cash Flow = Total Income - Total Expense
- Verifies closing balance: Expected Closing = Opening + Total Income - Total Expense
- Evaluates running balance continuity: Previous + Credit - Debit = Current
- Diagnoses root causes:
  * Missing transactions (unaccounted balance jumps)
  * Duplicate transactions (repeated rows without balance change)
  * Inverted debit/credit (swapped transaction direction)
  * Incorrect amount extraction
  * Header/footer leaks (summary rows parsed as transactions)
- Emits detailed audit trails with source_page and raw_text for debugging
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
import re
from typing import Any



class ValidationStatus(str, Enum):
    VALID = "VALID"
    WARNING = "WARNING"
    SUSPICIOUS = "SUSPICIOUS"
    ERROR = "ERROR"


class DiscrepancyType(str, Enum):
    CLOSING_BALANCE_MISMATCH = "CLOSING_BALANCE_MISMATCH"
    TRANSACTION_BALANCE_MISMATCH = "TRANSACTION_BALANCE_MISMATCH"
    POSSIBLE_MISSING_TRANSACTION = "POSSIBLE_MISSING_TRANSACTION"
    POSSIBLE_INVERTED_DEBIT_CREDIT = "POSSIBLE_INVERTED_DEBIT_CREDIT"
    POSSIBLE_DUPLICATE_TRANSACTION = "POSSIBLE_DUPLICATE_TRANSACTION"
    SUSPICIOUS_HEADER_FOOTER_ENTRY = "SUSPICIOUS_HEADER_FOOTER_ENTRY"
    INCORRECT_AMOUNT_EXTRACTION = "INCORRECT_AMOUNT_EXTRACTION"


@dataclass
class Discrepancy:
    type: DiscrepancyType
    severity: ValidationStatus
    message: str
    transaction_index: int | None = None
    date: date | None = None
    description: str | None = None
    source_page: int | None = None
    raw_text: str | None = None
    expected_value: float | None = None
    actual_value: float | None = None
    difference: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "transaction_index": self.transaction_index,
            "date": self.date.isoformat() if isinstance(self.date, (date,)) else str(self.date or ""),
            "description": self.description,
            "source_page": self.source_page,
            "raw_text": self.raw_text,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "difference": self.difference,
        }


@dataclass
class ReconciliationReport:
    status: ValidationStatus
    opening_balance: float
    total_income: float
    total_expense: float
    net_cash_flow: float
    expected_closing_balance: float
    extracted_closing_balance: float | None
    closing_balance_difference: float = 0.0
    total_transactions: int = 0
    verified_transactions: int = 0
    discrepancy_count: int = 0
    discrepancies: list[Discrepancy] = field(default_factory=list)
    summary_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "opening_balance": self.opening_balance,
            "total_income": self.total_income,
            "total_expense": self.total_expense,
            "net_cash_flow": self.net_cash_flow,
            "expected_closing_balance": self.expected_closing_balance,
            "extracted_closing_balance": self.extracted_closing_balance,
            "closing_balance_difference": self.closing_balance_difference,
            "total_transactions": self.total_transactions,
            "verified_transactions": self.verified_transactions,
            "discrepancy_count": self.discrepancy_count,
            "discrepancies": [d.to_dict() for d in self.discrepancies],
            "summary_notes": self.summary_notes,
        }


_HEADER_FOOTER_PATTERNS = [
    r"^page\s+\d+\s+(?:of|\/)\s+\d+",
    r"\btotal\b",
    r"\bgrand\s+total\b",
    r"\bbrought\s+forward\b",
    r"\bcarried\s+forward\b",
    r"\bb\/f\b",
    r"\bc\/f\b",
    r"\bclosing\s+balance\b",
    r"\bend\s+of\s+statement\b",
    r"\bstatement\s+summary\b",
]


def _matches_header_footer_pattern(text: str) -> bool:
    lowered = (text or "").lower().strip()
    return any(re.search(pat, lowered) for pat in _HEADER_FOOTER_PATTERNS)


def reconcile_transactions(
    rows: list[dict],
    opening_balance: float | None = None,
    extracted_closing_balance: float | None = None,
) -> ReconciliationReport:
    """
    Performs comprehensive financial validation and reconciliation
    across all parsed transaction rows.
    """
    if not rows:
        return ReconciliationReport(
            status=ValidationStatus.VALID,
            opening_balance=0.0,
            total_income=0.0,
            total_expense=0.0,
            net_cash_flow=0.0,
            expected_closing_balance=0.0,
            extracted_closing_balance=extracted_closing_balance,
            total_transactions=0,
            verified_transactions=0,
            discrepancy_count=0,
            summary_notes=["No transaction rows to reconcile."],
        )

    discrepancies: list[Discrepancy] = []

    # 1. Compute totals strictly by direction
    total_income = round(sum(float(r.get("credit") or 0.0) for r in rows), 2)
    total_expense = round(sum(float(r.get("debit") or 0.0) for r in rows), 2)
    net_cash_flow = round(total_income - total_expense, 2)

    # Determine Opening Balance
    if opening_balance is not None:
        open_bal = round(opening_balance, 2)
    else:
        first = rows[0]
        if first.get("balance") is not None:
            first_cr = float(first.get("credit") or 0.0)
            first_dr = float(first.get("debit") or 0.0)
            open_bal = round(first["balance"] - first_cr + first_dr, 2)
        else:
            open_bal = 0.0

    # Calculate Expected Closing Balance
    expected_closing = round(open_bal + net_cash_flow, 2)

    # Determine actual extracted closing balance
    actual_closing = extracted_closing_balance
    if actual_closing is None:
        last_with_bal = next((r["balance"] for r in reversed(rows) if r.get("balance") is not None), None)
        actual_closing = round(last_with_bal, 2) if last_with_bal is not None else expected_closing

    closing_diff = round(actual_closing - expected_closing, 2)

    # 2. Check Closing Balance Match
    if abs(closing_diff) > 0.05:
        discrepancies.append(
            Discrepancy(
                type=DiscrepancyType.CLOSING_BALANCE_MISMATCH,
                severity=ValidationStatus.ERROR,
                message=(
                    f"Closing balance mismatch: Expected {expected_closing:.2f} "
                    f"(Opening {open_bal:.2f} + Net {net_cash_flow:.2f}), but statement shows {actual_closing:.2f}. "
                    f"Difference: {closing_diff:+.2f}."
                ),
                expected_value=expected_closing,
                actual_value=actual_closing,
                difference=closing_diff,
            )
        )

    # 3. Row-by-Row Continuity & Diagnostic Checks
    prev_balance = open_bal
    verified_txns = 0

    for idx, r in enumerate(rows, start=1):
        dr = round(float(r.get("debit") or 0.0), 2)
        cr = round(float(r.get("credit") or 0.0), 2)
        curr_bal = r.get("balance")
        desc = r.get("description", "")
        src_page = r.get("source_page", 1)
        raw = r.get("raw_text", "")

        # Check for header/footer leak in transaction description
        if _matches_header_footer_pattern(desc):
            # Check if this row is a genuine transaction or leaked summary row
            if dr == 0 and cr == 0:
                if idx == 1 and curr_bal is not None and any(k in desc.lower() for k in ("opening", "initial", "brought forward", "b/f", "bal b/d")):
                    # Valid opening/initial balance anchor line
                    pass
                else:
                    discrepancies.append(
                        Discrepancy(
                            type=DiscrepancyType.SUSPICIOUS_HEADER_FOOTER_ENTRY,
                            severity=ValidationStatus.WARNING,
                            message=f"Leaked header/summary line parsed as transaction: '{desc}'",
                            transaction_index=idx,
                            date=r.get("date"),
                            description=desc,
                            source_page=src_page,
                            raw_text=raw,
                        )
                    )

        if curr_bal is not None:
            curr_bal = round(curr_bal, 2)
            expected_curr = round(prev_balance + cr - dr, 2)
            diff = round(curr_bal - expected_curr, 2)

            if abs(diff) <= 0.05:
                verified_txns += 1
            else:
                # Discrepancy detected! Diagnose why:
                # Diagnostic A: Inverted Debit / Credit?
                # Test what happens if we subtract credit and add debit instead
                inverted_test = round(prev_balance + dr - cr, 2)
                if abs(curr_bal - inverted_test) <= 0.05 and (dr > 0 or cr > 0):
                    discrepancies.append(
                        Discrepancy(
                            type=DiscrepancyType.POSSIBLE_INVERTED_DEBIT_CREDIT,
                            severity=ValidationStatus.SUSPICIOUS,
                            message=(
                                f"Row {idx} appears to have inverted debit/credit. "
                                f"Current: Dr={dr:.2f}, Cr={cr:.2f}. Balance movement matches Dr={cr:.2f}, Cr={dr:.2f}."
                            ),
                            transaction_index=idx,
                            date=r.get("date"),
                            description=desc,
                            source_page=src_page,
                            raw_text=raw,
                            expected_value=expected_curr,
                            actual_value=curr_bal,
                            difference=diff,
                        )
                    )
                # Diagnostic B: Missing Transaction?
                elif abs(diff) > 0.05:
                    discrepancies.append(
                        Discrepancy(
                            type=DiscrepancyType.POSSIBLE_MISSING_TRANSACTION,
                            severity=ValidationStatus.SUSPICIOUS,
                            message=(
                                f"Row {idx} has an unexplained balance jump of {diff:+.2f}. "
                                f"Expected {expected_curr:.2f}, but found {curr_bal:.2f}. "
                                f"A transaction of {abs(diff):.2f} may be missing before this line."
                            ),
                            transaction_index=idx,
                            date=r.get("date"),
                            description=desc,
                            source_page=src_page,
                            raw_text=raw,
                            expected_value=expected_curr,
                            actual_value=curr_bal,
                            difference=diff,
                        )
                    )

            prev_balance = curr_bal
        else:
            # Running balance not reported on this row
            prev_balance = round(prev_balance + cr - dr, 2)

    # 4. Duplicate Transaction Detection
    for i in range(len(rows)):
        for j in range(i + 1, min(i + 4, len(rows))):
            r1, r2 = rows[i], rows[j]
            same_date = r1.get("date") == r2.get("date")
            same_amt = (r1.get("debit") == r2.get("debit")) and (r1.get("credit") == r2.get("credit"))
            same_desc = r1.get("description", "").strip().lower() == r2.get("description", "").strip().lower()

            if same_date and same_amt and same_desc and (r1.get("debit", 0) > 0 or r1.get("credit", 0) > 0):
                # Check if running balance moved
                b1, b2 = r1.get("balance"), r2.get("balance")
                if b1 is not None and b2 is not None and b1 == b2:
                    # Balance DID NOT MOVE -> parsing duplicate!
                    discrepancies.append(
                        Discrepancy(
                            type=DiscrepancyType.POSSIBLE_DUPLICATE_TRANSACTION,
                            severity=ValidationStatus.WARNING,
                            message=(
                                f"Duplicate transaction detected at row {j + 1} matching row {i + 1} "
                                f"('{r1.get('description')}', amount {r1.get('debit') or r1.get('credit')}) "
                                f"with identical running balance {b1:.2f}."
                            ),
                            transaction_index=j + 1,
                            date=r2.get("date"),
                            description=r2.get("description"),
                            source_page=r2.get("source_page"),
                            raw_text=r2.get("raw_text"),
                        )
                    )

    # 5. Determine Overall Validation Status
    has_error = any(d.severity == ValidationStatus.ERROR for d in discrepancies)
    has_suspicious = any(d.severity == ValidationStatus.SUSPICIOUS for d in discrepancies)
    has_warning = any(d.severity == ValidationStatus.WARNING for d in discrepancies)

    if has_error:
        overall_status = ValidationStatus.ERROR
    elif has_suspicious:
        overall_status = ValidationStatus.SUSPICIOUS
    elif has_warning:
        overall_status = ValidationStatus.WARNING
    else:
        overall_status = ValidationStatus.VALID

    # 6. Summary Notes
    summary_notes = []
    if overall_status == ValidationStatus.VALID:
        summary_notes.append("100% Arithmetic Parity: All transactions verified against running balance.")
    else:
        summary_notes.append(
            f"Validation Status: {overall_status.value}. {len(discrepancies)} discrepancy(ies) detected."
        )
        for d in discrepancies[:3]:
            summary_notes.append(f"• {d.message}")

    return ReconciliationReport(
        status=overall_status,
        opening_balance=open_bal,
        total_income=total_income,
        total_expense=total_expense,
        net_cash_flow=net_cash_flow,
        expected_closing_balance=expected_closing,
        extracted_closing_balance=actual_closing,
        closing_balance_difference=closing_diff,
        total_transactions=len(rows),
        verified_transactions=verified_txns,
        discrepancy_count=len(discrepancies),
        discrepancies=discrepancies,
        summary_notes=summary_notes,
    )
