"""
Typed domain models for the Universal Adaptive Bank Statement Extraction Engine.
Defines rich data structures for detected columns, header candidates, normalized transactions,
reconciliation results, confidence scores, and pipeline outcomes.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class ColumnRole(str, Enum):
    DATE = "DATE"
    VALUE_DATE = "VALUE_DATE"
    DESCRIPTION = "DESCRIPTION"
    REFERENCE = "REFERENCE"
    CHEQUE_NO = "CHEQUE_NO"
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    AMOUNT = "AMOUNT"
    BALANCE = "BALANCE"
    DR_CR = "DR_CR"
    TRANSACTION_ID = "TRANSACTION_ID"
    SERIAL_NO = "SERIAL_NO"
    UNKNOWN = "UNKNOWN"


class AmountMode(str, Enum):
    SEPARATE_DR_CR = "SEPARATE_DR_CR"
    SINGLE_AMOUNT_WITH_INDICATOR = "SINGLE_AMOUNT_WITH_INDICATOR"
    SIGNED_AMOUNT = "SIGNED_AMOUNT"
    UNKNOWN = "UNKNOWN"


class LayoutType(str, Enum):
    BORDERED_TABLE = "BORDERED_TABLE"
    BORDERLESS_SPATIAL = "BORDERLESS_SPATIAL"
    TEXT_STREAM = "TEXT_STREAM"
    OCR_RECONSTRUCTED = "OCR_RECONSTRUCTED"
    UNKNOWN = "UNKNOWN"


class ValidationStatus(str, Enum):
    VALID = "VALID"
    WARNING = "WARNING"
    SUSPICIOUS = "SUSPICIOUS"
    ERROR = "ERROR"


class ReconciliationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_VERIFIED = "NOT_VERIFIED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class DetectedColumn:
    role: ColumnRole
    header_name: str
    x0: float
    x1: float
    center_x: float = 0.0
    col_idx: int = -1
    confidence: float = 1.0

    def __post_init__(self):
        if not self.center_x:
            self.center_x = (self.x0 + self.x1) / 2.0


@dataclass
class HeaderCandidate:
    page_number: int
    y_top: float
    y_bottom: float
    columns: list[DetectedColumn]
    amount_mode: AmountMode
    raw_header_text: str
    semantic_score: float
    confidence: float = 1.0

    @property
    def has_date(self) -> bool:
        return any(c.role in (ColumnRole.DATE, ColumnRole.VALUE_DATE) for c in self.columns)

    @property
    def has_amount(self) -> bool:
        return any(c.role in (ColumnRole.DEBIT, ColumnRole.CREDIT, ColumnRole.AMOUNT) for c in self.columns)

    @property
    def has_balance(self) -> bool:
        return any(c.role == ColumnRole.BALANCE for c in self.columns)

    @property
    def has_description(self) -> bool:
        return any(c.role == ColumnRole.DESCRIPTION for c in self.columns)


@dataclass
class NormalizedTransaction:
    s_no: int
    transaction_date: date
    description: str
    raw_description: str
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    balance: Optional[Decimal] = None
    value_date: Optional[date] = None
    reference_number: str = ""
    cheque_number: str = ""
    currency: str = "INR"
    transaction_type: str = "UNCERTAIN"  # INCOME, EXPENSE, TRANSFER, UNCERTAIN
    category: str = "Uncategorized"
    counterparty: str = ""
    payment_mode: str = "OTHER"
    is_own_account: bool = False
    is_emi: bool = False
    source_page: int = 1
    extraction_method: str = "TABLE"
    confidence_score: float = 1.0
    validation_status: ValidationStatus = ValidationStatus.VALID
    validation_warnings: list[str] = field(default_factory=list)
    raw_tokens: list[str] = field(default_factory=list)
    raw_text: str = ""

    def to_legacy_dict(self, file_name: str = "") -> dict[str, Any]:
        """Convert to existing application dictionary format for 100% backward compatibility."""
        dir_val = "CR" if (self.credit and self.credit > Decimal("0")) else ("DR" if (self.debit and self.debit > Decimal("0")) else "")
        v_date_str = self.value_date.strftime("%d/%m/%Y") if self.value_date else (self.transaction_date.strftime("%d/%m/%Y") if self.transaction_date else "")

        return {
            "s_no": self.s_no,
            "sno": self.s_no,
            "date": self.transaction_date,
            "value_date": v_date_str,
            "description": self.description or "Transaction",
            "raw_description": self.raw_description,
            "reference": self.reference_number,
            "chq_no": self.cheque_number or self.reference_number,
            "direction": dir_val,
            "debit": float(self.debit) if self.debit is not None and self.debit > Decimal("0") else (0.0 if dir_val == "DR" else None),
            "credit": float(self.credit) if self.credit is not None and self.credit > Decimal("0") else (0.0 if dir_val == "CR" else None),
            "balance": float(self.balance) if self.balance is not None else None,
            "computed_balance": float(self.balance) if self.balance is not None else None,
            "transaction_type": self.transaction_type,
            "category": self.category,
            "counterparty": self.counterparty,
            "payment_mode": self.payment_mode,
            "tag": self.category,
            "is_own_account": self.is_own_account,
            "is_emi": self.is_emi,
            "source_page": self.source_page,
            "extraction_method": self.extraction_method,
            "confidence_score": round(self.confidence_score, 2),
            "validation_status": self.validation_status.value,
            "validation_warnings": list(self.validation_warnings),
            "raw_text": self.raw_text,
            "is_uncertain": self.confidence_score < 0.7 or self.validation_status in (ValidationStatus.WARNING, ValidationStatus.SUSPICIOUS, ValidationStatus.ERROR),
            "uncertain_reason": "; ".join(self.validation_warnings) if self.validation_warnings else "",
            "file_name": file_name,
        }


@dataclass
class DocumentMetadata:
    bank_name: str = "BANK"
    account_holder: str = ""
    account_no: str = ""
    masked_account_no: str = ""
    account_type: str = "Savings"
    statement_period: str = ""
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    currency: str = "INR"
    footer_total_credit: Optional[Decimal] = None
    footer_total_debit: Optional[Decimal] = None
    statement_summary: Optional[dict[str, Any]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@dataclass
class ReconciliationResult:
    status: ReconciliationStatus
    opening_balance: Decimal
    total_credit: Decimal
    total_debit: Decimal
    net_cash_flow: Decimal
    computed_closing_balance: Decimal
    stated_closing_balance: Optional[Decimal]
    closing_difference: Decimal
    total_transactions: int
    verified_transactions: int
    mismatched_transactions: int
    balance_mismatches: list[dict[str, Any]] = field(default_factory=list)
    failure_reasons: list[str] = field(default_factory=list)
    summary_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "opening_balance": float(self.opening_balance),
            "total_credit": float(self.total_credit),
            "total_debit": float(self.total_debit),
            "net_cash_flow": float(self.net_cash_flow),
            "expected_closing_balance": float(self.computed_closing_balance),
            "computed_closing_balance": float(self.computed_closing_balance),
            "stated_closing_balance": float(self.stated_closing_balance) if self.stated_closing_balance is not None else None,
            "extracted_closing_balance": float(self.stated_closing_balance) if self.stated_closing_balance is not None else None,
            "closing_balance_difference": float(self.closing_difference),
            "total_transactions": self.total_transactions,
            "verified_transactions": self.verified_transactions,
            "mismatched_transactions": self.mismatched_transactions,
            "balance_mismatches": self.balance_mismatches,
            "discrepancies": self.balance_mismatches,
            "failure_reasons": self.failure_reasons,
            "summary_notes": self.summary_notes,
            "is_verified": self.status == ReconciliationStatus.PASS,
        }

