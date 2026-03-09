import io

import pandas as pd
import streamlit as st

from table_extractor import extract_tables_from_pdf, get_raw_ocr_data

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
with st.sidebar:
    st.header("Upload PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", label_visibility="collapsed")
    st.markdown("---")
    st.markdown(
        "**How to use**\n"
        "1. Upload a PDF with tables.\n"
        "2. Uncheck columns or rows you don't need.\n"
        "3. Download a single table as CSV, or use\n"
        "   *Download All Selected Tables* to combine them."
    )

# ── Cached helpers ────────────────────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def _cached_extract(file_bytes: bytes):
    return extract_tables_from_pdf(io.BytesIO(file_bytes))


@st.cache_data(show_spinner=False)
def _cached_raw_ocr(file_bytes: bytes) -> pd.DataFrame | None:
    return get_raw_ocr_data(io.BytesIO(file_bytes))


# ── Main area ─────────────────────────────────────────────────────────────────
if uploaded_file is None:
    st.info("Upload a PDF in the sidebar to get started.")
else:
    file_bytes = uploaded_file.getvalue()

    with st.spinner("Extracting tables from PDF…"):
        tables, method = _cached_extract(file_bytes)

    if method == "ocr":
        st.info("ℹ️ No selectable text found — tables extracted via OCR.")
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

st.markdown(
    '<p class="hornfels-link">Powered by '
    f'<a href="{HORNFELS_URL}" target="_blank" rel="noopener noreferrer">Hornfels Consulting</a>'
    "</p>",
    unsafe_allow_html=True,
)
