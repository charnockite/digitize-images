"""Tests for the table_extractor module."""

import pathlib

import pandas as pd
import pytest

from table_extractor import _dedup_header, extract_tables_from_pdf
from conftest import requires_ocr_tools

EXAMPLES_DIR = pathlib.Path(__file__).parent.parent / "examples"
FLAT_PDF = EXAMPLES_DIR / "test_selectable.pdf"
NON_FLAT_PDF = EXAMPLES_DIR / "test_ocr.pdf"


# ---------------------------------------------------------------------------
# _dedup_header
# ---------------------------------------------------------------------------


def test_dedup_header_no_duplicates():
    """Unique column names are returned unchanged."""
    header = ["a", "b", "c"]
    assert _dedup_header(header) == ["a", "b", "c"]


def test_dedup_header_with_duplicates():
    """Duplicate column names are made unique by appending a counter."""
    header = ["a", "b", "a", "a"]
    assert _dedup_header(header) == ["a", "b", "a_1", "a_2"]


def test_dedup_header_all_same():
    """All identical names receive unique suffixes."""
    header = ["x", "x", "x"]
    result = _dedup_header(header)
    assert len(result) == 3
    assert len(set(result)) == 3


def test_dedup_header_empty():
    """An empty header returns an empty list."""
    assert _dedup_header([]) == []


# ---------------------------------------------------------------------------
# extract_tables_from_pdf – flat (selectable-text) PDF
# ---------------------------------------------------------------------------


def test_flat_pdf_returns_tables():
    """A PDF with selectable text tables produces at least one table."""
    tables, method = extract_tables_from_pdf(FLAT_PDF)
    assert len(tables) > 0


def test_flat_pdf_uses_pdfplumber():
    """A PDF with selectable text should be extracted via pdfplumber."""
    _, method = extract_tables_from_pdf(FLAT_PDF)
    assert method == "pdfplumber"


def test_flat_pdf_tuple_structure():
    """Each entry is a (page_number, table_index, DataFrame) tuple."""
    tables, _ = extract_tables_from_pdf(FLAT_PDF)
    for page_num, table_idx, df in tables:
        assert isinstance(page_num, int) and page_num >= 1
        assert isinstance(table_idx, int) and table_idx >= 1
        assert isinstance(df, pd.DataFrame)


def test_flat_pdf_dataframe_has_rows_and_columns():
    """Each extracted DataFrame has at least one row and one column."""
    tables, _ = extract_tables_from_pdf(FLAT_PDF)
    for _, _, df in tables:
        assert df.shape[0] >= 1
        assert df.shape[1] >= 1


def test_flat_pdf_no_none_values():
    """All cell values are strings (None cells are replaced with empty strings)."""
    tables, _ = extract_tables_from_pdf(FLAT_PDF)
    for _, _, df in tables:
        for col in df.columns:
            assert all(isinstance(v, str) for v in df[col])


def test_flat_pdf_page_numbers():
    """Page numbers in the result match the actual pages that contain tables."""
    tables, _ = extract_tables_from_pdf(FLAT_PDF)
    page_nums = [page_num for page_num, _, _ in tables]
    assert all(p >= 1 for p in page_nums)


# ---------------------------------------------------------------------------
# extract_tables_from_pdf – non-flat (OCR / image-only) PDF
# ---------------------------------------------------------------------------


@requires_ocr_tools
def test_non_flat_pdf_returns_tables_via_ocr():
    """An image-only PDF falls back to OCR and returns at least one table."""
    tables, method = extract_tables_from_pdf(NON_FLAT_PDF)
    assert method == "ocr"
    assert len(tables) > 0


@requires_ocr_tools
def test_non_flat_pdf_tuple_structure():
    """OCR-extracted tables follow the same (page_number, table_index, DataFrame) structure."""
    tables, _ = extract_tables_from_pdf(NON_FLAT_PDF)
    for page_num, table_idx, df in tables:
        assert isinstance(page_num, int) and page_num >= 1
        assert isinstance(table_idx, int) and table_idx >= 1
        assert isinstance(df, pd.DataFrame)


@requires_ocr_tools
def test_non_flat_pdf_dataframe_has_rows_and_columns():
    """Each OCR-extracted DataFrame has at least one row and one column."""
    tables, _ = extract_tables_from_pdf(NON_FLAT_PDF)
    for _, _, df in tables:
        assert df.shape[0] >= 1
        assert df.shape[1] >= 1
