import streamlit as st

from table_extractor import extract_tables_from_pdf

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
        "3. Download the filtered table as CSV."
    )

# ── Main area ─────────────────────────────────────────────────────────────────
if uploaded_file is None:
    st.info("Upload a PDF in the sidebar to get started.")
else:
    with st.spinner("Extracting tables from PDF…"):
        tables = extract_tables_from_pdf(uploaded_file)

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
