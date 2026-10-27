"""
Multi-Line Narration Reconstruction and Transaction Boundary Engine.

Identifies transaction boundaries, filters noise / headers / footers,
and seamlessly reconstructs wrapped multi-line descriptions across physical rows and pages.
"""
from __future__ import annotations
import re
from typing import Optional

# Common footer and noise patterns in bank statements
NOISE_PATTERNS = [
    re.compile(r"^page\s+\d+\s*(?:of|/)\s*\d+", re.IGNORECASE),
    re.compile(r"^\*+\s*end of statement\s*\*+", re.IGNORECASE),
    re.compile(r"^this is a system generated (?:statement|advice)", re.IGNORECASE),
    re.compile(r"^computer generated copy", re.IGNORECASE),
    re.compile(r"^statement summary", re.IGNORECASE),
    re.compile(r"^opening\s+balance\s*:", re.IGNORECASE),
    re.compile(r"^closing\s+balance\s*:", re.IGNORECASE),
    re.compile(r"^total\s+(?:debit|credit|withdrawal|deposit)\s*:", re.IGNORECASE),
    re.compile(r"^\-{5,}$"),
    re.compile(r"^\={5,}$"),
    re.compile(r"^\*+$"),
]

HEADER_BLEED_PATTERNS = [
    re.compile(r"\bpage\s+\d+\s*(?:of|/)\s*\d+\b", re.IGNORECASE),
    re.compile(r"\bdate\s+particulars\s+cheque\b", re.IGNORECASE),
    re.compile(r"\baccount\s+statement\s+for\b", re.IGNORECASE),
]


def is_noise_or_summary_line(text: str) -> bool:
    """Returns True if the line is a page footer, summary box, or visual divider."""
    if not text:
        return True
    s = text.strip()
    if len(s) < 2:
        return True
    for pat in NOISE_PATTERNS:
        if pat.search(s):
            return True
    return False


def clean_narration(text: str) -> str:
    """Cleans up internal newlines, extra spaces, and header bleeds from narration text."""
    if not text:
        return ""
    clean = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    for pat in HEADER_BLEED_PATTERNS:
        clean = pat.sub("", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


class NarrationReconstructor:
    """Accumulates and merges multi-line narration fragments for active transactions."""

    def __init__(self):
        self.pending_narration_lines: list[str] = []

    def start_transaction(self, initial_text: str = "") -> None:
        """Starts a new transaction narration buffer."""
        self.pending_narration_lines = []
        if initial_text and not is_noise_or_summary_line(initial_text):
            self.pending_narration_lines.append(initial_text.strip())

    def append_continuation(self, text: str) -> bool:
        """Appends a continuation line if it does not match noise/footer patterns."""
        if not text or is_noise_or_summary_line(text):
            return False
        clean = text.strip()
        if clean:
            self.pending_narration_lines.append(clean)
            return True
        return False

    def build_narrations(self) -> tuple[str, str]:
        """Returns (normalized_description, raw_description)."""
        if not self.pending_narration_lines:
            return "Transaction", ""

        raw_desc = " \n ".join(self.pending_narration_lines)
        normalized = clean_narration(" ".join(self.pending_narration_lines))
        return normalized or "Transaction", raw_desc

