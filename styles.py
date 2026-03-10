"""
Centralised theming and styling for the Digitize Images Streamlit app.

All colour tokens, CSS, and helpers that touch visual presentation live here
so that app.py can focus exclusively on application logic.
"""

import pathlib

import streamlit as st

# ── Brand colour tokens ───────────────────────────────────────────────────────

DARK_GREEN = "#1B3C33"
ACCENT_GOLD = "#C68D40"
WHITE = "#FFFFFF"
LIGHT_BG = "#F0F4F2"

# ── CSS loader ────────────────────────────────────────────────────────────────

_CSS_PATH = pathlib.Path(__file__).parent / "styles.css"


def apply_custom_css() -> None:
    """Inject the project-level CSS into the current Streamlit page."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ── Reusable HTML components ──────────────────────────────────────────────────


def render_divider() -> None:
    """Render the branded horizontal divider below the page header."""
    st.markdown('<hr class="hornfels-divider">', unsafe_allow_html=True)


def render_footer(url: str) -> None:
    """Render the branded footer with a link to *url*."""
    st.markdown(
        '<p class="hornfels-link">Powered by '
        f'<a href="{url}" target="_blank" rel="noopener noreferrer">Hornfels Consulting</a>'
        "</p>",
        unsafe_allow_html=True,
    )
