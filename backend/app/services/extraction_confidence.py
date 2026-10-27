"""
Transparent Confidence Scoring and Review Workflow Engine.

Calculates multi-dimensional extraction confidence scores for headers, columns,
dates, amounts, transaction boundaries, and balance continuity.
Identifies and flags uncertain transactions for manual review.
"""
from __future__ import annotations
from typing import Optional

from app.services.adaptive_models import (
    NormalizedTransaction,
    ValidationStatus,
    ReconciliationResult,
    ReconciliationStatus,
)


class ExtractionConfidenceEvaluator:
    """Computes transparent, evidence-based confidence metrics for extracted statement data."""

    @classmethod
    def evaluate_transaction(
        cls,
        txn: NormalizedTransaction,
        date_confidence: float = 1.0,
        amount_confidence: float = 1.0,
        header_confidence: float = 1.0,
    ) -> float:
        """
        Calculates a composite confidence score (0.0 to 1.0) based on:
        - Date validity & ambiguity (25%)
        - Amount precision & direction (30%)
        - Narration length & completeness (20%)
        - Header detection strength (15%)
        - Balance continuity match (10%)
        """
        score = 0.0

        # 1. Date component (25%)
        if txn.transaction_date:
            score += 0.25 * min(1.0, max(0.0, date_confidence))

        # 2. Amount component (30%)
        has_amt = (txn.debit is not None and txn.debit > 0) or (txn.credit is not None and txn.credit > 0)
        if has_amt:
            score += 0.30 * min(1.0, max(0.0, amount_confidence))

        # 3. Description component (20%)
        desc = (txn.description or "").strip()
        if len(desc) >= 8:
            score += 0.20
        elif len(desc) >= 3:
            score += 0.10

        # 4. Header confidence (15%)
        score += 0.15 * min(1.0, max(0.0, header_confidence))

        # 5. Balance continuity (10%)
        if txn.validation_status == ValidationStatus.VALID:
            score += 0.10
        elif txn.validation_status == ValidationStatus.WARNING:
            score += 0.04

        final_score = round(min(1.0, max(0.0, score)), 2)
        txn.confidence_score = final_score

        if final_score < 0.70:
            if "Low extraction confidence" not in txn.validation_warnings:
                txn.validation_warnings.append(f"Low extraction confidence ({final_score:.2f})")

        return final_score

    @classmethod
    def evaluate_statement_quality(
        cls,
        transactions: list[NormalizedTransaction],
        reconciliation: ReconciliationResult,
    ) -> float:
        """Computes statement-level extraction quality score (0.0 to 100.0)."""
        if not transactions:
            return 0.0

        avg_txn_conf = sum(t.confidence_score for t in transactions) / len(transactions)

        rec_factor = 1.0
        if reconciliation.status == ReconciliationStatus.PASS:
            rec_factor = 1.0
        elif reconciliation.status == ReconciliationStatus.WARNING:
            rec_factor = 0.85
        elif reconciliation.status == ReconciliationStatus.FAIL:
            rec_factor = 0.60
        else:
            rec_factor = 0.70

        quality = (avg_txn_conf * 0.7 + rec_factor * 0.3) * 100.0
        return round(min(100.0, max(0.0, quality)), 1)

