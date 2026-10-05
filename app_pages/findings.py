import html
import re

import streamlit as st

from omers.findings import build_findings
from omers.store import load_tables

_NEGATIVE = re.compile(r"(-\$[\d,]+(?:\.\d+)?(?:bn|M)?|-[\d,]+\.\d+%)")

st.markdown(
    """
    <style>
    .kf-title, .kf-subtitle, .kf-body {
      font-family: "Segoe UI", sans-serif;
      text-align: justify;
      color: #252423;
    }
    p.kf-title {
      font-size: 1.35rem !important;
      font-weight: 600;
      line-height: 1.35;
      color: #0B3A5B;
      margin: 0 0 0.85rem 0;
    }
    p.kf-subtitle {
      font-size: 1.05rem !important;
      font-weight: 600;
      line-height: 1.4;
      color: #0B3A5B;
      margin: 0.85rem 0 0.2rem 0;
    }
    p.kf-body {
      font-size: 1rem !important;
      font-weight: 400;
      line-height: 1.6;
      margin: 0;
    }
    .kf-body .neg, .kf-title .neg { color: #A4262C; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.header("Key findings")
st.markdown(
    '<p class="kf-body">Prepared from the loaded case-study workbook. The figures below are not a live company result.</p>',
    unsafe_allow_html=True,
)

if not st.session_state.get("loaded"):
    st.warning("Upload a workbook in the sidebar to load the dashboard.")
    st.stop()


def _report(text: str) -> str:
    safe = html.escape(text)
    return _NEGATIVE.sub(r'<span class="neg">\1</span>', safe)


for finding in build_findings(load_tables()):
    with st.container(border=True):
        st.markdown(f'<p class="kf-title">{_report(finding["title"])}</p>', unsafe_allow_html=True)
        st.markdown('<p class="kf-subtitle">Observation</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="kf-body">{_report(finding["observation"])}</p>', unsafe_allow_html=True)
        st.markdown('<p class="kf-subtitle">Business implication</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="kf-body">{_report(finding["implication"])}</p>', unsafe_allow_html=True)
        st.markdown('<p class="kf-subtitle">Dashboard evidence</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="kf-body">{_report(finding["evidence"])}</p>', unsafe_allow_html=True)
