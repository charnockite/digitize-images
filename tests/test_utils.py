"""Tests for the utils module."""

import pandas as pd
import pytest

from utils import apply_regex_filter


@pytest.fixture()
def sample_df():
    return pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "Charlie", "Dave"],
            "Score": ["90", "75", "88", "62"],
            "Label": ["pass", "fail", "pass", "fail"],
        }
    )


# ---------------------------------------------------------------------------
# apply_regex_filter – basic matching
# ---------------------------------------------------------------------------


def test_regex_filter_matching_rows(sample_df):
    """Rows where any cell matches the pattern are returned."""
    result, err = apply_regex_filter(sample_df, "Alice")
    assert err is None
    assert len(result) == 1
    assert result.iloc[0]["Name"] == "Alice"


def test_regex_filter_multiple_matches(sample_df):
    """Multiple matching rows are all returned."""
    result, err = apply_regex_filter(sample_df, "pass")
    assert err is None
    assert len(result) == 2
    assert list(result["Name"]) == ["Alice", "Charlie"]


def test_regex_filter_case_sensitive(sample_df):
    """Matching is case-sensitive by default."""
    result_upper, _ = apply_regex_filter(sample_df, "ALICE")
    result_lower, _ = apply_regex_filter(sample_df, "alice")
    assert len(result_upper) == 0
    assert len(result_lower) == 0


def test_regex_filter_case_insensitive_flag(sample_df):
    """Inline (?i) flag enables case-insensitive matching."""
    result, err = apply_regex_filter(sample_df, "(?i)alice")
    assert err is None
    assert len(result) == 1


def test_regex_filter_anchored_pattern(sample_df):
    """Anchored patterns (^ / $) work correctly."""
    result, err = apply_regex_filter(sample_df, r"^9")  # Score starts with 9
    assert err is None
    assert len(result) == 1
    assert result.iloc[0]["Name"] == "Alice"


def test_regex_filter_matches_across_columns(sample_df):
    """Pattern that matches in any column causes the row to be included."""
    # '62' appears in Score column for Dave
    result, err = apply_regex_filter(sample_df, "62")
    assert err is None
    assert len(result) == 1
    assert result.iloc[0]["Name"] == "Dave"


def test_regex_filter_no_match_returns_empty(sample_df):
    """When no row matches, an empty DataFrame is returned."""
    result, err = apply_regex_filter(sample_df, "xyz_no_match")
    assert err is None
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_regex_filter_index_is_reset(sample_df):
    """Returned DataFrame has a reset (0-based) index."""
    result, err = apply_regex_filter(sample_df, "pass")
    assert err is None
    assert list(result.index) == list(range(len(result)))


# ---------------------------------------------------------------------------
# apply_regex_filter – invalid pattern handling
# ---------------------------------------------------------------------------


def test_regex_filter_invalid_pattern_returns_original(sample_df):
    """An invalid regex returns the original DataFrame unchanged."""
    result, err = apply_regex_filter(sample_df, "[invalid")
    assert err is not None
    pd.testing.assert_frame_equal(result, sample_df)


def test_regex_filter_invalid_pattern_returns_error_string(sample_df):
    """An invalid regex returns a non-empty error message string."""
    _, err = apply_regex_filter(sample_df, "(unclosed")
    assert isinstance(err, str)
    assert len(err) > 0


def test_regex_filter_valid_pattern_returns_no_error(sample_df):
    """A valid regex returns None as the error value."""
    _, err = apply_regex_filter(sample_df, r"\d+")
    assert err is None


# ---------------------------------------------------------------------------
# apply_regex_filter – edge cases
# ---------------------------------------------------------------------------


def test_regex_filter_empty_dataframe():
    """An empty DataFrame in returns an empty DataFrame out."""
    empty_df = pd.DataFrame({"A": [], "B": []})
    result, err = apply_regex_filter(empty_df, "anything")
    assert err is None
    assert len(result) == 0


def test_regex_filter_numeric_column():
    """Numeric column values are coerced to strings before matching."""
    df = pd.DataFrame({"value": [100, 200, 300]})
    result, err = apply_regex_filter(df, "200")
    assert err is None
    assert len(result) == 1
    assert result.iloc[0]["value"] == 200


def test_regex_filter_all_rows_match(sample_df):
    """When every row matches, all rows are returned."""
    result, err = apply_regex_filter(sample_df, r"\w+")  # matches any word char
    assert err is None
    assert len(result) == len(sample_df)
