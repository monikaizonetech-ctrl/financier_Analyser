"""
Test suite to verify RAM optimization in the PDF processing pipeline:
1. Chunked SHA-256 calculation
2. Prompt releasing of page objects and caches
3. In-place _make_json_safe avoiding deep copies
4. Streaming authenticity checks without full f.read()
5. Concurrency protection for large PDF analyses
"""
import os
import unittest
import tracemalloc
import gc
from datetime import datetime, date
from decimal import Decimal

from app.services.pdf_extractor import extract_pdf_document, extract_document_metadata
from app.services.authenticity_service import check_document_authenticity
from app.services.file_analysis_service import _make_json_safe
from app.routers.reports import _large_pdf_semaphore, _is_large_analysis, _get_available_memory_mb


class TestMemoryOptimization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.large_pdf = os.path.join(
            os.path.dirname(__file__),
            "..",
            "uploads",
            "7927a5ce-3d3c-4f45-a232-cb0a11dccc33",
            "7364831226.pdf",
        )

    def test_01_make_json_safe_in_place_and_no_duplication(self):
        """Verify _make_json_safe runs in-place and handles shared references without duplicating memory."""
        # Shared row referenced in multiple lists
        row = {
            "date": date(2026, 8, 1),
            "created_at": datetime(2026, 8, 1, 12, 0, 0),
            "amount": Decimal("1500.50"),
            "description": "Payment",
        }
        summary = {
            "details": [{"transactions": [row]}],
            "analytics": {
                "all_rows": [row],
                "top_expenses": [row],
            },
        }

        tracemalloc.start()
        res = _make_json_safe(summary)
        c, p = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # In-place conversion assertions
        self.assertEqual(res["details"][0]["transactions"][0]["date"], "2026-08-01")
        self.assertEqual(res["analytics"]["all_rows"][0]["date"], "2026-08-01")
        self.assertEqual(res["analytics"]["all_rows"][0]["amount"], 1500.50)
        self.assertIs(
            res["details"][0]["transactions"][0],
            res["analytics"]["all_rows"][0],
            "Shared references must remain identical objects (no deep copies created)",
        )
        self.assertLess(p, 100 * 1024, "Should allocate negligible memory for make_json_safe")

    def test_02_chunked_sha256_and_prompt_cache_flushing(self):
        """Verify extract_pdf_document uses chunked hash and bounded memory."""
        if not os.path.exists(self.large_pdf):
            self.skipTest("Large sample PDF not present")

        tracemalloc.start()
        doc = extract_pdf_document(self.large_pdf, max_pages=15)
        self.assertTrue(doc.is_valid)
        self.assertEqual(doc.pages_processed, 15)

        # Ensure debug text chunking was capped at 20 pages max
        self.assertLessEqual(len(doc.raw_debug_text.split("--- PAGE ")), 21)

        c, p = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak memory for 15 pages with cache flushing and periodic GC should stay under 35 MB
        self.assertLess(p / (1024 * 1024), 35.0, "15 pages extraction peak should stay under 35 MB")

    def test_03_authenticity_check_streaming_without_raw_buffer(self):
        """Verify check_document_authenticity does not hold full file raw bytes in memory."""
        if not os.path.exists(self.large_pdf):
            self.skipTest("Large sample PDF not present")

        file_size_mb = os.path.getsize(self.large_pdf) / (1024 * 1024)
        self.assertGreater(file_size_mb, 5.0, "Sample PDF should be large (> 5 MB)")

        tracemalloc.start()
        res = check_document_authenticity(self.large_pdf)
        c, p = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self.assertIn("status", res)
        # Peak memory must not exceed file size + baseline overhead (meaning raw_bytes = f.read() was eliminated)
        self.assertLess(p / (1024 * 1024), 25.0, "Streaming authenticity check peak must stay under 25 MB")

    def test_04_concurrency_lock_and_memory_helpers(self):
        """Verify concurrency controls and system memory checking."""
        # Available memory helper
        avail = _get_available_memory_mb()
        self.assertIsNotNone(avail, "System available memory should be resolvable")
        self.assertGreater(avail, 0.0)

        # Large PDF detection
        if os.path.exists(self.large_pdf):
            self.assertTrue(_is_large_analysis([self.large_pdf]))
        self.assertFalse(_is_large_analysis(["nonexistent.txt"]))

        # Concurrency semaphore
        acquired = _large_pdf_semaphore.acquire(timeout=1)
        self.assertTrue(acquired)
        _large_pdf_semaphore.release()

