"""Utility helpers for the Digitize Images application."""

import re

import pandas as pd


def extract_regex_matches(
    df: pd.DataFrame, table_id: str, pattern: str
) -> tuple[pd.DataFrame, str | None]:
    """Extract individual cell values from *df* that match *pattern*.

    Each cell is converted to a string before matching. A cell is included
    in the result when the pattern has at least one match anywhere in the
    cell's string representation.

    Parameters
    ----------
    df:
        DataFrame whose cells will be searched.
    table_id:
        Identifier stamped into the ``tableID`` column of every result row.
    pattern:
        Regular expression pattern to search for in each cell.

    Returns
    -------
    tuple[pd.DataFrame, str | None]
        ``(matches_df, None)`` on success – *matches_df* has columns
        ``["tableID", "match"]`` with one row per matching cell value.
        ``(empty_df, error_message)`` when *pattern* is not a valid regular
        expression so the caller can surface an appropriate error to the user.
    """
    empty = pd.DataFrame(columns=["tableID", "match"])
    try:
        compiled = re.compile(pattern)
        rows = [
            {"tableID": table_id, "match": val}
            for col in df.columns
            for val in df[col].astype(str)
            if compiled.search(val)
        ]
        return (pd.DataFrame(rows) if rows else empty), None
    except re.error as exc:
        return empty, str(exc)
