"""
Universal Adaptive Bank Statement Pipeline.

Master orchestrator for universal bank statement extraction:
- Adaptive header detection across bordered tables and spatial borderless text
- Intelligent OCR fallback for scanned pages
- Universal date and Decimal amount normalization
- Multi-line narration reconstruction across row and page boundaries
- Mathematical balance equation solving and debit/credit assignment resolution
- Dynamic financial categorization and own-account inference
- Transparent confidence scoring and validation audit trails
- Memory-safe incremental streaming
"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
import gc
import logging
import os
import re
from typing import Any, Callable, Optional

from app.services.adaptive_models import (
    ColumnRole,
    AmountMode,
    DetectedColumn,
    HeaderCandidate,
    NormalizedTransaction,
    DocumentMetadata,
    ReconciliationResult,
    ReconciliationStatus,
    ValidationStatus,
)
from app.services.financial_normalizer import (
    UniversalDateNormalizer,
    UniversalAmountNormalizer,
)
from app.services.adaptive_header_detector import AdaptiveHeaderDetector
from app.services.narration_reconstructor import (
    NarrationReconstructor,
    is_noise_or_summary_line,
)
from app.services.balance_reconciliation_engine import BalanceReconciliationEngine
from app.services.financial_classifier import FinancialClassifier
from app.services.extraction_confidence import ExtractionConfidenceEvaluator
from app.services.adaptive_ocr_service import AdaptiveOCRService
from app.services.pdf_extractor import (
    extract_pdf_document,
    extract_document_metadata,
    ExtractedDocument,
    ExtractedPage,
    ExtractedLine,
)

logger = logging.getLogger(__name__)


class BankStatementPipeline:
    """Production-grade pipeline executing adaptive extraction and reconciliation."""

    def __init__(self):
        self.date_normalizer = UniversalDateNormalizer(prefer_day_first=True)
        self.header_detector = AdaptiveHeaderDetector(max_pages_to_search=4)

    def process_document(
        self,
        file_path: str,
        file_name: str,
        password: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> dict[str, Any]:
        """
        Executes the universal extraction and reconciliation pipeline on a bank statement.
        Returns a rich summary dictionary 100% compatible with existing frontend & analytics.
        """
        if progress_callback:
            progress_callback(5, 100, f"Validating {file_name}...")

        # 1. Inspect and extract document structures
        doc = extract_pdf_document(
            file_path,
            max_pages=None,
            password=password,
            progress_callback=progress_callback,
        )

        if not doc.is_valid:
            raise ValueError(doc.error_message or "Failed to read PDF document")

        # 2. Extract Document Metadata
        meta_dict = extract_document_metadata(doc)
        metadata = self._parse_document_metadata(meta_dict)

        # 3. Check for dedicated text stream parser (e.g. Indian Bank text stream)
        # Preserve specialized high-speed stream parsers if document layout matches
        bank = metadata.bank_name.upper()
        if bank == "INDIAN BANK":
            from app.services.transaction_parser import parse_indian_bank_text_transactions, _IB_DATE_START
            has_ib_stream = any(
                _IB_DATE_START.match(l.text.strip())
                for p in doc.pages
                for l in p.transaction_lines
            )
            if has_ib_stream:
                if progress_callback:
                    progress_callback(50, 100, "Processing stream layout...")
                legacy_txns = parse_indian_bank_text_transactions(doc, file_name, meta_dict)
                return self._wrap_legacy_transactions(legacy_txns, file_path, file_name, metadata)

        # 4. Feed document date tokens to ambiguity resolver
        for p in doc.pages[:3]:
            for line in p.lines:
                for word in line.words:
                    self.date_normalizer.feed_evidence(word.text)

        # 5. Extract transactions page by page
        raw_txns: list[NormalizedTransaction] = []
        active_header: Optional[HeaderCandidate] = None
        reconstructor = NarrationReconstructor()
        current_txn: Optional[NormalizedTransaction] = None

        total_pages = len(doc.pages)
        for page_idx, page in enumerate(doc.pages):
            if progress_callback:
                prog = 20 + int((page_idx / max(1, total_pages)) * 60)
                progress_callback(prog, 100, f"Extracting page {page_idx + 1} of {total_pages}...")

            # Check if page is scanned or lacks text
            if page.is_scanned or page.character_count < 80:
                if AdaptiveOCRService.is_available():
                    try:
                        import fitz
                        fitz_doc = fitz.open(file_path)
                        if password:
                            fitz_doc.authenticate(password)
                        fitz_page = fitz_doc[page_idx]
                        ocr_page = AdaptiveOCRService.ocr_page(fitz_page, page_idx + 1)
                        fitz_doc.close()
                        page = ocr_page
                    except Exception as ocr_err:
                        logger.warning("OCR page extraction failed: %s", ocr_err)

            # Discover or update header
            page_header = None
            if page.raw_tables:
                for tbl in page.raw_tables:
                    page_header = self.header_detector.detect_header_from_table(tbl, page.page_number)
                    if page_header:
                        break

            if not page_header and page.lines:
                page_header = self.header_detector.detect_header_from_lines(page.lines, page.page_number)

            if page_header:
                active_header = page_header
            elif not active_header and self.header_detector.active_header:
                active_header = self.header_detector.active_header

            # Extract from table grid if present and mapped
            page_txns: list[NormalizedTransaction] = []
            if page.raw_tables and active_header:
                page_txns = self._extract_from_tables(
                    page.raw_tables,
                    active_header,
                    page.page_number,
                    metadata,
                )

            # Fallback to spatial line extraction
            if not page_txns and page.lines:
                page_txns = self._extract_from_spatial_lines(
                    page.lines,
                    active_header,
                    page.page_number,
                    metadata,
                )

            raw_txns.extend(page_txns)

            # Promptly free page objects to maintain low RAM usage
            try:
                page.raw_tables.clear()
                page.lines.clear()
                page.transaction_lines.clear()
                page.header_lines.clear()
                page.footer_lines.clear()
                page.raw_text = ""
            except Exception:
                pass

            if (page_idx + 1) % 15 == 0:
                gc.collect()

        if progress_callback:
            progress_callback(85, 100, "Reconciling transactions & verifying financial integrity...")

        # 6. Fallback if no transactions extracted: try generic date-amount line scanner
        if not raw_txns:
            raw_txns = self._fallback_date_amount_scanner(doc, metadata)

        if not raw_txns:
            return self._build_empty_result(file_path, file_name, metadata)

        # 7. Deduplicate True Duplicates Conservatively
        deduped_txns = self._deduplicate_conservatively(raw_txns)

        # 8. Detect & Normalize Chronological Direction
        ascending_txns = self._ensure_ascending_order(deduped_txns)

        # Assign serial numbers sequentially
        for s_idx, t in enumerate(ascending_txns, start=1):
            t.s_no = s_idx

        # 9. Solve Balance Continuity & Reconcile
        reconciliation = BalanceReconciliationEngine.reconcile(
            ascending_txns,
            statement_opening_balance=metadata.opening_balance,
            statement_closing_balance=metadata.closing_balance,
        )

        # 10. Classify Financial Categories & Evaluate Confidence
        for t in ascending_txns:
            is_cr = (t.credit is not None and t.credit > Decimal("0"))
            cat, pmode, cp, is_own, is_emi = FinancialClassifier.classify(
                t.description,
                is_credit=is_cr,
                account_holder=metadata.account_holder,
                account_no=metadata.account_no,
            )
            t.category = cat
            t.payment_mode = pmode
            t.counterparty = cp
            t.is_own_account = is_own
            t.is_emi = is_emi

            ExtractionConfidenceEvaluator.evaluate_transaction(
                t,
                header_confidence=active_header.confidence if active_header else 0.7,
            )

        quality_score = ExtractionConfidenceEvaluator.evaluate_statement_quality(
            ascending_txns, reconciliation
        )

        # 11. Compute Authenticity
        from app.services.authenticity_service import check_document_authenticity
        auth_res = check_document_authenticity(
            file_path,
            parsed_transactions=[t.to_legacy_dict(file_name) for t in ascending_txns],
            meta={
                "opening_balance": float(reconciliation.opening_balance),
                "closing_balance": float(reconciliation.computed_closing_balance),
                "statement_summary": metadata.statement_summary,
                "footer_total_credit": float(reconciliation.total_credit),
                "footer_total_debit": float(reconciliation.total_debit),
            },
            is_password_protected=bool(password),
        )

        if progress_callback:
            progress_callback(100, 100, "Analysis complete.")

        # 12. Convert to application dictionary
        legacy_rows = [t.to_legacy_dict(file_name) for t in ascending_txns]
        balances = [float(t.balance) for t in ascending_txns if t.balance is not None]

        return {
            "transactions_found": len(legacy_rows),
            "total_credits": float(reconciliation.total_credit),
            "total_debits": float(reconciliation.total_debit),
            "closing_balance": float(reconciliation.computed_closing_balance),
            "net_cash_flow": float(reconciliation.net_cash_flow),
            "opening_balance": float(reconciliation.opening_balance),
            "max_balance": round(max(balances), 2) if balances else float(reconciliation.opening_balance),
            "min_balance": round(min(balances), 2) if balances else float(reconciliation.opening_balance),
            "avg_balance": round(sum(balances) / len(balances), 2) if balances else float(reconciliation.opening_balance),
            "transactions": legacy_rows,
            "file_name": file_name,
            "account_holder": metadata.account_holder or None,
            "bank_name": metadata.bank_name if metadata.bank_name != "BANK" else None,
            "account_no": metadata.account_no or None,
            "account_type": metadata.account_type or None,
            "statement_summary": metadata.statement_summary,
            "statement_period": metadata.statement_period,
            "statement_opening_balance": float(metadata.opening_balance) if metadata.opening_balance is not None else None,
            "statement_closing_balance": float(metadata.closing_balance) if metadata.closing_balance is not None else None,
            "authenticity": auth_res,
            "reconciliation": reconciliation.to_dict(),
            "extraction_quality_score": quality_score,
            "has_data": len(legacy_rows) > 0,
        }

    def _extract_from_tables(
        self,
        tables: list[list[list[Optional[str]]]],
        header: HeaderCandidate,
        page_number: int,
        metadata: DocumentMetadata,
    ) -> list[NormalizedTransaction]:
        """Parses rows from extracted 2D table matrices using the detected header layout."""
        results: list[NormalizedTransaction] = []
        col_role_map: dict[ColumnRole, int] = {c.role: c.col_idx for c in header.columns if c.col_idx >= 0}

        date_col = col_role_map.get(ColumnRole.DATE, col_role_map.get(ColumnRole.VALUE_DATE))
        val_date_col = col_role_map.get(ColumnRole.VALUE_DATE)
        desc_col = col_role_map.get(ColumnRole.DESCRIPTION)
        ref_col = col_role_map.get(ColumnRole.REFERENCE, col_role_map.get(ColumnRole.CHEQUE_NO))
        debit_col = col_role_map.get(ColumnRole.DEBIT)
        credit_col = col_role_map.get(ColumnRole.CREDIT)
        amount_col = col_role_map.get(ColumnRole.AMOUNT)
        balance_col = col_role_map.get(ColumnRole.BALANCE)
        dr_cr_col = col_role_map.get(ColumnRole.DR_CR)

        for tbl in tables:
            for r_idx, row in enumerate(tbl):
                if not row or not any(row):
                    continue

                row_str = " ".join(str(c or "").strip() for c in row if c)
                if is_noise_or_summary_line(row_str):
                    continue

                # 1. Parse Date
                date_val = None
                is_ambig = False
                date_conf = 1.0
                if date_col is not None and date_col < len(row):
                    raw_d = str(row[date_col] or "").strip()
                    date_val, is_ambig, date_conf = self.date_normalizer.parse(raw_d)

                if date_val is None and val_date_col is not None and val_date_col < len(row):
                    raw_vd = str(row[val_date_col] or "").strip()
                    date_val, is_ambig, date_conf = self.date_normalizer.parse(raw_vd)

                # 2. Parse Amounts
                debit_amt: Optional[Decimal] = None
                credit_amt: Optional[Decimal] = None
                balance_amt: Optional[Decimal] = None

                # Debit / Credit separate columns
                if debit_col is not None and debit_col < len(row):
                    raw_dr = str(row[debit_col] or "").strip()
                    amt, _, _, _ = UniversalAmountNormalizer.parse(raw_dr)
                    if amt is not None and amt > Decimal("0"):
                        debit_amt = amt

                if credit_col is not None and credit_col < len(row):
                    raw_cr = str(row[credit_col] or "").strip()
                    amt, _, _, _ = UniversalAmountNormalizer.parse(raw_cr)
                    if amt is not None and amt > Decimal("0"):
                        credit_amt = amt

                # Single amount column
                if amount_col is not None and amount_col < len(row) and debit_amt is None and credit_amt is None:
                    raw_amt = str(row[amount_col] or "").strip()
                    indicator = None
                    if dr_cr_col is not None and dr_cr_col < len(row):
                        raw_ind = str(row[dr_cr_col] or "").strip().upper()
                        if "DR" in raw_ind:
                            indicator = "DR"
                        elif "CR" in raw_ind:
                            indicator = "CR"

                    amt, direction, _, _ = UniversalAmountNormalizer.parse(raw_amt, default_direction=indicator)
                    if amt is not None and amt > Decimal("0"):
                        if direction == "CR":
                            credit_amt = amt
                        else:
                            debit_amt = amt

                # Balance
                if balance_col is not None and balance_col < len(row):
                    raw_bal = str(row[balance_col] or "").strip()
                    bal, _, _, _ = UniversalAmountNormalizer.parse(raw_bal)
                    balance_amt = bal

                # Check if this row is a valid transaction anchor
                has_financial_activity = (debit_amt is not None or credit_amt is not None)
                if date_val is not None and has_financial_activity:
                    # Description
                    desc = "Transaction"
                    raw_desc = ""
                    if desc_col is not None and desc_col < len(row):
                        raw_desc = str(row[desc_col] or "").strip()
                        desc = raw_desc or "Transaction"

                    ref = ""
                    if ref_col is not None and ref_col < len(row):
                        ref = str(row[ref_col] or "").strip()

                    t_type = "INCOME" if (credit_amt and credit_amt > 0) else ("EXPENSE" if (debit_amt and debit_amt > 0) else "UNCERTAIN")

                    txn = NormalizedTransaction(
                        s_no=len(results) + 1,
                        transaction_date=date_val,
                        description=desc,
                        raw_description=raw_desc,
                        debit=debit_amt,
                        credit=credit_amt,
                        balance=balance_amt,
                        reference_number=ref,
                        cheque_number=ref,
                        currency=metadata.currency,
                        transaction_type=t_type,
                        source_page=page_number,
                        extraction_method="TABLE",
                        raw_text=row_str,
                    )
                    results.append(txn)
                elif results and desc_col is not None and desc_col < len(row):
                    # Continuation row: append to previous transaction description
                    continuation_text = str(row[desc_col] or "").strip()
                    if continuation_text and not is_noise_or_summary_line(continuation_text):
                        prev = results[-1]
                        prev.description = f"{prev.description} {continuation_text}".strip()
                        prev.raw_description = f"{prev.raw_description} \n {continuation_text}".strip()

        return results

    def _extract_from_spatial_lines(
        self,
        lines: list[ExtractedLine],
        header: Optional[HeaderCandidate],
        page_number: int,
        metadata: DocumentMetadata,
    ) -> list[NormalizedTransaction]:
        """Extracts transactions from borderless text lines based on coordinate spans."""
        results: list[NormalizedTransaction] = []
        if not lines:
            return results

        # Date pattern for transaction anchors
        date_re = re.compile(
            r"\b(\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}[-/\.][A-Za-z]{3}[-/\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4})\b"
        )
        # Amount pattern
        amt_re = re.compile(r"\b\d{1,3}(?:,\d{2,3})*(?:\.\d{2})\b")

        deb_col = next((c for c in header.columns if c.role == ColumnRole.DEBIT), None) if header else None
        cr_col = next((c for c in header.columns if c.role == ColumnRole.CREDIT), None) if header else None
        bal_col = next((c for c in header.columns if c.role == ColumnRole.BALANCE), None) if header else None

        for line in lines:
            text = line.text.strip()
            if not text or is_noise_or_summary_line(text):
                continue

            d_match = date_re.search(text)
            if d_match and d_match.start() < 30:
                # Potential start of new transaction
                raw_d = d_match.group(1)
                parsed_d, _, _ = self.date_normalizer.parse(raw_d)

                if parsed_d:
                    # Find all amounts on this line
                    amounts = []
                    for m in amt_re.finditer(text):
                        amt_str = m.group(0)
                        amt, _, _, _ = UniversalAmountNormalizer.parse(amt_str)
                        if amt is not None:
                            amounts.append((amt, m.start()))

                    if amounts:
                        # Extract description (text between date and first amount)
                        first_amt_pos = amounts[0][1]
                        desc_part = text[d_match.end():first_amt_pos].strip()

                        # Check for Opening Balance b/f row
                        is_opening_bal_line = bool(re.search(r"\b(?:opening\s*bal|b/f|brought\s*forward)\b", desc_part or text, re.IGNORECASE))
                        if is_opening_bal_line:
                            if amounts:
                                op_candidate = amounts[-1][0]
                                if metadata.opening_balance is None:
                                    metadata.opening_balance = op_candidate
                            continue

                        # Look up last known balance from previous transactions or opening balance
                        last_known_balance = None
                        for prev_t in reversed(results):
                            if prev_t.balance is not None:
                                last_known_balance = prev_t.balance
                                break
                        if last_known_balance is None and metadata.opening_balance is not None:
                            last_known_balance = metadata.opening_balance

                        # Determine Debit, Credit, Balance from extracted amounts
                        debit_val = None
                        credit_val = None
                        bal_val = None

                        if len(amounts) >= 3:
                            if cr_col and deb_col and cr_col.center_x < deb_col.center_x:
                                credit_val = amounts[0][0]
                                debit_val = amounts[1][0]
                            else:
                                debit_val = amounts[0][0]
                                credit_val = amounts[1][0]
                            bal_val = amounts[2][0]
                        elif len(amounts) == 2:
                            amt_candidate = amounts[0][0]
                            bal_candidate = amounts[1][0]
                            bal_val = bal_candidate

                            # 1. Coordinate check if header has column positions
                            amt_word_x = None
                            if line.words:
                                amt_str_digits = str(amt_candidate).replace(".", "")
                                for w in line.words:
                                    clean_w = w.text.replace(",", "").replace(".", "")
                                    if amt_str_digits in clean_w:
                                        amt_word_x = w.x0
                                        break

                            resolved_dir = None
                            if amt_word_x is not None and deb_col and cr_col and deb_col.x0 > 0 and cr_col.x0 > 0:
                                dist_dr = abs(amt_word_x - deb_col.center_x)
                                dist_cr = abs(amt_word_x - cr_col.center_x)
                                if abs(dist_dr - dist_cr) > 15.0:
                                    resolved_dir = "CR" if dist_cr < dist_dr else "DR"

                            # 2. Mathematical balance movement check
                            if resolved_dir is None and last_known_balance is not None and bal_candidate is not None:
                                if bal_candidate > last_known_balance:
                                    resolved_dir = "CR"
                                elif bal_candidate < last_known_balance:
                                    resolved_dir = "DR"

                            # 3. Text keywords
                            if resolved_dir is None:
                                if any(k in text.upper() for k in ("CR", "CREDIT", "DEPOSIT", "INWARD", "+")):
                                    resolved_dir = "CR"
                                else:
                                    resolved_dir = "DR"

                            if resolved_dir == "CR":
                                credit_val = amt_candidate
                            else:
                                debit_val = amt_candidate
                        elif len(amounts) == 1:
                            amt_candidate = amounts[0][0]
                            resolved_dir = None
                            if any(k in text.upper() for k in ("CR", "CREDIT", "DEPOSIT", "INWARD", "+")):
                                resolved_dir = "CR"
                            elif any(k in text.upper() for k in ("DR", "DEBIT", "WITHDRAWAL", "-")):
                                resolved_dir = "DR"
                            else:
                                resolved_dir = "DR"

                            if resolved_dir == "CR":
                                credit_val = amt_candidate
                            else:
                                debit_val = amt_candidate

                        t_type = "INCOME" if (credit_val and credit_val > 0) else "EXPENSE"

                        txn = NormalizedTransaction(
                            s_no=len(results) + 1,
                            transaction_date=parsed_d,
                            description=desc_part or "Transaction",
                            raw_description=desc_part,
                            debit=debit_val,
                            credit=credit_val,
                            balance=bal_val,
                            currency=metadata.currency,
                            transaction_type=t_type,
                            source_page=page_number,
                            extraction_method="SPATIAL",
                            raw_text=text,
                        )
                        results.append(txn)
                        continue

            # If not a new anchor and we have an active transaction, treat as description continuation
            if results and len(text) > 2 and not is_noise_or_summary_line(text):
                prev = results[-1]
                prev.description = f"{prev.description} {text}".strip()
                prev.raw_description = f"{prev.raw_description} \n {text}".strip()

        return results

    def _fallback_date_amount_scanner(
        self,
        doc: ExtractedDocument,
        metadata: DocumentMetadata,
    ) -> list[NormalizedTransaction]:
        """Ultimate fallback: scans all physical lines for date + amount combinations."""
        txns: list[NormalizedTransaction] = []
        for p in doc.pages:
            txns.extend(self._extract_from_spatial_lines(p.lines, None, p.page_number, metadata))
        return txns

    def _deduplicate_conservatively(
        self,
        txns: list[NormalizedTransaction],
    ) -> list[NormalizedTransaction]:
        """Deduplicates true repeated extractions without deleting valid repeated transactions."""
        deduped = []
        seen = set()
        for t in txns:
            # Key includes page, date, exact debit, exact credit, balance, and description prefix
            d_key = (
                t.source_page,
                t.transaction_date,
                t.debit,
                t.credit,
                t.balance,
                t.description[:20].lower(),
            )
            if d_key in seen:
                continue
            seen.add(d_key)
            deduped.append(t)
        return deduped

    def _ensure_ascending_order(
        self,
        txns: list[NormalizedTransaction],
    ) -> list[NormalizedTransaction]:
        """Ensures transactions are sorted chronologically ascending."""
        if len(txns) <= 1:
            return txns

        # Check if first date > last date
        if txns[0].transaction_date and txns[-1].transaction_date:
            if txns[0].transaction_date > txns[-1].transaction_date:
                txns.reverse()

        txns.sort(key=lambda x: x.transaction_date or date.min)
        return txns

    def _parse_document_metadata(self, meta_dict: dict[str, Any]) -> DocumentMetadata:
        """Constructs DocumentMetadata with Decimal conversions from raw metadata dictionary."""
        op_bal, _, _, _ = UniversalAmountNormalizer.parse(meta_dict.get("opening_balance"))
        cl_bal, _, _, _ = UniversalAmountNormalizer.parse(meta_dict.get("closing_balance"))
        tot_cr, _, _, _ = UniversalAmountNormalizer.parse(meta_dict.get("footer_total_credit"))
        tot_dr, _, _, _ = UniversalAmountNormalizer.parse(meta_dict.get("footer_total_debit"))

        return DocumentMetadata(
            bank_name=meta_dict.get("bank_name", "BANK"),
            account_holder=meta_dict.get("account_holder", ""),
            account_no=meta_dict.get("account_no", ""),
            masked_account_no=meta_dict.get("masked_account_no", ""),
            account_type=meta_dict.get("account_type", "Savings"),
            statement_period=meta_dict.get("statement_period", ""),
            opening_balance=op_bal,
            closing_balance=cl_bal,
            currency=meta_dict.get("currency", "INR"),
            footer_total_credit=tot_cr,
            footer_total_debit=tot_dr,
            statement_summary=meta_dict.get("statement_summary"),
        )

    def _wrap_legacy_transactions(
        self,
        legacy_txns: list[dict[str, Any]],
        file_path: str,
        file_name: str,
        metadata: DocumentMetadata,
    ) -> dict[str, Any]:
        """Adapts legacy stream parser results into the universal output structure."""
        tot_cr = round(sum(float(r.get("credit") or 0.0) for r in legacy_txns), 2)
        tot_dr = round(sum(float(r.get("debit") or 0.0) for r in legacy_txns), 2)
        op_bal = float(metadata.opening_balance) if metadata.opening_balance is not None else 0.0
        cl_bal = legacy_txns[-1]["balance"] if legacy_txns and legacy_txns[-1].get("balance") is not None else op_bal

        balances = [r["balance"] for r in legacy_txns if r.get("balance") is not None]

        from app.services.authenticity_service import check_document_authenticity
        auth_res = check_document_authenticity(
            file_path,
            parsed_transactions=legacy_txns,
            meta={"opening_balance": op_bal, "closing_balance": cl_bal},
        )

        return {
            "transactions_found": len(legacy_txns),
            "total_credits": tot_cr,
            "total_debits": tot_dr,
            "closing_balance": cl_bal,
            "net_cash_flow": round(tot_cr - tot_dr, 2),
            "opening_balance": op_bal,
            "max_balance": round(max(balances), 2) if balances else op_bal,
            "min_balance": round(min(balances), 2) if balances else op_bal,
            "avg_balance": round(sum(balances) / len(balances), 2) if balances else op_bal,
            "transactions": legacy_txns,
            "file_name": file_name,
            "account_holder": metadata.account_holder or None,
            "bank_name": metadata.bank_name if metadata.bank_name != "BANK" else None,
            "account_no": metadata.account_no or None,
            "account_type": metadata.account_type or None,
            "statement_summary": metadata.statement_summary,
            "statement_period": metadata.statement_period,
            "authenticity": auth_res,
            "has_data": len(legacy_txns) > 0,
        }

    def _build_empty_result(
        self,
        file_path: str,
        file_name: str,
        metadata: DocumentMetadata,
    ) -> dict[str, Any]:
        """Constructs safe empty result structure when no rows could be parsed."""
        from app.services.authenticity_service import check_document_authenticity
        auth_res = check_document_authenticity(file_path)

        size_kb = round(os.path.getsize(file_path) / 1024, 2) if os.path.exists(file_path) else 0
        return {
            "transactions_found": 0,
            "total_credits": 0.0,
            "total_debits": 0.0,
            "closing_balance": 0.0,
            "net_cash_flow": 0.0,
            "opening_balance": 0.0,
            "max_balance": 0.0,
            "min_balance": 0.0,
            "avg_balance": 0.0,
            "transactions": [],
            "file_name": file_name,
            "account_holder": metadata.account_holder or None,
            "bank_name": metadata.bank_name if metadata.bank_name != "BANK" else None,
            "account_no": metadata.account_no or None,
            "account_type": metadata.account_type or None,
            "statement_summary": metadata.statement_summary,
            "statement_period": metadata.statement_period,
            "authenticity": auth_res,
            "note": f"File parsed ({size_kb} KB). No transaction rows detected.",
            "has_data": False,
        }
