import io
import pathlib

import pandas as pd
import streamlit as st

from table_extractor import extract_tables_from_pdf, get_raw_ocr_data
from utils import extract_regex_matches

LOGO_PATH = "hornfels_250x250.png"
HORNFELS_URL = "https://hornfelsconsulting.com"

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

    /* File uploader — white box needs dark text for contrast */
    [data-testid="stFileUploader"] * {
        color: #1B3C33 !important;
    }

    /* Regex text input in sidebar should use the same dark green */
    [data-testid="stTextInput"] input {
        color: #1B3C33 !important;
        -webkit-text-fill-color: #1B3C33 !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #1B3C33 !important;
        opacity: 0.75;
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


# ── Sidebar ──────────────────────────────────────────────────────────────────
# Initialise bulk file list so the main-area code can always reference it.
uploaded_files: list = []
with st.sidebar:
    mode = st.radio(
        "Mode",
        options=["Single file", "Bulk processing"],
        horizontal=True,
    )
    st.markdown("---")

    # ── Regex filter (global, applies to all tables / both modes) ─────────────
    use_regex = st.checkbox("Enable regex filter", key="use_regex_global")
    regex_pattern = ""
    if use_regex:
        re_inp, link_col = st.columns([4, 1])
        with re_inp:
            regex_pattern = st.text_input(
                "Regular expression",
                key="regex_pattern_global",
                placeholder=r"e.g. ^\d{4}$ or .*total.*",
                label_visibility="collapsed",
            )
            st.caption(
                "Simple regex only for safety: no groups `()`/alternation `|`/backrefs, "
                "max pattern length 100, max repeat 1000."
            )
        with link_col:
            st.markdown("💡 [regex101](https://regex101.com/)")
    st.markdown("---")

    if mode == "Single file":
        st.header("Upload PDF")
        uploaded_file = st.file_uploader(
            "Choose a PDF file", type="pdf", label_visibility="collapsed"
        )
        st.markdown("---")
        if use_regex:
            st.markdown(
                "**How to use (Regex)**\n"
                "1. Enter a regular expression above.\n"
                "2. Upload a PDF with tables.\n"
                "3. Download matching values per table\n"
                "   or as a single combined CSV."
            )
        else:
            st.markdown(
                "**How to use**\n"
                "1. Upload a PDF with tables.\n"
                "2. Uncheck columns or rows you don't need.\n"
                "3. Download a single table as CSV, or use\n"
                "   *Download All Selected Tables* to combine them."
            )
    else:
        uploaded_file = None
        st.header("Upload PDFs")
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type="pdf",
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        st.markdown("---")
        if use_regex:
            st.markdown(
                "**How to use (Regex + Bulk)**\n"
                "1. Enter a regular expression above.\n"
                "2. Upload one or more PDFs with tables.\n"
                "3. Download matching values per file\n"
                "   or as a single combined CSV."
            )
        else:
            st.markdown(
                "**How to use (Bulk)**\n"
                "1. Upload one or more PDFs with tables.\n"
                "2. Each file is processed automatically.\n"
                "3. Download per-file CSVs, or use\n"
                "   *Download All Tables* to combine everything."
            )

# ── Cached helpers ────────────────────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def _cached_extract(file_bytes: bytes):
    return extract_tables_from_pdf(io.BytesIO(file_bytes))


@st.cache_data(show_spinner=False)
def _cached_raw_ocr(file_bytes: bytes) -> pd.DataFrame | None:
    return get_raw_ocr_data(io.BytesIO(file_bytes))


# ── Shared helper: process one file in regex mode ─────────────────────────────


def _process_file_regex(
    file_bytes: bytes,
    file_label: str,
    pattern: str,
    download_key: str,
) -> list[pd.DataFrame]:
    """Extract regex matches from every table in a single PDF.

    Displays per-table match counts and a per-file download button.
    Returns a list of non-empty match DataFrames for the caller to accumulate
    into a combined download.
    """
    tables, method = _cached_extract(file_bytes)

    if method == "ocr":
        st.info("ℹ️ No selectable text found — tables extracted via OCR.")

    if not tables:
        st.warning(
            "No tables were detected in this PDF. "
            "Make sure the file contains structured table data, "
            "or that the text is legible enough for OCR."
        )
        return []

    file_parts: list[pd.DataFrame] = []
    regex_error: str | None = None

    for idx, (page_num, table_idx, df) in enumerate(tables):
        table_id = f"{file_label}_table_{idx + 1}_page_{page_num}"
        matches_df, regex_error = extract_regex_matches(df, table_id, pattern)
        if regex_error is not None:
            break
        if not matches_df.empty:
            file_parts.append(matches_df)

    if regex_error is not None:
        st.error(
            f"⚠️ Invalid or unsafe regular expression: {regex_error}  "
            "— visit [regex101.com](https://regex101.com/) for help."
        )
        return []

    if not file_parts:
        st.warning("No matches found.")
        return []

    file_matches_df = pd.concat(file_parts, ignore_index=True)
    st.success(f"Found **{len(file_matches_df)}** match(es) across {len(tables)} table(s).")
    file_csv = file_matches_df.to_csv(index=False).encode("utf-8")
    file_stem = pathlib.Path(file_label).stem
    st.download_button(
        label=f"⬇ Download matches from {file_label}",
        data=file_csv,
        file_name=f"{file_stem}_matches.csv",
        mime="text/csv",
        key=download_key,
    )
    return file_parts


# ── Main area ─────────────────────────────────────────────────────────────────
if mode == "Single file":
    if uploaded_file is None:
        st.info("Upload a PDF in the sidebar to get started.")
    else:
        file_bytes = uploaded_file.getvalue()

        if use_regex:
            # ── Regex mode: global pattern over all tables ────────────────
            if not regex_pattern:
                st.info("Enter a regular expression in the sidebar to filter results.")
            else:
                with st.spinner("Extracting tables and applying regex filter…"):
                    all_parts = _process_file_regex(
                        file_bytes,
                        pathlib.Path(uploaded_file.name).stem,
                        regex_pattern,
                        "download_regex_single",
                    )

                if all_parts:
                    combined_df = pd.concat(all_parts, ignore_index=True)
                    combined_csv = combined_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇ Download All Matches as CSV",
                        data=combined_csv,
                        file_name="regex_matches.csv",
                        mime="text/csv",
                        key="download_regex_all",
                    )

        else:
            # ── Normal single-file mode ───────────────────────────────────
            with st.spinner("Extracting tables from PDF…"):
                tables, method = _cached_extract(file_bytes)

            if method == "ocr":
                st.info("ℹ️ No selectable text found — tables extracted via OCR.")
                with st.spinner("Extracting tables using OCR…"):
                    raw_df = _cached_raw_ocr(file_bytes)
                if raw_df is not None:
                    raw_csv = raw_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇ Get Raw OCR Output",
                        data=raw_csv,
                        file_name="raw_ocr_output.csv",
                        mime="text/csv",
                        key="download_raw_ocr",
                    )

            if not tables:
                st.warning(
                    "No tables were detected in this PDF. "
                    "Make sure the file contains structured table data, "
                    "or that the text is legible enough for OCR."
                )
            else:
                st.success(f"Found **{len(tables)}** table(s). Edit selections below, then download.")

                # Collect (tableID, final_df) pairs from selected tables for combined download.
                combined_parts: list[pd.DataFrame] = []

                for idx, (page_num, table_idx, df) in enumerate(tables):
                    st.subheader(f"Table {idx + 1}  ·  Page {page_num}")

                    # ── Table-level inclusion toggle ──────────────────────────────
                    table_included = st.checkbox(
                        "Include in combined download",
                        value=True,
                        key=f"table_included_{idx}",
                    )

                    # ── Column selection ──────────────────────────────────────────
                    st.markdown("**Columns to include:**")
                    all_cols = df.columns.tolist()

                    # "Check All / Check None" buttons for columns
                    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
                    with col_btn1:
                        if st.button("Check All", key=f"check_all_cols_{idx}"):
                            for i in range(len(all_cols)):
                                st.session_state[f"col_{idx}_{i}"] = True
                    with col_btn2:
                        if st.button("Check None", key=f"check_none_cols_{idx}"):
                            for i in range(len(all_cols)):
                                st.session_state[f"col_{idx}_{i}"] = False

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

                    final_df: pd.DataFrame | None = None

                    if not selected_cols:
                        st.info("Select at least one column to see a preview.")
                    else:
                        # ── Row selection via editable table ─────────────────────
                        df_edit = df[selected_cols].copy()

                        # Determine the default Include value based on any row override.
                        _rows_key = f"rows_include_{idx}"
                        include_default: bool = st.session_state.get(_rows_key, True)
                        df_edit.insert(0, "Include", include_default)

                        # "Check All / Check None" buttons for rows
                        row_btn1, row_btn2, _ = st.columns([1, 1, 4])
                        with row_btn1:
                            if st.button("Check All", key=f"check_all_rows_{idx}"):
                                st.session_state[_rows_key] = True
                                st.session_state.pop(f"editor_{idx}", None)
                                st.rerun()
                        with row_btn2:
                            if st.button("Check None", key=f"check_none_rows_{idx}"):
                                st.session_state[_rows_key] = False
                                st.session_state.pop(f"editor_{idx}", None)
                                st.rerun()

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

                        # ── Per-table download ────────────────────────────────────
                        csv_bytes = final_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label=f"⬇ Download Table {idx + 1} as CSV",
                            data=csv_bytes,
                            file_name=f"table_{idx + 1}_page_{page_num}.csv",
                            mime="text/csv",
                            key=f"download_{idx}",
                        )

                    # Accumulate for combined download when the table is selected.
                    if table_included and final_df is not None and len(final_df) > 0:
                        stamped = final_df.copy()
                        stamped.insert(0, "tableID", f"table_{idx + 1}_page_{page_num}")
                        combined_parts.append(stamped)

                    st.markdown("---")

                # ── Combined download ─────────────────────────────────────────────
                if combined_parts:
                    combined_df = pd.concat(combined_parts, ignore_index=True)
                    combined_csv = combined_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇ Download All Selected Tables as CSV",
                        data=combined_csv,
                        file_name="all_tables.csv",
                        mime="text/csv",
                        key="download_all",
                    )

else:  # Bulk processing
    if not uploaded_files:
        st.info("Upload one or more PDFs in the sidebar to get started.")
    else:
        all_bulk_parts: list[pd.DataFrame] = []

        if use_regex and regex_pattern:
            # ── Regex mode: extract matches from every file ───────────────
            for file_idx, bulk_file in enumerate(uploaded_files):
                file_bytes = bulk_file.getvalue()
                file_name = bulk_file.name

                st.subheader(f"📄 {file_name}")
                with st.spinner(f"Extracting tables from {file_name}…"):
                    parts = _process_file_regex(
                        file_bytes,
                        file_name,
                        regex_pattern,
                        f"download_bulk_regex_{file_idx}",
                    )
                all_bulk_parts.extend(parts)
                st.markdown("---")

            if all_bulk_parts:
                combined_df = pd.concat(all_bulk_parts, ignore_index=True)
                combined_csv = combined_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇ Download All Matches as CSV",
                    data=combined_csv,
                    file_name="regex_matches_bulk.csv",
                    mime="text/csv",
                    key="download_regex_bulk_all",
                )

        elif use_regex and not regex_pattern:
            st.info("Enter a regular expression in the sidebar to filter results.")

        else:
            # ── Normal bulk mode ──────────────────────────────────────────
            for file_idx, bulk_file in enumerate(uploaded_files):
                file_bytes = bulk_file.getvalue()
                file_name = bulk_file.name

                st.subheader(f"📄 {file_name}")

                with st.spinner(f"Extracting tables from {file_name}…"):
                    tables, method = _cached_extract(file_bytes)

                if method == "ocr":
                    st.info("ℹ️ No selectable text found — tables extracted via OCR.")

                if not tables:
                    st.warning(
                        "No tables were detected in this PDF. "
                        "Make sure the file contains structured table data, "
                        "or that the text is legible enough for OCR."
                    )
                else:
                    st.success(f"Found **{len(tables)}** table(s) using {method}.")

                    file_parts: list[pd.DataFrame] = []
                    for idx, (page_num, table_idx, df) in enumerate(tables):
                        stamped = df.copy()
                        table_id = f"{file_name}_table_{idx + 1}_page_{page_num}"
                        stamped.insert(0, "tableID", table_id)
                        file_parts.append(stamped)

                    if file_parts:
                        file_df = pd.concat(file_parts, ignore_index=True)
                        file_csv = file_df.to_csv(index=False).encode("utf-8")
                        file_stem = pathlib.Path(file_name).stem
                        st.download_button(
                            label=f"⬇ Download tables from {file_name}",
                            data=file_csv,
                            file_name=f"{file_stem}_tables.csv",
                            mime="text/csv",
                            key=f"download_bulk_{file_idx}",
                        )
                        all_bulk_parts.extend(file_parts)

                st.markdown("---")

            # ── Combined download for all files ───────────────────────────────────
            if all_bulk_parts:
                combined_df = pd.concat(all_bulk_parts, ignore_index=True)
                combined_csv = combined_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇ Download All Tables as CSV",
                    data=combined_csv,
                    file_name="all_tables_bulk.csv",
                    mime="text/csv",
                    key="download_all_bulk",
                )

st.markdown(
    '<p class="hornfels-link">Powered by '
    f'<a href="{HORNFELS_URL}" target="_blank" rel="noopener noreferrer">Hornfels Consulting</a>'
    "</p>",
    unsafe_allow_html=True,
)
#add footer with disclaimer about OCR limitations and link to Hornfels website

st.image("https://img.shields.io/badge/License-MIT-yellow.svg", width=64, link="https://opensource.org/licenses/MIT")
st.markdown(
    """
    Use at your own risk and benefit. No warranty or liability is implied or expressly granted. Your data is not shared, stored, or usable in any way except by you.  Aim away from face.  Keep out of reach of children.  Never end a sentence with a preposition.
    OCR-based extraction may have limitations in accuracy, especially with complex layouts or low-quality scans. Always review the extracted data for errors.
    """,
)
