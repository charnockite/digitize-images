import io
import statistics

import pandas as pd
import pdf2image
import pdfplumber
import pytesseract
import streamlit as st
from PIL import Image

LOGO_PATH = "hornfels_250x250.png"
HORNFELS_URL = "https://hornfelsconsulting.com"

# A valid table must have at least a header row and one data row.
MIN_TABLE_ROWS = 2
# Maximum number of column-checkboxes to display per row in the UI.
MAX_COLUMNS_PER_ROW = 6

st.markdown(
    """
    <style>
    /* Header / top bar */
    [data-testid="stHeader"] {
        background-color: #1B3C33;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1B3C33;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }

    /* Main title */
    h1 {
        color: #1B3C33;
        font-weight: 700;
    }

    /* Divider line accent */
    .hornfels-divider {
        border: none;
        border-top: 3px solid #C68D40;
        margin: 0.25rem 0 1.25rem 0;
    }

    /* Footer / branding link */
    .hornfels-link a {
        color: #C68D40;
        font-weight: 600;
        text-decoration: none;
    }
    .hornfels-link a:hover {
        text-decoration: underline;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image(LOGO_PATH, width=90)
with col_title:
    st.title("Digitize Images")

st.markdown('<hr class="hornfels-divider">', unsafe_allow_html=True)


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


def extract_tables_from_pdf(file) -> tuple[list[tuple[int, int, pd.DataFrame]], str]:
    """Return tables and the extraction method used ('pdfplumber' or 'ocr').

    First attempts pdfplumber for PDFs with selectable text.  If no tables are
    found, falls back to OCR (pdf2image + pytesseract).
    """
    file_bytes = file.read() if hasattr(file, "read") else file

    tables = _extract_tables_pdfplumber(io.BytesIO(file_bytes))
    if tables:
        return tables, "pdfplumber"

    tables = _extract_tables_ocr(io.BytesIO(file_bytes))
    return tables, "ocr"


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


# ── OCR helpers ───────────────────────────────────────────────────────────────

# DPI used when rasterising each PDF page for OCR.
_OCR_DPI = 200
# Words whose y-center is within this many pixels are considered the same row.
_ROW_TOLERANCE = 8
# Columns whose x-center is within this many pixels are considered the same column.
_COL_TOLERANCE = 20
# Minimum confidence score (0-100) for a word to be included.
_MIN_CONFIDENCE = 30


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

    # Compute the y-center for each word.
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


def _extract_tables_ocr(file) -> list[tuple[int, int, pd.DataFrame]]:
    """Convert each PDF page to an image, run OCR, and return structured tables."""
    file_bytes = file.read() if hasattr(file, "read") else file
    try:
        images = pdf2image.convert_from_bytes(file_bytes, dpi=_OCR_DPI)
    except Exception:
        return []

    tables = []
    for page_num, image in enumerate(images, start=1):
        df = _ocr_page_to_dataframe(image)
        if df is not None:
            tables.append((page_num, 1, df))
    return tables


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Upload PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", label_visibility="collapsed")
    st.markdown("---")
    st.markdown(
        "**How to use**\n"
        "1. Upload a PDF with tables.\n"
        "2. Uncheck columns or rows you don't need.\n"
        "3. Download the filtered table as CSV."
    )

# ── Main area ─────────────────────────────────────────────────────────────────
if uploaded_file is None:
    st.info("Upload a PDF in the sidebar to get started.")
else:
    with st.spinner("Extracting tables from PDF…"):
        tables, method = extract_tables_from_pdf(uploaded_file)

    if method == "ocr":
        st.info("ℹ️ No selectable text found — tables extracted via OCR.")

    if not tables:
        st.warning(
            "No tables were detected in this PDF. "
            "Make sure the file contains structured table data, "
            "or that the text is legible enough for OCR."
        )
    else:
        st.success(f"Found **{len(tables)}** table(s). Edit selections below, then download.")

        for idx, (page_num, table_idx, df) in enumerate(tables):
            st.subheader(f"Table {idx + 1}  ·  Page {page_num}")

            # ── Column selection ──────────────────────────────────────────
            st.markdown("**Columns to include:**")
            all_cols = df.columns.tolist()
            checkbox_columns = st.columns(min(len(all_cols), MAX_COLUMNS_PER_ROW))
            col_selection: dict[str, bool] = {}
            for i, col in enumerate(all_cols):
                with checkbox_columns[i % MAX_COLUMNS_PER_ROW]:
                    col_selection[col] = st.checkbox(
                        col if col else f"Col {i + 1}",
                        value=True,
                        key=f"col_{idx}_{i}",
                    )

            selected_cols = [c for c, v in col_selection.items() if v]

            if not selected_cols:
                st.info("Select at least one column to see a preview.")
            else:
                # ── Row selection via editable table ─────────────────────
                df_edit = df[selected_cols].copy()
                df_edit.insert(0, "Include", True)

                st.markdown("**Rows to include** (uncheck to exclude):")
                edited_df = st.data_editor(
                    df_edit,
                    column_config={
                        "Include": st.column_config.CheckboxColumn(
                            "Include", default=True, width="small"
                        )
                    },
                    hide_index=True,
                    width="stretch",
                    key=f"editor_{idx}",
                )

                final_df = edited_df[edited_df["Include"]].drop(columns=["Include"])

                st.caption(f"{len(final_df)} of {len(df)} rows selected.")

                # ── Download ─────────────────────────────────────────────
                csv_bytes = final_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"⬇ Download Table {idx + 1} as CSV",
                    data=csv_bytes,
                    file_name=f"table_{idx + 1}_page_{page_num}.csv",
                    mime="text/csv",
                    key=f"download_{idx}",
                )

            st.markdown("---")

st.markdown(
    '<p class="hornfels-link">Powered by '
    f'<a href="{HORNFELS_URL}" target="_blank" rel="noopener noreferrer">Hornfels Consulting</a>'
    "</p>",
    unsafe_allow_html=True,
)
