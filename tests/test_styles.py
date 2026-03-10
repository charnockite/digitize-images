"""Tests for the styles module."""

import pathlib
from unittest.mock import call, patch

import pytest

import styles


# ── Colour token tests ────────────────────────────────────────────────────────


def test_colour_constants_are_hex_strings():
    """All exported colour tokens should be non-empty hex colour strings."""
    for name in ("DARK_GREEN", "ACCENT_GOLD", "WHITE", "LIGHT_BG"):
        value = getattr(styles, name)
        assert isinstance(value, str), f"{name} should be a str"
        assert value.startswith("#"), f"{name} should start with '#'"
        assert len(value) == 7, f"{name} should be a 6-digit hex colour (e.g. #RRGGBB)"


def test_colour_values():
    """Colour tokens must match the Hornfels brand palette."""
    assert styles.DARK_GREEN == "#1B3C33"
    assert styles.ACCENT_GOLD == "#C68D40"
    assert styles.WHITE == "#FFFFFF"
    assert styles.LIGHT_BG == "#F0F4F2"


# ── CSS file tests ────────────────────────────────────────────────────────────


def test_css_file_exists():
    """styles.css must exist alongside styles.py."""
    css_path = pathlib.Path(styles.__file__).parent / "styles.css"
    assert css_path.is_file(), "styles.css not found"


def test_css_file_is_non_empty():
    """styles.css must contain at least some CSS."""
    css_path = pathlib.Path(styles.__file__).parent / "styles.css"
    content = css_path.read_text(encoding="utf-8")
    assert len(content) > 0, "styles.css is empty"


def test_css_file_contains_brand_colours():
    """styles.css should reference the brand colour tokens."""
    css_path = pathlib.Path(styles.__file__).parent / "styles.css"
    content = css_path.read_text(encoding="utf-8")
    assert styles.DARK_GREEN.lower() in content.lower()
    assert styles.ACCENT_GOLD.lower() in content.lower()


# ── apply_custom_css ──────────────────────────────────────────────────────────


def test_apply_custom_css_calls_st_markdown():
    """apply_custom_css() should inject a <style> block via st.markdown."""
    with patch("styles.st") as mock_st:
        styles.apply_custom_css()

    mock_st.markdown.assert_called_once()
    args, kwargs = mock_st.markdown.call_args
    injected = args[0]
    assert "<style>" in injected
    assert "</style>" in injected
    assert kwargs.get("unsafe_allow_html") is True


# ── render_divider ────────────────────────────────────────────────────────────


def test_render_divider_calls_st_markdown():
    """render_divider() should emit an <hr> with the hornfels-divider class."""
    with patch("styles.st") as mock_st:
        styles.render_divider()

    mock_st.markdown.assert_called_once()
    args, kwargs = mock_st.markdown.call_args
    html = args[0]
    assert "hornfels-divider" in html
    assert kwargs.get("unsafe_allow_html") is True


# ── render_footer ─────────────────────────────────────────────────────────────


def test_render_footer_contains_url():
    """render_footer() should include the provided URL in the emitted HTML."""
    test_url = "https://example.com"
    with patch("styles.st") as mock_st:
        styles.render_footer(test_url)

    mock_st.markdown.assert_called_once()
    args, kwargs = mock_st.markdown.call_args
    html = args[0]
    assert test_url in html
    assert "hornfels-link" in html
    assert kwargs.get("unsafe_allow_html") is True


def test_render_footer_opens_in_new_tab():
    """render_footer() link should open in a new tab for security."""
    with patch("styles.st") as mock_st:
        styles.render_footer("https://hornfelsconsulting.com")

    args, _ = mock_st.markdown.call_args
    html = args[0]
    assert 'target="_blank"' in html
    assert "noopener" in html
