"""
Dynamic Financial Transaction Classifier and Counterparty Extraction Engine.

Classifies transactions into standard financial categories, isolates payment rails,
extracts counterparties from payment strings (UPI, NEFT, RTGS, IMPS, POS, ACH),
and dynamically infers own-account transfers from document metadata without hardcoding customer data.
"""
from __future__ import annotations
import re
from typing import Optional

# Generic payment rail patterns
_PAT_UPI = re.compile(r"\bUPI(?:/|\s+)([A-Z0-9\-_]+)?(?:/|\s+)?([A-Za-z0-9\.\-_@]+)?", re.IGNORECASE)
_PAT_NEFT = re.compile(r"\bNEFT[-/\s]([A-Z0-9]+)[-/\s]([A-Za-z0-9\s\.\-_]+)", re.IGNORECASE)
_PAT_IMPS = re.compile(r"\bIMPS[-/\s]([A-Z0-9]+)[-/\s]([A-Za-z0-9\s\.\-_]+)", re.IGNORECASE)
_PAT_RTGS = re.compile(r"\bRTGS[-/\s]([A-Z0-9]+)[-/\s]([A-Za-z0-9\s\.\-_]+)", re.IGNORECASE)
_PAT_POS = re.compile(r"\bPOS\s+([A-Za-z0-9\s\.\-_]+)", re.IGNORECASE)
_PAT_ACH = re.compile(r"\b(?:ACH|NACH)[-/\s]([A-Za-z0-9\s\.\-_]+)", re.IGNORECASE)

# Standard Category Patterns
_PAT_SALARY = re.compile(r"\b(?:salary|payroll|stipend|wages)\b", re.IGNORECASE)
_PAT_EMI = re.compile(r"\b(?:emi|loan\s*repay|nach|ach|hdb|bajaj|cholamandalam|shriram|muthoot|home\s*loan|car\s*loan)\b", re.IGNORECASE)
_PAT_LOAN_DISBURSEMENT = re.compile(r"\b(?:loan\s*disb|disbursement|loan\s*sanction|credit\s*facility)\b", re.IGNORECASE)
_PAT_ATM = re.compile(r"\b(?:atm|cash\s*wdl|nfs|matm|atw)\b", re.IGNORECASE)
_PAT_CASH_DEP = re.compile(r"\b(?:cash\s*dep|cdm|bna|by\s*cash)\b", re.IGNORECASE)
_PAT_CHARGES = re.compile(r"\b(?:charge|fee|sms\s*alert|annual\s*fee|penal|gst\s*on\s*charge|int\.coll|consolidated\s*charge)\b", re.IGNORECASE)
_PAT_INTEREST = re.compile(r"\b(?:interest|int\.pd|int\.cr)\b", re.IGNORECASE)
_PAT_UTILITY = re.compile(r"\b(?:electricity|telecom|airtel|jio|vodafone|bescom|tneb|water\s*bill|broadband|recharge)\b", re.IGNORECASE)
_PAT_TAX = re.compile(r"\b(?:income\s*tax|gst\s*payment|advance\s*tax|tds|challan)\b", re.IGNORECASE)


class FinancialClassifier:
    """Classifies financial transactions dynamically without hardcoded entity names."""

    @classmethod
    def classify(
        cls,
        narration: str,
        is_credit: bool,
        account_holder: str = "",
        account_no: str = "",
    ) -> tuple[str, str, str, bool, bool]:
        """
        Returns:
        (category, payment_mode, counterparty, is_own_account, is_emi)
        """
        if not narration:
            return "Uncategorized", "OTHER", "", False, False

        clean = narration.strip()
        upper = clean.upper()

        # 1. Determine Payment Mode and Counterparty
        payment_mode = "OTHER"
        counterparty = ""

        m_upi = _PAT_UPI.search(clean)
        if m_upi:
            payment_mode = "UPI"
            g1, g2 = m_upi.group(1) or "", m_upi.group(2) or ""
            # Usually g1 is VPA/Ref and g2 is name, or vice versa
            counterparty = g2 if (g2 and not g2.isdigit()) else g1
        elif _PAT_NEFT.search(clean):
            payment_mode = "NEFT"
            m = _PAT_NEFT.search(clean)
            counterparty = m.group(2).strip()
        elif _PAT_IMPS.search(clean):
            payment_mode = "IMPS"
            m = _PAT_IMPS.search(clean)
            counterparty = m.group(2).strip()
        elif _PAT_RTGS.search(clean):
            payment_mode = "RTGS"
            m = _PAT_RTGS.search(clean)
            counterparty = m.group(2).strip()
        elif _PAT_POS.search(clean):
            payment_mode = "POS"
            m = _PAT_POS.search(clean)
            counterparty = m.group(1).strip()
        elif _PAT_ACH.search(clean):
            payment_mode = "NACH"
            m = _PAT_ACH.search(clean)
            counterparty = m.group(1).strip()
        elif _PAT_ATM.search(clean):
            payment_mode = "ATM"
            counterparty = "ATM Cash"
        elif _PAT_CASH_DEP.search(clean):
            payment_mode = "CASH"
            counterparty = "Cash Deposit"
        elif "CHQ" in upper or "CHEQUE" in upper:
            payment_mode = "CHEQUE"
            counterparty = "Cheque Clearing"
        elif _PAT_CHARGES.search(clean):
            payment_mode = "BANK CHARGE"
            counterparty = "Bank Fees"

        # 2. Dynamic Own Account Check
        is_own_account = False
        self_keywords = ("SELF", "OWN ACCOUNT", "INTERNAL TRANSFER", "TRANSFER TO OWN", "TRF TO OWN")
        if any(kw in upper for kw in self_keywords):
            is_own_account = True
        elif account_no and len(account_no) >= 6 and account_no in upper:
            is_own_account = True
        elif account_holder:
            # Check for significant matching tokens (length >= 5) from account holder
            tokens = [t for t in re.findall(r"[A-Z0-9]+", account_holder.upper()) if len(t) >= 5]
            if tokens and any(t in upper for t in tokens):
                is_own_account = True

        # 3. Category & EMI Check
        category = "Uncategorized"
        is_emi = False

        if not is_credit and _PAT_EMI.search(clean):
            category = "EMI / Loan Payment"
            is_emi = True
        elif is_credit and _PAT_LOAN_DISBURSEMENT.search(clean):
            category = "Loan Disbursement"
        elif is_credit and _PAT_SALARY.search(clean):
            category = "Salary Credit"
        elif _PAT_CHARGES.search(clean):
            category = "Bank Charges & Tax"
        elif _PAT_INTEREST.search(clean):
            category = "Interest"
        elif _PAT_TAX.search(clean):
            category = "Tax Payment"
        elif _PAT_UTILITY.search(clean):
            category = "Utilities"
        elif payment_mode in ("CASH", "ATM"):
            category = "Cash / ATM"
        elif is_own_account:
            category = "Internal Transfer"
        elif is_credit:
            category = "Customer Receipt / Inflow"
        else:
            category = "Vendor / Expense Payment"

        if not counterparty:
            # Use first 3 words of narration as fallback counterparty
            counterparty = " ".join(clean.split()[:3])

        return category, payment_mode, counterparty.strip(" -/"), is_own_account, is_emi

