import io
import statistics

import pandas as pd
import pdf2image
import pdfplumber
import pytesseract
from PIL import Image

# A valid table must have at least a header row and one data row.
MIN_TABLE_ROWS = 2

# DPI used when rasterising each PDF page for OCR.
_OCR_DPI = 200
# Words whose y-center is within this many pixels are considered the same row.
_ROW_TOLERANCE = 8
# Columns whose x-center is within this many pixels are considered the same column.
_COL_TOLERANCE = 20
# Minimum confidence score (0-100) for a word to be included.
_MIN_CONFIDENCE = 30


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


def _cluster_centers(values: list[int], tolerance: int) -> list[int]:
    """Merge close values into cluster centers (sorted ascending)."""
    sorted_vals = sorted(set(values))
    clusters: list[list[int]] = []
    for v in sorted_vals:
        if clusters and v - statistics.mean(clusters[-1]) <= tolerance:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [round(statistics.mean(c)) for c in clusters]


def _ocr_page_to_dataframe(image: Image.Image) -> pd.DataFrame | None:
    """Run Tesseract on one page image and reconstruct a table from word positions."""
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DATAFRAME)

    # Keep only confident, non-empty words.
    data = data[(data["conf"] >= _MIN_CONFIDENCE) & (data["text"].str.strip() != "")]
    if data.empty:
        return None

    # Compute the y-center and x-center for each word.
    data = data.copy()
    data["y_center"] = data["top"] + data["height"] // 2
    data["x_center"] = data["left"] + data["width"] // 2

    row_centers = _cluster_centers(data["y_center"].tolist(), _ROW_TOLERANCE)
    col_centers = _cluster_centers(data["x_center"].tolist(), _COL_TOLERANCE)

    if not row_centers or not col_centers:
        return None

    # Assign each word to a (row_idx, col_idx) grid cell.
    def nearest_index(value: int, centers: list[int]) -> int:
        return min(range(len(centers)), key=lambda i: abs(centers[i] - value))

    data["row_idx"] = data["y_center"].apply(lambda v: nearest_index(v, row_centers))
    data["col_idx"] = data["x_center"].apply(lambda v: nearest_index(v, col_centers))

    # Concatenate words in the same cell (preserving reading order within cell).
    cell_data: dict[tuple[int, int], list[str]] = {}
    for _, word_row in data.sort_values(["row_idx", "col_idx", "left"]).iterrows():
        key = (int(word_row["row_idx"]), int(word_row["col_idx"]))
        cell_data.setdefault(key, []).append(str(word_row["text"]))

    n_rows = len(row_centers)
    n_cols = len(col_centers)
    grid = [
        [" ".join(cell_data.get((r, c), [])) for c in range(n_cols)]
        for r in range(n_rows)
    ]

    if len(grid) < MIN_TABLE_ROWS:
        return None

    header = _dedup_header(grid[0])
    df = pd.DataFrame(grid[1:], columns=header)
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
