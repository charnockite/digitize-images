"""Pytest configuration and shared fixtures."""

import shutil

import pytest


def _ocr_tools_available() -> bool:
    """Return True when both poppler (pdftoppm/pdfinfo) and tesseract are on PATH."""
    poppler = shutil.which("pdftoppm") or shutil.which("pdfinfo")
    tesseract = shutil.which("tesseract")
    return bool(poppler and tesseract)


requires_ocr_tools = pytest.mark.skipif(
    not _ocr_tools_available(),
    reason="poppler-utils and tesseract-ocr must be installed to run OCR tests",
)
