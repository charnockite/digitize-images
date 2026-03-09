import io

import pandas as pd
import pdf2image
import pdfplumber
import pytesseract
from PIL import Image

# A valid table must have at least a header row and one data row.
MIN_TABLE_ROWS = 2

# DPI used when rasterising each PDF page for OCR.
_OCR_DPI = 200


def _dedup_header(header: list[str]) -> list[str]:
    """Return a list of column names with duplicates made unique."""
    seen: dict[str, int] = {}
    result = []
    for name in header:
        if name in seen:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            result.append(name)
    return result


def _ocr_page_to_dataframe(image: Image.Image) -> pd.DataFrame | None:
    """Run Tesseract on one page image and return the text as a DataFrame.

    Each non-empty line of OCR output becomes a row, with whitespace-separated
    tokens as columns.  The first row is used as the column header.  Rows with
    fewer tokens than the widest row are padded with empty strings.

    Note: whitespace splitting means multi-word cell values are split into
    separate columns.  This is an intentional simplification — the goal is to
    load the text rather than to reconstruct a precise table layout.
    """
    text = pytesseract.image_to_string(image)

    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < MIN_TABLE_ROWS:
        return None

    rows = [line.split() for line in lines]

    # Pad every row to the same width.
    max_cols = max(len(row) for row in rows)
    rows = [row + [""] * (max_cols - len(row)) for row in rows]

    header = _dedup_header(rows[0])
    df = pd.DataFrame(rows[1:], columns=header)
    return df


def _extract_tables_pdfplumber(file) -> list[tuple[int, int, pd.DataFrame]]:
    """Try to extract tables using pdfplumber (works on text-layer PDFs)."""
    tables = []
    with pdfplumber.open(file) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_tables = page.extract_tables()
            for table_idx, raw_table in enumerate(page_tables, start=1):
                if not raw_table or len(raw_table) < MIN_TABLE_ROWS:
                    continue
                header = _dedup_header(
                    [str(cell) if cell is not None else "" for cell in raw_table[0]]
                )
                rows = [
                    [str(cell) if cell is not None else "" for cell in row]
                    for row in raw_table[1:]
                ]
                df = pd.DataFrame(rows, columns=header)
                tables.append((page_num, table_idx, df))
    return tables


def _extract_tables_ocr(file_bytes: bytes) -> list[tuple[int, int, pd.DataFrame]]:
    """Convert each PDF page to an image, run OCR, and return structured tables."""
    try:
        images = pdf2image.convert_from_bytes(file_bytes, dpi=_OCR_DPI)
    except (
        pdf2image.exceptions.PDFInfoNotInstalledError,
        pdf2image.exceptions.PopplerNotInstalledError,
        pdf2image.exceptions.PDFPageCountError,
        pdf2image.exceptions.PDFSyntaxError,
        pdf2image.exceptions.PDFPopplerTimeoutError,
    ):
        return []

    tables = []
    for page_num, image in enumerate(images, start=1):
        df = _ocr_page_to_dataframe(image)
        if df is not None:
            tables.append((page_num, 1, df))
    return tables


def get_raw_ocr_data(file) -> pd.DataFrame | None:
    """Run ``pytesseract.image_to_data`` on every page and return a combined DataFrame.

    Each page's output is augmented with a ``page`` column so rows can be
    traced back to their source page.  Returns ``None`` if the PDF cannot be
    rasterised (e.g. poppler/Tesseract not installed).
    """
    if hasattr(file, "read"):
        file_bytes = file.read()
    else:
        with open(file, "rb") as fh:
            file_bytes = fh.read()

    try:
        images = pdf2image.convert_from_bytes(file_bytes, dpi=_OCR_DPI)
    except (
        pdf2image.exceptions.PDFInfoNotInstalledError,
        pdf2image.exceptions.PopplerNotInstalledError,
        pdf2image.exceptions.PDFPageCountError,
        pdf2image.exceptions.PDFSyntaxError,
        pdf2image.exceptions.PDFPopplerTimeoutError,
    ):
        return None

    dfs: list[pd.DataFrame] = []
    for page_num, image in enumerate(images, start=1):
        try:
            df = pytesseract.image_to_data(image, output_type=pytesseract.Output.DATAFRAME)
        except pytesseract.TesseractError:
            continue
        df.insert(0, "page", page_num)
        dfs.append(df)

    if not dfs:
        return None

    return pd.concat(dfs, ignore_index=True)


def extract_tables_from_pdf(
    file,
) -> tuple[list[tuple[int, int, pd.DataFrame]], str]:
    """Extract tables from a PDF, falling back to OCR when needed.

    Tries pdfplumber first (fast, accurate for PDFs with a text layer).  If no
    tables are found that way, the pages are rasterised and passed through
    Tesseract OCR.

    Returns:
        A ``(tables, method)`` tuple where *tables* is a list of
        ``(page_number, table_index, DataFrame)`` triples and *method* is
        either ``"pdfplumber"`` or ``"ocr"``.
    """
    if hasattr(file, "read"):
        file_bytes = file.read()
    else:
        # Accept pathlib.Path or str
        with open(file, "rb") as fh:
            file_bytes = fh.read()

    tables = _extract_tables_pdfplumber(io.BytesIO(file_bytes))
    if tables:
        return tables, "pdfplumber"

    tables = _extract_tables_ocr(file_bytes)
    return tables, "ocr"
