"""Utility helpers for the Digitize Images application."""

import re

import pandas as pd


def apply_regex_filter(df: pd.DataFrame, pattern: str) -> tuple[pd.DataFrame, str | None]:
    """Filter rows in *df* where any cell contains a match for *pattern*.

    Each cell is converted to a string before matching, so numeric and other
    typed columns are handled transparently.

    Parameters
    ----------
    df:
        DataFrame whose rows will be filtered.
    pattern:
        Regular expression pattern to search for in each row.

    Returns
    -------
    tuple[pd.DataFrame, str | None]
        ``(filtered_df, None)`` on success – *filtered_df* contains only the
        rows where at least one cell matched *pattern*, with the index reset.
        ``(df, error_message)`` when *pattern* is not a valid regular
        expression so the caller can surface an appropriate error to the user.
    """
    try:
        mask = df.apply(
            lambda row: row.astype(str).str.contains(pattern, regex=True, na=False).any(),
            axis=1,
        )
        return df[mask].reset_index(drop=True), None
    except re.error as exc:
        return df, str(exc)
