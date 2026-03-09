"""Tests for the utils module."""

import pandas as pd
import pytest

from utils import extract_regex_matches


@pytest.fixture()
def sample_df():
    return pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "Charlie", "Dave"],
            "Score": ["90", "75", "88", "62"],
            "Label": ["pass", "fail", "pass", "fail"],
        }
    )


TABLE_ID = "table_1_page_1"


# ---------------------------------------------------------------------------
# extract_regex_matches – basic matching
# ---------------------------------------------------------------------------


def test_regex_matches_basic(sample_df):
    """A cell containing the pattern is returned as a match row."""
    result, err = extract_regex_matches(sample_df, TABLE_ID, "Alice")
    assert err is None
    assert len(result) == 1
    assert result.iloc[0]["match"] == "Alice"
    assert result.iloc[0]["tableID"] == TABLE_ID


def test_regex_matches_multiple(sample_df):
    """Multiple matching cells are all returned."""
    result, err = extract_regex_matches(sample_df, TABLE_ID, "pass")
    assert err is None
    assert len(result) == 2
    assert list(result["match"]) == ["pass", "pass"]


def test_regex_matches_case_sensitive(sample_df):
    """Matching is case-sensitive by default."""
    result_upper, _ = extract_regex_matches(sample_df, TABLE_ID, "ALICE")
    result_lower, _ = extract_regex_matches(sample_df, TABLE_ID, "alice")
    assert len(result_upper) == 0
    assert len(result_lower) == 0


def test_regex_matches_case_insensitive_flag(sample_df):
    """Inline (?i) flag enables case-insensitive matching."""
    result, err = extract_regex_matches(sample_df, TABLE_ID, "(?i)alice")
    assert err is None
    assert len(result) == 1
    assert result.iloc[0]["match"] == "Alice"


def test_regex_matches_anchored_pattern(sample_df):
    """Anchored patterns (^ / $) work correctly."""
    result, err = extract_regex_matches(sample_df, TABLE_ID, r"^9")  # Score starts with 9
    assert err is None
    assert len(result) == 1
    assert result.iloc[0]["match"] == "90"


def test_regex_matches_no_match_returns_empty(sample_df):
    """When nothing matches, an empty DataFrame with correct columns is returned."""
    result, err = extract_regex_matches(sample_df, TABLE_ID, "xyz_no_match")
    assert err is None
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["tableID", "match"]
    assert len(result) == 0


def test_regex_matches_columns_are_tableID_and_match(sample_df):
    """Returned DataFrame always has exactly [tableID, match] columns."""
    result, err = extract_regex_matches(sample_df, TABLE_ID, "Alice")
    assert err is None
    assert list(result.columns) == ["tableID", "match"]


def test_regex_matches_table_id_stamped(sample_df):
    """tableID column contains the provided table identifier."""
    custom_id = "table_3_page_7"
    result, err = extract_regex_matches(sample_df, custom_id, r"\d+")
    assert err is None
    assert (result["tableID"] == custom_id).all()


# ---------------------------------------------------------------------------
# extract_regex_matches – invalid pattern handling
# ---------------------------------------------------------------------------


def test_regex_matches_invalid_pattern_returns_empty(sample_df):
    """An invalid regex returns an empty DataFrame with correct columns."""
    result, err = extract_regex_matches(sample_df, TABLE_ID, "[invalid")
    assert err is not None
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["tableID", "match"]
    assert len(result) == 0


def test_regex_matches_invalid_pattern_returns_error_string(sample_df):
    """An invalid regex returns a non-empty error message string."""
    _, err = extract_regex_matches(sample_df, TABLE_ID, "(unclosed")
    assert isinstance(err, str)
    assert len(err) > 0


def test_regex_matches_valid_pattern_returns_no_error(sample_df):
    """A valid regex returns None as the error value."""
    _, err = extract_regex_matches(sample_df, TABLE_ID, r"\d+")
    assert err is None


# ---------------------------------------------------------------------------
# extract_regex_matches – edge cases
# ---------------------------------------------------------------------------


def test_regex_matches_empty_dataframe():
    """An empty DataFrame in returns an empty DataFrame out."""
    empty_df = pd.DataFrame({"A": [], "B": []})
    result, err = extract_regex_matches(empty_df, TABLE_ID, "anything")
    assert err is None
    assert len(result) == 0
    assert list(result.columns) == ["tableID", "match"]


def test_regex_matches_numeric_column():
    """Numeric column values are coerced to strings before matching."""
    df = pd.DataFrame({"value": [100, 200, 300]})
    result, err = extract_regex_matches(df, TABLE_ID, "200")
    assert err is None
    assert len(result) == 1
    assert result.iloc[0]["match"] == "200"


def test_regex_matches_all_cells_match(sample_df):
    """When every cell matches, all cells are returned."""
    result, err = extract_regex_matches(sample_df, TABLE_ID, r"\w+")
    assert err is None
    # 4 rows × 3 columns = 12 cells all contain word characters
    assert len(result) == 4 * 3
