"""ShopImpact: the full everyday app, with research tools inside Impact Lab."""

from pathlib import Path

import streamlit as st

from ui.common import (
    init_session,
    persist_session,
    refresh_purchase_month_index,
    render_persistence_warning,
    render_topbar,
)

st.set_page_config(
    page_title="ShopImpact",
    page_icon=Path(__file__).with_name("static") / "favicon.svg",
    layout="wide",
    initial_sidebar_state="auto",
)

init_session()
refresh_purchase_month_index()

pages = [
    st.Page(
        "views/home.py",
        title="Home",
        icon=":material/home:",
        url_path="home",
        default=True,
    ),
    st.Page(
        "views/dashboard.py",
        title="Dashboard",
        icon=":material/monitoring:",
        url_path="dashboard",
    ),
    st.Page(
        "views/purchases.py",
        title="Purchases",
        icon=":material/shopping_bag:",
        url_path="purchases",
    ),
    st.Page(
        "views/swaps_plan.py",
        title="Swaps and plan",
        icon=":material/eco:",
        url_path="swaps-plan",
    ),
    st.Page(
        "views/impact_lab.py",
        title="Impact Lab",
        icon=":material/science:",
        url_path="impact-lab",
    ),
    st.Page(
        "views/garden_badges.py",
        title="Garden and badges",
        icon=":material/yard:",
        url_path="garden-badges",
    ),
    st.Page(
        "views/month_review.py",
        title="Month in review",
        icon=":material/auto_stories:",
        url_path="month-review",
    ),
    st.Page(
        "views/settings_about.py",
        title="Settings and about",
        icon=":material/settings:",
        url_path="settings-about",
    ),
    st.Page("views/ask_tilly.py", title="Ask Tilly", url_path="ask-tilly"),
    st.Page(
        "views/research.py",
        title="Research tools",
        icon=":material/biotech:",
        url_path="research",
    ),
    st.Page(
        "views/research_feedback.py", title="Research feedback", url_path="feedback"
    ),
]

page = st.navigation(pages, position="hidden")
render_topbar(
    "Impact Lab"
    if page.title in {"Research tools", "Research feedback", "Ask Tilly"}
    else page.title,
    [
        item
        for item in pages
        if item.title not in {"Research tools", "Research feedback", "Ask Tilly"}
    ],
)
with st.container(key=f"route-view-{page.url_path or 'home'}"):
    page.run()
render_persistence_warning()
persist_session()
