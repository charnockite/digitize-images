import pandas as pd
import pdfplumber
import streamlit as st

LOGO_PATH = "hornfels_250x250.png"
HORNFELS_URL = "https://hornfelsconsulting.com"

# A valid table must have at least a header row and one data row.
MIN_TABLE_ROWS = 2
# Maximum number of column-checkboxes to display per row in the UI.
MAX_COLUMNS_PER_ROW = 6
# Only the first N pages of a PDF are processed to avoid Streamlit hanging on large files.
MAX_PDF_PAGES = 10

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


def extract_tables_from_pdf(file) -> tuple[list[tuple[int, int, pd.DataFrame]], bool]:
    """Return extracted tables and a flag indicating whether the PDF was truncated.

    Only the first MAX_PDF_PAGES pages are processed to prevent Streamlit from
    hanging on large files.  The returned bool is True when the PDF contained
    more pages than the limit.
    """
    tables = []
    truncated = False
    with pdfplumber.open(file) as pdf:
        if len(pdf.pages) > MAX_PDF_PAGES:
            truncated = True
        pages_to_process = pdf.pages[:MAX_PDF_PAGES]
        for page_num, page in enumerate(pages_to_process, start=1):
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
    return tables, truncated


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
        tables, truncated = extract_tables_from_pdf(uploaded_file)

    if truncated:
        st.warning(
            f"This PDF has more than {MAX_PDF_PAGES} pages. "
            f"Only the first {MAX_PDF_PAGES} pages were processed to keep the app responsive."
        )

    if not tables:
        st.warning(
            "No tables were detected in this PDF. "
            "Make sure the file contains structured table data."
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
                    use_container_width=True,
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
