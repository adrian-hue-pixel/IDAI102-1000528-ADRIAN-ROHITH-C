"""Research tools hosted inside the original ShopImpact shell and preferences."""

import streamlit as st

import research_app as research
from ui.common import page_header

TOOLS = {
    "Start here": None,
    "Cited estimates": research.log_page,
    "Research journal": research.journal_page,
    "Monthly analysis": research.dashboard_page,
    "Method": research.method_body,
    "Validation": research.validation_body,
    "Budget planner": research.planner_body,
    "Product text": research.classifier_page,
    "Lifespan": research.lifecycle_page,
    "Replay": research.replay_body,
    "Feedback": research.feedback_page,
    "Data & export": research.settings_page,
}


def render(initial_tool="Start here"):
    page_header(
        "Research tools",
        "Go deeper into the evidence behind everyday choices.",
        action_label="Back to Impact Lab",
        action_page="views/impact_lab.py",
    )
    research.bootstrap()
    state = st.session_state
    # Appearance and motion come from the app's existing controls, not a second shell.
    state.research_mode = state.display_mode
    state.research_motion = state.reduce_motion
    state.research_month = f"{state.view_month[0]:04d}-{state.view_month[1]:02d}"
    key = "research_feedback_tool" if initial_tool == "Feedback" else "research_tool"
    selected = st.selectbox(
        "Explore research tools",
        list(TOOLS),
        index=list(TOOLS).index(initial_tool),
        key=key,
    )
    state.research_embedded = True
    try:
        renderer = TOOLS[selected]
        if renderer is None:
            st.markdown("### A closer look, when you want it")
            st.write(
                "Your journal, garden and daily tools are still where you left them. This corner of Impact Lab adds sourced estimates and experiments."
            )
            cols = st.columns(3)
            items = [
                (
                    "Cited estimates",
                    "Inspect EPA factors and Monte Carlo mapping sensitivity.",
                ),
                (
                    "Validation",
                    "See where spend estimates disagree with manufacturer LCAs.",
                ),
                (
                    "Budget planner",
                    "Compare exact dynamic programming with a greedy strategy.",
                ),
            ]
            for col, (title, description) in zip(cols, items):
                with col, st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.caption(description)
            st.info(
                "Everyday journal totals use the existing illustrative model. Research entries use the versioned EPA dataset and stay in their own journal, so historical records are never silently recalculated."
            )
            st.caption(
                "Choose a tool above. The same appearance, motion settings and selected month apply here."
            )
        else:
            renderer()
    finally:
        state.pop("research_embedded", None)
    research.persist()
