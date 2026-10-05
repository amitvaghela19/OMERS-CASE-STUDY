import streamlit as st

from omers.chat_graph import REFUSAL, ask
from omers.store import load_tables
from omers.suggestions import pick_suggestions

st.header("Chat")
st.caption("Ask in your own words, or use a suggestion. Each figure comes from a query on the cleaned database.")

if not st.session_state.get("loaded"):
    st.warning("Upload a workbook in the sidebar before asking a question.")
    st.stop()

tables = load_tables()
if "suggestions" not in st.session_state:
    st.session_state.suggestions = pick_suggestions(tables)
if "messages" not in st.session_state:
    st.session_state.messages = []

title, action = st.columns([5, 1], vertical_alignment="center")
title.markdown("**Suggested questions**")
if action.button("Refresh", icon=":material/refresh:", width="stretch"):
    st.session_state.suggestions = pick_suggestions(tables, avoid=set(st.session_state.suggestions))
    st.rerun()

clicked = None
left, right = st.columns(2)
for index, suggestion in enumerate(st.session_state.suggestions):
    column = left if index % 2 == 0 else right
    if column.button(suggestion, key=f"suggestion-{index}", width="stretch"):
        clicked = suggestion

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = clicked or st.chat_input("Ask about an asset, region, return, equity bridge, or paste a SELECT")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    try:
        reply = ask(question)
    except Exception as exc:
        st.exception(exc)
        reply = REFUSAL
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
