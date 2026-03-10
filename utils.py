"""Utility helpers for the Digitize Images application."""

import re

import pandas as pd

MAX_REGEX_LENGTH = 100
MAX_REGEX_REPEAT = 1000


def _validate_safe_regex(pattern: str) -> str | None:
    """Return an error message when *pattern* is too complex for safe matching."""
    if not pattern:
        return "Pattern cannot be empty."

    if len(pattern) > MAX_REGEX_LENGTH:
        return f"Pattern is too long (max {MAX_REGEX_LENGTH} characters)."

    body = pattern
    if body.startswith("(?i)"):
        body = body[4:]

    escaped = False
    in_class = False
    idx = 0
    while idx < len(body):
        ch = body[idx]

        if escaped:
            if ch.isdigit():
                return "Backreferences are not allowed."
            escaped = False
            idx += 1
            continue

        if ch == "\\":
            escaped = True
            idx += 1
            continue

        if in_class:
            if ch == "]":
                in_class = False
            idx += 1
            continue

        if ch == "[":
            in_class = True
            idx += 1
            continue

        if ch in {"(", ")", "|"}:
            return "Grouping and alternation are not allowed."

        if ch == "{":
            close = body.find("}", idx + 1)
            if close == -1:
                return None
            quant = body[idx + 1 : close].strip()
            if quant:
                parts = [p.strip() for p in quant.split(",")]
                if len(parts) > 2 or any((p and not p.isdigit()) for p in parts):
                    return "Invalid repetition quantifier."
                nums = [int(p) for p in parts if p]
                if nums and max(nums) > MAX_REGEX_REPEAT:
                    return f"Repetition quantifier too large (max {MAX_REGEX_REPEAT})."
            idx = close + 1
            continue

        idx += 1

    if in_class:
        return "Unclosed character class."

    return None


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
    safety_error = _validate_safe_regex(pattern)
    if safety_error is not None:
        return empty, safety_error

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
