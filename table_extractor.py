import pandas as pd
import pdfplumber

# A valid table must have at least a header row and one data row.
MIN_TABLE_ROWS = 2


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


def extract_tables_from_pdf(file) -> list[tuple[int, int, pd.DataFrame]]:
    """Return a list of (page_number, table_index, DataFrame) for every table found."""
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
