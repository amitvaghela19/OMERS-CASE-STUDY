from pathlib import Path

import streamlit as st

from omers.clean import clean_workbook
from omers.store import DATA, db_ready, ingest_frames

ROOT = Path(__file__).resolve().parent
DEFAULT = ROOT / "Test Case.xlsx"
LOGO = ROOT / "assets" / "oxford-logo.svg"
FAVICON = ROOT / "assets" / "oxford-favicon.svg"

st.set_page_config(
    page_title="Oxford Properties",
    page_icon=str(FAVICON),
    layout="wide",
)
st.logo(str(LOGO), icon_image=str(FAVICON), size="large")
st.markdown(
    """
    <style>
    [data-testid="stSidebarLogo"] {
        height: 32px;
        width: auto;
    }
    [data-testid="stSidebarHeader"] {
        align-items: center;
        padding: 8px 4px 4px 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _load_default() -> None:
    frames, notes = clean_workbook(DEFAULT)
    ingest_frames(frames)
    st.session_state.loaded = True
    st.session_state.source_name = DEFAULT.name
    st.session_state.clean_notes = notes


if "loaded" not in st.session_state:
    if db_ready():
        st.session_state.loaded = True
        st.session_state.source_name = "cleaned database"
        st.session_state.clean_notes = ["Using the cleaned database already on disk."]
    elif DEFAULT.exists():
        _load_default()
    else:
        st.session_state.loaded = False
        st.session_state.source_name = ""
        st.session_state.clean_notes = []

with st.sidebar:
    st.subheader("Workbook")
    st.caption("Upload Test Case.xlsx or another file with the same sheets and columns. The file is cleaned before the pages refresh.")
    upload = st.file_uploader("Workbook", type=["xlsx"], label_visibility="collapsed")
    if upload is not None:
        token = f"{upload.name}:{upload.size}"
        if st.session_state.get("upload_token") != token:
            try:
                frames, notes = clean_workbook(upload)
                ingest_frames(frames)
            except Exception as exc:
                st.error(str(exc))
            else:
                st.session_state.upload_token = token
                st.session_state.loaded = True
                st.session_state.source_name = upload.name
                st.session_state.clean_notes = notes
                st.rerun()
    if DEFAULT.exists() and st.button("Reload Test Case.xlsx"):
        _load_default()
        st.session_state.upload_token = None
        st.rerun()
    if st.session_state.get("source_name"):
        st.write(f"Loaded: {st.session_state.source_name}")
    for note in st.session_state.get("clean_notes", []):
        st.caption(note)
    if (DATA / "cleaned_workbook.xlsx").exists():
        st.caption("Cleaned workbook: data/cleaned_workbook.xlsx")

pages = [
    st.Page(str(ROOT / "app_pages" / "portfolio.py"), title="Portfolio performance", icon=":material/monitoring:", default=True),
    st.Page(str(ROOT / "app_pages" / "equity.py"), title="Equity movements", icon=":material/waterfall_chart:"),
    st.Page(str(ROOT / "app_pages" / "findings.py"), title="Key findings", icon=":material/insights:"),
    st.Page(str(ROOT / "app_pages" / "sql_lab.py"), title="SQL", icon=":material/database:"),
    st.Page(str(ROOT / "app_pages" / "chat.py"), title="Chat", icon=":material/chat:"),
]
st.navigation(pages).run()
