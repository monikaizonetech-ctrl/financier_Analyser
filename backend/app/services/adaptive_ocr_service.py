"""
Adaptive OCR Fallback Engine.

Renders scanned or image-based PDF pages to high-resolution bitmaps,
applies OpenCV computer vision enhancements (grayscale, bilateral noise reduction,
Otsu adaptive thresholding, deskewing), and extracts spatial word/line coordinates
using RapidOCR / Tesseract.
"""
from __future__ import annotations
import logging
from typing import Any, Optional

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    from rapidocr_onnxruntime import RapidOCR
    _rapid_ocr = RapidOCR()
except Exception:
    _rapid_ocr = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

from app.services.pdf_extractor import ExtractedPage, ExtractedLine, ExtractedWord, LineType

logger = logging.getLogger(__name__)


class AdaptiveOCRService:
    """Provides selective OCR extraction for scanned or low-character pages."""

    @classmethod
    def is_available(cls) -> bool:
        """Returns True if at least one OCR backend and OpenCV are available."""
        return cv2 is not None and (_rapid_ocr is not None or pytesseract is not None)

    @classmethod
    def preprocess_image(cls, img_np: Any) -> Any:
        """Applies OpenCV deskew, grayscale conversion, and thresholding."""
        if cv2 is None or img_np is None:
            return img_np

        try:
            # 1. Grayscale
            if len(img_np.shape) == 3:
                gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            else:
                gray = img_np

            # 2. Noise Reduction
            denoised = cv2.bilateralFilter(gray, 9, 75, 75)

            # 3. Deskew
            coords = np.column_stack(np.where(denoised < 240))
            if coords.size > 0:
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                if abs(angle) > 0.5 and abs(angle) < 45:
                    (h, w) = denoised.shape[:2]
                    center = (w // 2, h // 2)
                    m = cv2.getRotationMatrix2D(center, angle, 1.0)
                    denoised = cv2.warpAffine(
                        denoised, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
                    )

            # 4. Otsu Adaptive Thresholding
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return thresh
        except Exception as e:
            logger.warning("OpenCV image preprocessing error: %s", e)
            return img_np

    @classmethod
    def ocr_page(
        cls,
        fitz_page: Any,
        page_number: int,
        dpi: int = 200,
    ) -> ExtractedPage:
        """
        Renders a PyMuPDF page to an image, executes OCR, and constructs an ExtractedPage.
        """
        # Render pixmap
        zoom = dpi / 72.0
        import fitz
        mat = fitz.Matrix(zoom, zoom)
        pix = fitz_page.get_pixmap(matrix=mat, alpha=False)

        # Convert to numpy array
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
        processed = cls.preprocess_image(img_np)

        words_list: list[ExtractedWord] = []
        raw_text_chunks: list[str] = []

        # 1. Try RapidOCR (fast, onnx-based, robust)
        if _rapid_ocr is not None:
            try:
                ocr_result, _ = _rapid_ocr(processed)
                if ocr_result:
                    for item in ocr_result:
                        # item: [ [ [x0, y0], [x1, y0], [x1, y1], [x0, y1] ], text, score ]
                        pts, text, score = item[0], item[1].strip(), float(item[2])
                        if not text:
                            continue
                        raw_text_chunks.append(text)
                        # Coordinates in page points (divide by zoom)
                        x0 = min(p[0] for p in pts) / zoom
                        x1 = max(p[0] for p in pts) / zoom
                        y0 = min(p[1] for p in pts) / zoom
                        y1 = max(p[1] for p in pts) / zoom

                        # Split text into individual words
                        tokens = text.split()
                        if len(tokens) == 1:
                            words_list.append(ExtractedWord(text=tokens[0], x0=x0, x1=x1, top=y0, bottom=y1))
                        else:
                            span_w = (x1 - x0) / max(1, len(tokens))
                            for idx, tok in enumerate(tokens):
                                tok_x0 = x0 + idx * span_w
                                tok_x1 = tok_x0 + span_w
                                words_list.append(ExtractedWord(text=tok, x0=tok_x0, x1=tok_x1, top=y0, bottom=y1))
            except Exception as e:
                logger.warning("RapidOCR execution error: %s", e)

        # 2. Fallback to pytesseract if RapidOCR yielded nothing
        if not words_list and pytesseract is not None:
            try:
                data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
                n_boxes = len(data["text"])
                for i in range(n_boxes):
                    txt = data["text"][i].strip()
                    if not txt:
                        continue
                    raw_text_chunks.append(txt)
                    x = data["left"][i] / zoom
                    y = data["top"][i] / zoom
                    w = data["width"][i] / zoom
                    h = data["height"][i] / zoom
                    words_list.append(ExtractedWord(text=txt, x0=x, x1=x + w, top=y, bottom=y + h))
            except Exception as e:
                logger.warning("Pytesseract execution error: %s", e)

        # Cluster words into ExtractedLines using vertical proximity
        words_list.sort(key=lambda w: (round(w.top / 8.0) * 8.0, w.x0))
        lines: list[ExtractedLine] = []
        if words_list:
            curr_line_words = [words_list[0]]
            curr_y = words_list[0].top

            for w in words_list[1:]:
                if abs(w.top - curr_y) <= 6.0:  # vertical tolerance
                    curr_line_words.append(w)
                else:
                    curr_line_words.sort(key=lambda x: x.x0)
                    line_text = " ".join(item.text for item in curr_line_words)
                    y_top = min(item.top for item in curr_line_words)
                    y_bot = max(item.bottom for item in curr_line_words)
                    lines.append(
                        ExtractedLine(
                            line_number=len(lines) + 1,
                            text=line_text,
                            y_top=y_top,
                            y_bottom=y_bot,
                            words=curr_line_words,
                            page_number=page_number,
                            line_type=LineType.TRANSACTION_CANDIDATE,
                        )
                    )
                    curr_line_words = [w]
                    curr_y = w.top

            if curr_line_words:
                curr_line_words.sort(key=lambda x: x.x0)
                line_text = " ".join(item.text for item in curr_line_words)
                y_top = min(item.top for item in curr_line_words)
                y_bot = max(item.bottom for item in curr_line_words)
                lines.append(
                    ExtractedLine(
                        line_number=len(lines) + 1,
                        text=line_text,
                        y_top=y_top,
                        y_bottom=y_bot,
                        words=curr_line_words,
                        page_number=page_number,
                        line_type=LineType.TRANSACTION_CANDIDATE,
                    )
                )

        full_text = "\n".join(l.text for l in lines)
        return ExtractedPage(
            page_number=page_number,
            width=fitz_page.rect.width,
            height=fitz_page.rect.height,
            raw_text=full_text,
            character_count=len(full_text),
            lines=lines,
            transaction_lines=lines,
            is_scanned=True,
        )

