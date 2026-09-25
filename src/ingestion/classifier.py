"""PDF classification: native (text-based) vs scanned (image-based).

Uses PyMuPDF to attempt text extraction on each page.  Pages that yield
enough characters are considered native; otherwise they are scanned.
The document-level classification is derived from the per-page results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class PdfType(str, Enum):
    """High-level document classification."""

    NATIVE = "native"
    SCANNED = "scanned"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class PageClassification:
    """Per-page classification result."""

    page_number: int
    char_count: int
    is_native: bool


@dataclass(frozen=True)
class PdfClassification:
    """Full classification for one PDF file."""

    pdf_type: PdfType
    total_pages: int
    native_pages: int
    scanned_pages: int
    pages: list[PageClassification] = field(default_factory=list)

    @property
    def native_ratio(self) -> float:
        if self.total_pages == 0:
            return 0.0
        return self.native_pages / self.total_pages


class PdfClassifier:
    """Classifies a PDF as native, scanned, or hybrid.

    Parameters
    ----------
    min_chars_per_page:
        Minimum characters of extractable text for a page to be
        considered native.  Default ``50``.
    native_threshold:
        Ratio of native pages (0‑1) above which the document is
        classified as *native*.  Default ``0.80`` (80 %).
    scanned_threshold:
        Ratio of native pages (0‑1) below which the document is
        classified as *scanned*.  Default ``0.20`` (20 %).
        Values between the two thresholds yield *hybrid*.
    """

    def __init__(
        self,
        *,
        min_chars_per_page: int = 50,
        native_threshold: float = 0.80,
        scanned_threshold: float = 0.20,
    ):
        self.min_chars_per_page = min_chars_per_page
        self.native_threshold = native_threshold
        self.scanned_threshold = scanned_threshold

    def classify(self, pdf_path: str | Path) -> PdfClassification:
        """Classify a single PDF file."""
        try:
            import pymupdf
        except ImportError:
            try:
                import fitz as pymupdf  # type: ignore[no-redef]
            except ImportError:
                logger.warning(
                    "PyMuPDF not installed — assuming scanned PDF: %s",
                    pdf_path,
                )
                return PdfClassification(
                    pdf_type=PdfType.SCANNED,
                    total_pages=0,
                    native_pages=0,
                    scanned_pages=0,
                )

        path = Path(pdf_path)
        try:
            doc = pymupdf.open(str(path))
        except Exception:
            logger.warning(
                "Could not open PDF for classification — assuming scanned: %s",
                pdf_path,
            )
            return PdfClassification(
                pdf_type=PdfType.SCANNED,
                total_pages=0,
                native_pages=0,
                scanned_pages=0,
            )

        pages: list[PageClassification] = []

        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").strip()
                char_count = len(text)
                is_native = char_count >= self.min_chars_per_page
                pages.append(
                    PageClassification(
                        page_number=page_num + 1,
                        char_count=char_count,
                        is_native=is_native,
                    )
                )
        except Exception:
            logger.warning(
                "Error reading pages for classification — assuming scanned: %s",
                pdf_path,
            )
            return PdfClassification(
                pdf_type=PdfType.SCANNED,
                total_pages=0,
                native_pages=0,
                scanned_pages=0,
            )
        finally:
            doc.close()

        total = len(pages)
        native_count = sum(1 for p in pages if p.is_native)
        scanned_count = total - native_count

        if total == 0:
            pdf_type = PdfType.SCANNED
        elif native_count / total >= self.native_threshold:
            pdf_type = PdfType.NATIVE
        elif native_count / total <= self.scanned_threshold:
            pdf_type = PdfType.SCANNED
        else:
            pdf_type = PdfType.HYBRID

        return PdfClassification(
            pdf_type=pdf_type,
            total_pages=total,
            native_pages=native_count,
            scanned_pages=scanned_count,
            pages=pages,
        )
