"""
Adaptive Semantic Header and Column Detection Engine.

Dynamically locates statement table headers without rigid row limits or bank-specific templates.
Clusters words by spatial coordinates (x0, x1, top, bottom), scores header candidates using
fuzzy semantic matching, determines separate vs unified amount modes, and tracks column boundaries.
"""
from __future__ import annotations
import re
from typing import Any, Optional

from app.services.adaptive_models import (
    ColumnRole,
    AmountMode,
    DetectedColumn,
    HeaderCandidate,
)

# Semantic dictionaries mapping standard aliases to ColumnRoles
ROLE_PATTERNS: dict[ColumnRole, list[str]] = {
    ColumnRole.DATE: [
        r"^date$", r"^txn\s*date$", r"^transaction\s*date$", r"^trans\s*date$",
        r"^posting\s*date$", r"^post\s*date$", r"^entry\s*date$", r"^booking\s*date$",
        r"^value\s*date$",
    ],
    ColumnRole.VALUE_DATE: [
        r"^value\s*date$", r"^val\s*date$", r"^effective\s*date$",
    ],
    ColumnRole.DESCRIPTION: [
        r"^description$", r"^narration$", r"^particulars$", r"^details$",
        r"^transaction\s*details$", r"^remarks$", r"^transaction\s*particulars$",
        r"^narrative$", r"^desc$", r"^tran\s*particulars$",
    ],
    ColumnRole.REFERENCE: [
        r"^ref(?:\s*no\.?|\s*number)?$", r"^reference(?:\s*no\.?|\s*number)?$",
        r"^utr(?:\s*no\.?)?$", r"^cheque(?:\s*no\.?|\s*number)?$",
        r"^chq(?:\s*no\.?|\s*number)?$", r"^tran(?:saction)?\s*id$",
        r"^instrument(?:\s*no\.?)?$", r"^chk\s*no$",
    ],
    ColumnRole.CHEQUE_NO: [
        r"^cheque(?:\s*no\.?|\s*number)?$", r"^chq(?:\s*no\.?|\s*number)?$",
        r"^chk\s*no$", r"^instrument(?:\s*no\.?)?$",
    ],
    ColumnRole.DEBIT: [
        r"^debit(?:\s*\(?inr\)?)?$", r"^withdrawal(?:\s*\(?inr\)?)?$",
        r"^dr$", r"^dr\s*amount$", r"^debit\s*amount$", r"^withdrawals?$",
        r"^withdrawal\s*amt$", r"^debit\s*amt$",
    ],
    ColumnRole.CREDIT: [
        r"^credit(?:\s*\(?inr\)?)?$", r"^deposit(?:\s*\(?inr\)?)?$",
        r"^cr$", r"^cr\s*amount$", r"^credit\s*amount$", r"^deposits?$",
        r"^deposit\s*amt$", r"^credit\s*amt$",
    ],
    ColumnRole.AMOUNT: [
        r"^amount(?:\s*\(?inr\)?)?$", r"^transaction\s*amount$",
        r"^txn\s*amount$", r"^amt$", r"^trans\s*amt$",
    ],
    ColumnRole.BALANCE: [
        r"^balance(?:\s*\(?inr\)?)?$", r"^closing\s*balance$",
        r"^running\s*balance$", r"^available\s*balance$", r"^bal$",
        r"^closing\s*bal$", r"^running\s*bal$", r"^balance\s*amount$",
    ],
    ColumnRole.DR_CR: [
        r"^dr\s*/?\s*cr$", r"^cr\s*/?\s*dr$", r"^type$", r"^sign$",
        r"^indicator$", r"^d\s*/?\s*c$",
    ],
    ColumnRole.TRANSACTION_ID: [
        r"^tran(?:saction)?\s*id$", r"^txn\s*id$", r"^id$",
    ],
    ColumnRole.SERIAL_NO: [
        r"^s\.?\s*no\.?$", r"^sl\.?\s*no\.?$", r"^seq\.?\s*no\.?$",
        r"^serial\s*no$", r"^sr\.?\s*no\.?$",
    ],
}


def match_cell_role(text: str) -> ColumnRole:
    """Matches a header cell string against semantic role patterns."""
    clean = re.sub(r"[\r\n\t]+", " ", str(text or "")).strip().lower()
    clean = re.sub(r"\s+", " ", clean)
    if not clean:
        return ColumnRole.UNKNOWN

    # Exact or regex match
    for role, patterns in ROLE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, clean):
                return role

    return ColumnRole.UNKNOWN


class AdaptiveHeaderDetector:
    """Scans pages dynamically to discover and track table headers, column roles,
    and horizontal coordinate spans across bordered and borderless bank statements.
    """

    def __init__(self, max_pages_to_search: int = 4):
        self.max_pages_to_search = max_pages_to_search
        self.active_header: Optional[HeaderCandidate] = None

    def detect_header_from_table(
        self,
        table: list[list[Optional[str]]],
        page_number: int,
        search_row_limit: int = 35,
    ) -> Optional[HeaderCandidate]:
        """Examines up to search_row_limit rows of a 2D table to locate the optimal header."""
        if not table:
            return None

        best_candidate: Optional[HeaderCandidate] = None
        highest_score = 0.0

        limit = min(len(table), search_row_limit)
        for r_idx in range(limit):
            row = table[r_idx]
            if not row or not any(row):
                continue

            columns: list[DetectedColumn] = []
            for col_idx, cell in enumerate(row):
                cell_text = str(cell or "").strip()
                if not cell_text:
                    continue
                role = match_cell_role(cell_text)
                if role != ColumnRole.UNKNOWN:
                    columns.append(
                        DetectedColumn(
                            role=role,
                            header_name=cell_text,
                            x0=float(col_idx * 100),  # Virtual coordinates for grid
                            x1=float((col_idx + 1) * 100),
                            col_idx=col_idx,
                            confidence=1.0,
                        )
                    )

            score, amt_mode = self._score_column_set(columns)
            if score > highest_score and score >= 3.0:
                highest_score = score
                raw_text = " | ".join(str(c or "").strip() for c in row if c)
                best_candidate = HeaderCandidate(
                    page_number=page_number,
                    y_top=float(r_idx),
                    y_bottom=float(r_idx + 1),
                    columns=columns,
                    amount_mode=amt_mode,
                    raw_header_text=raw_text,
                    semantic_score=score,
                    confidence=min(1.0, score / 6.0),
                )

        if best_candidate:
            self.active_header = best_candidate
        return best_candidate

    def detect_header_from_lines(
        self,
        lines: list[Any],
        page_number: int,
        search_line_limit: int = 50,
    ) -> Optional[HeaderCandidate]:
        """Detects headers in borderless text lines with spatial word coordinates."""
        if not lines:
            return None

        best_candidate: Optional[HeaderCandidate] = None
        highest_score = 0.0

        limit = min(len(lines), search_line_limit)
        for idx in range(limit):
            line = lines[idx]
            text = getattr(line, "text", str(line)).strip()
            if not text:
                continue

            words = getattr(line, "words", [])
            columns: list[DetectedColumn] = []

            # Check individual words or phrases in the line
            if words:
                # Group words into contiguous chunks or match word-by-word
                curr_phrase = []
                curr_x0 = 0.0
                curr_x1 = 0.0

                for w in words:
                    w_text = getattr(w, "text", "").strip()
                    w_x0 = getattr(w, "x0", 0.0)
                    w_x1 = getattr(w, "x1", 0.0)

                    # Test individual word
                    role = match_cell_role(w_text)
                    if role != ColumnRole.UNKNOWN:
                        columns.append(
                            DetectedColumn(
                                role=role,
                                header_name=w_text,
                                x0=w_x0,
                                x1=w_x1,
                                confidence=1.0,
                            )
                        )
                    else:
                        # Try 2-word phrase
                        curr_phrase.append((w_text, w_x0, w_x1))
                        if len(curr_phrase) >= 2:
                            comb_text = f"{curr_phrase[-2][0]} {curr_phrase[-1][0]}"
                            comb_role = match_cell_role(comb_text)
                            if comb_role != ColumnRole.UNKNOWN:
                                columns.append(
                                    DetectedColumn(
                                        role=comb_role,
                                        header_name=comb_text,
                                        x0=curr_phrase[-2][1],
                                        x1=curr_phrase[-1][2],
                                        confidence=1.0,
                                    )
                                )

            # If words not available, try splitting line by multiple spaces or delimiters
            if not columns:
                tokens = re.split(r"\s{2,}|\t|\|", text)
                for t_idx, tok in enumerate(tokens):
                    tok_clean = tok.strip()
                    role = match_cell_role(tok_clean)
                    if role != ColumnRole.UNKNOWN:
                        columns.append(
                            DetectedColumn(
                                role=role,
                                header_name=tok_clean,
                                x0=float(t_idx * 100),
                                x1=float((t_idx + 1) * 100),
                                col_idx=t_idx,
                                confidence=0.85,
                            )
                        )

            score, amt_mode = self._score_column_set(columns)
            if score > highest_score and score >= 3.0:
                highest_score = score
                y_top = getattr(line, "y_top", float(idx))
                y_bottom = getattr(line, "y_bottom", float(idx + 1))
                best_candidate = HeaderCandidate(
                    page_number=page_number,
                    y_top=y_top,
                    y_bottom=y_bottom,
                    columns=columns,
                    amount_mode=amt_mode,
                    raw_header_text=text,
                    semantic_score=score,
                    confidence=min(1.0, score / 6.0),
                )

        if best_candidate:
            self.active_header = best_candidate
        return best_candidate

    def _score_column_set(self, columns: list[DetectedColumn]) -> tuple[float, AmountMode]:
        """Evaluates semantic presence of essential banking columns and determines AmountMode."""
        score = 0.0
        roles = {c.role for c in columns}

        has_date = ColumnRole.DATE in roles or ColumnRole.VALUE_DATE in roles
        has_desc = ColumnRole.DESCRIPTION in roles
        has_debit = ColumnRole.DEBIT in roles
        has_credit = ColumnRole.CREDIT in roles
        has_amount = ColumnRole.AMOUNT in roles
        has_balance = ColumnRole.BALANCE in roles
        has_indicator = ColumnRole.DR_CR in roles

        if has_date:
            score += 2.0
        if has_desc:
            score += 1.5
        if has_balance:
            score += 2.0

        amount_mode = AmountMode.UNKNOWN
        if has_debit and has_credit:
            score += 3.0
            amount_mode = AmountMode.SEPARATE_DR_CR
        elif has_amount and has_indicator:
            score += 2.5
            amount_mode = AmountMode.SINGLE_AMOUNT_WITH_INDICATOR
        elif has_amount:
            score += 1.5
            amount_mode = AmountMode.SIGNED_AMOUNT
        elif has_debit or has_credit:
            score += 1.5
            amount_mode = AmountMode.SEPARATE_DR_CR

        if ColumnRole.REFERENCE in roles or ColumnRole.CHEQUE_NO in roles:
            score += 1.0
        if ColumnRole.SERIAL_NO in roles or ColumnRole.TRANSACTION_ID in roles:
            score += 0.5

        return score, amount_mode

