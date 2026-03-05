import streamlit as st

LOGO_PATH = "hornfels_250x250.png"
HORNFELS_URL = "https://hornfelsconsulting.com"

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
    st.title("App title")

st.markdown('<hr class="hornfels-divider">', unsafe_allow_html=True)

st.write("Hello World")

st.markdown(
    '<p class="hornfels-link">Powered by '
    f'<a href="{HORNFELS_URL}" target="_blank" rel="noopener noreferrer">Hornfels Consulting</a>'
    "</p>",
    unsafe_allow_html=True,
)
