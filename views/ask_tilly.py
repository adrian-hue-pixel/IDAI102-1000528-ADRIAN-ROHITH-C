"""Optional Ask Tilly chat in the existing ShopImpact shell."""

import os
import time

import streamlit as st

from ask_tilly import SOURCES, context_for, generate, reserve_call
from ui.common import page_header, render_tilly


def configuration(name, fallback=""):
    value = os.environ.get(name)
    if value:
        return value
    try:
        return st.secrets.get(name, fallback)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return fallback


def render():
    page_header(
        "Ask Tilly",
        "A little help understanding your choices and the evidence behind them.",
        action_label="Back to Impact Lab",
        action_page="views/impact_lab.py",
    )
    state = st.session_state
    avatar, intro = st.columns([1, 4], vertical_alignment="center")
    with avatar:
        render_tilly("curious", state.display_mode, state.reduce_motion)
    with intro:
        st.write(
            "Ask me about your footprint, the model's limits or a plan to explore."
        )
        st.caption(
            "AI answers can be wrong. Tilly explains the app's results and cannot change your journal."
        )
    key = configuration("GEMINI_API_KEY")
    model = configuration("GEMINI_MODEL", "gemini-2.5-flash")
    state.setdefault("tilly_messages", [])
    state.setdefault("tilly_call_times", [])
    share = st.checkbox(
        "Include my selected month's category summary", key="tilly_share"
    )
    scope = (share, tuple(state.view_month), str(state.purchases) if share else "")
    if state.get("tilly_scope") != scope:
        state.tilly_messages = []
        state.tilly_scope = scope
    context = context_for(state.purchases, state.view_month, share)
    st.caption(
        "Sending a question sends its text and this conversation to Google Gemini. If enabled, the category summary is included too. Brands, notes, exact dates, prices and receipts are excluded from the automatic summary. Chat stays in this session and is not saved to your journal."
    )
    with st.expander("Preview what Tilly can see"):
        st.json(context)
    consent = st.checkbox(
        "I agree to send my questions and the previewed context to Google Gemini",
        key="tilly_consent",
    )
    if st.button("Clear conversation"):
        state.tilly_messages = []
        st.rerun()
    if not key:
        st.info(
            "Tilly is ready for a connection. The app owner needs to configure a Gemini API key before chat is enabled."
        )
    st.caption(
        "Try: ‘What does mapping sensitivity mean?’ · ‘Why can cheap products get lower estimates?’ · ‘How does the budget planner work?’"
    )
    for message in state.tilly_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input(
        "Ask Tilly a question…", max_chars=2000, disabled=not key or not consent
    )
    if question:
        now = time.monotonic()
        times = [t for t in state.tilly_call_times if now - t < 3600]
        state.tilly_call_times = times
        if len(times) >= 20 or (times and now - times[-1] < 10):
            st.warning(
                "Please pause between questions. Each session allows 20 requests per hour."
            )
            return
        try:
            reserve_call()
            state.tilly_call_times.append(now)
            with st.spinner("Tilly is thinking…"):
                answer = generate(question, state.tilly_messages, context, key, model)
            state.tilly_messages.extend(
                [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ]
            )
            state.tilly_messages = state.tilly_messages[-12:]
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    with st.expander("Verified sources and limits"):
        for title, url in SOURCES.items():
            st.markdown(f"[{title}]({url})")
        st.caption(
            "These are the app's reference sources, not proof that every AI sentence is supported. Tilly has no live web search. Local rate limits are not a provider billing cap."
        )


render()
