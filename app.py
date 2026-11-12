"""ShopImpact: the full everyday app, with research tools inside Impact Lab."""

from pathlib import Path

import streamlit as st

from ui.account import has_workspace_access
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
    st.Page("views/account.py", title="Your account", url_path="account"),
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
st.session_state.app_navigation_pages = {item.title: item for item in pages}
# Every route, including bookmarked deep links, passes through the same entry gate.
# The choice is never restored from browser-local journal data.
if not has_workspace_access():
    if page.title != "Your account":
        st.session_state.entry_destination = page.title
        st.switch_page("views/account.py")
    from styles import inject_css
    from ui.studio import background_html

    state = st.session_state
    inject_css(state.display_mode, state.accent_palette, state.reduce_motion,
               state.text_size, state.dyslexia_font)
    st.markdown(background_html(state.display_mode, state.reduce_motion), unsafe_allow_html=True)
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']{display:none!important}</style>", unsafe_allow_html=True)
    page.run()
    st.stop()

history = st.session_state.setdefault("app_navigation_history", [])
if not history or history[-1] != page.title:
    history.append(page.title)
    del history[:-30]
render_topbar(
    "Impact Lab"
    if page.title in {"Research tools", "Research feedback", "Ask Tilly"}
    else page.title,
    [
        item
        for item in pages
        if item.title not in {"Research tools", "Research feedback", "Ask Tilly", "Your account"}
    ],
)
with st.container(key=f"route-view-{page.url_path or 'home'}"):
    page.run()
render_persistence_warning()
persist_session()
