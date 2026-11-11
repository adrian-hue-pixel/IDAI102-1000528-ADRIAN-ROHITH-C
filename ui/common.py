"""Shared state, top-bar controls, and accessible page components."""

import datetime as dt
import hashlib
import html
import json
from base64 import b64encode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st

import browser_persistence as bp
import browser_storage as bs
import charts
import logic as lg
from styles import THEMES, inject_css, normalize_mode
from ui.illustrations import cached_mascot_svg
from ui.studio import background_html, brand_html
from ui.undo import capture_state, record_change, undo_latest

OTHER_BRAND = "Other / not listed"
TOPBAR_SETTING_KEYS = {
    "display_mode": "topbar_display_mode",
    "accent_palette": "topbar_accent_palette",
    "currency_name": "topbar_currency_name",
    "goal_kg": "topbar_goal_kg",
    "text_size": "topbar_text_size",
    "dyslexia_font": "topbar_dyslexia_font",
    "sound_enabled": "topbar_sound_enabled",
    "reduce_motion": "topbar_reduce_motion",
    "uncertainty_band": "settings_uncertainty_band",
}


def viewer_timezone() -> dt.tzinfo:
    """Resolve the browser timezone, falling back to the server's local zone."""
    try:
        timezone_name = st.context.timezone
    except (AttributeError, RuntimeError):
        timezone_name = None
    if timezone_name:
        try:
            return ZoneInfo(timezone_name)
        except (TypeError, ValueError, ZoneInfoNotFoundError):
            pass
    return dt.datetime.now().astimezone().tzinfo or dt.timezone.utc


def app_today() -> dt.date:
    """Return today's date in the viewer's timezone for this script run."""
    return dt.datetime.now(dt.timezone.utc).astimezone(viewer_timezone()).date()


def init_session() -> None:
    """Initialize session defaults and restore the browser's saved journal once."""
    today = app_today()
    defaults = {
        "purchases": [],
        "next_id": 1,
        "last_event": None,
        "tip": "",
        "tip_view_category": "Clothing",
        "tip_offset": 0,
        "tip_key": None,
        "quote": lg.random_quote(),
        "undo_stack": [],
        "achievement_inbox": [],
        "plans": [],
        "garden_month": None,
        "favorites": [],
        "settings": {
            "text_size": "M",
            "dyslexia_font": False,
            "sound_enabled": False,
            "display_mode": "Light",
            "accent_palette": "Evergreen",
            "currency_name": "US Dollar ($)",
            "goal_kg": 80,
            "goal_history": [
                {"from_month": lg.month_of(today), "goal_kg": 80}
            ],
            "uncertainty_band": 30,
            "month_review_last_visit": None,
            "xp_scoring_notice_dismissed": False,
            "reduce_motion": False,
            "view_month": lg.month_of(today),
        },
        "view_month": lg.month_of(today),
        "guide_dismissed": False,
        "weekly_challenges_dismissed": False,
        "storage_available": True,
        "storage_error": None,
        "browser_storage_loaded": False,
        "browser_storage_signature": None,
        "raw_saved_state": None,
        "persistence_locked": False,
        "text_size": "M",
        "dyslexia_font": False,
        "sound_enabled": False,
        "display_mode": "Light",
        "accent_palette": "Evergreen",
        "currency_name": "US Dollar ($)",
        "goal_kg": 80,
        "goal_history": [{"from_month": lg.month_of(today), "goal_kg": 80}],
        "uncertainty_band": 30,
        "month_review_last_visit": None,
        "xp_scoring_notice_dismissed": False,
        "reduce_motion": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    state = st.session_state
    if not state.browser_storage_loaded:
        try:
            ready, saved, error = bs.read_saved_value()
        except (TypeError, ValueError, RuntimeError) as exc:
            ready, saved, error = True, None, str(exc)
        if ready:
            state.browser_storage_loaded = True
            state.storage_pending = False
            state.storage_available = error is None
            state.storage_error = error
            if saved is not None:
                state.raw_saved_state = saved
                try:
                    purchases, dismissed, skipped, inbox, plans, saved_settings = (
                        bp.decode_saved_state(saved, today=today)
                    )
                except (TypeError, ValueError) as exc:
                    state.persistence_locked = True
                    state.storage_error = f"Saved browser data could not be restored. ({exc})"
                else:
                    state.purchases = purchases
                    state.next_id = max((item["id"] for item in purchases), default=0) + 1
                    state.guide_dismissed = dismissed
                    state.achievement_inbox = inbox
                    state.plans = plans
                    state.browser_storage_signature = saved
                    state.settings.update(saved_settings)
                    for key in (
                        "text_size",
                        "dyslexia_font",
                        "sound_enabled",
                        "display_mode",
                        "accent_palette",
                        "currency_name",
                        "goal_kg",
                        "goal_history",
                        "uncertainty_band",
                        "month_review_last_visit",
                        "xp_scoring_notice_dismissed",
                        "reduce_motion",
                        "view_month",
                    ):
                        if key in state.settings:
                            state[key] = state.settings[key]
                    if skipped:
                        state.persistence_locked = True
                        state.storage_error = (
                            f"Only part of your saved data could be restored; "
                            f"{len(skipped)} row(s) were skipped: "
                            + "; ".join(reason for _, reason in skipped[:3])
                        )
        else:
            state.storage_pending = True

    state.display_mode = normalize_mode(state.display_mode)
    if "display_mode" in state.settings:
        state.settings["display_mode"] = state.display_mode


def persist_session() -> None:
    """Persist the journal and supported preferences after the active page runs."""
    state = st.session_state
    if (
        not state.browser_storage_loaded
        or not state.storage_available
        or state.persistence_locked
    ):
        return
    settings = {
        "text_size": state.text_size,
        "dyslexia_font": bool(state.dyslexia_font),
        "sound_enabled": bool(state.sound_enabled),
        "display_mode": state.display_mode,
        "accent_palette": state.accent_palette,
        "currency_name": state.currency_name,
        "goal_kg": int(state.goal_kg),
        "goal_history": state.goal_history,
        "uncertainty_band": int(state.uncertainty_band),
        "month_review_last_visit": state.month_review_last_visit,
        "xp_scoring_notice_dismissed": state.xp_scoring_notice_dismissed,
        "reduce_motion": bool(state.reduce_motion),
        "view_month": state.view_month,
    }
    saved = bp.encode_saved_state(
        state.purchases,
        state.guide_dismissed,
        state.achievement_inbox,
        state.plans,
        settings,
    )
    if saved == state.browser_storage_signature:
        return
    try:
        ready, error = bs.write_saved_value(saved)
    except (TypeError, ValueError, RuntimeError) as exc:
        ready, error = True, str(exc)
    if not ready:
        state.storage_pending = True
    elif error:
        state.storage_available = False
        state.storage_error = f"Browser saving is unavailable; data remains in this session. ({error})"
    else:
        state.browser_storage_signature = saved
        state.raw_saved_state = saved
        state.storage_pending = False
        state.storage_error = None


def render_persistence_warning() -> None:
    """Offer explicit recovery actions without replacing an unrestored save."""
    state = st.session_state
    if not state.persistence_locked:
        return
    st.warning(
        f"{state.storage_error or 'Your saved browser data could not be fully restored.'} "
        "It is protected from being overwritten until you download it or discard it."
    )
    raw_saved = state.raw_saved_state
    if raw_saved is not None:
        st.download_button(
            "Download my saved data (raw JSON)",
            raw_saved,
            file_name="shopimpact_saved_data_raw.json",
            mime="application/json",
            key="download_raw_saved_state",
        )
    if st.button(
        "Discard saved data and start fresh", key="discard_saved_state"
    ):
        state.confirm_discard_saved_state = True
    if state.get("confirm_discard_saved_state"):
        st.warning(
            "This permanently removes the saved ShopImpact data and its backup "
            "from this browser."
        )
        confirm, cancel = st.columns(2)
        if confirm.button(
            "Confirm discard and start fresh",
            key="confirm_discard_saved_state_action",
        ):
            try:
                ready, error = bs.remove_saved_value()
            except (TypeError, ValueError, RuntimeError) as exc:
                ready, error = True, str(exc)
            if not ready:
                state.storage_pending = True
            elif error:
                state.storage_error = f"Saved data could not be discarded. ({error})"
            else:
                state.purchases = []
                state.next_id = 1
                state.plans = []
                state.achievement_inbox = []
                state.guide_dismissed = False
                state.last_event = None
                state.browser_storage_signature = None
                state.raw_saved_state = None
                state.persistence_locked = False
                state.storage_error = None
                state.confirm_discard_saved_state = False
                st.rerun()
        if cancel.button("Keep my saved data", key="cancel_discard_saved_state"):
            state.confirm_discard_saved_state = False


def render_undo_control() -> None:
    """Expose the latest reversible action on every page."""
    stack = st.session_state.get("undo_stack", [])
    if not stack:
        return
    description = stack[-1]["description"]
    with st.container(key="undo-action"):
        if st.button(
            f"Undo: {description}",
            key="undo_latest_action",
            help="Restore the journal and plans to their previous state.",
        ):
            undo_latest()
            st.toast(f"Undid: {description}")
            st.rerun()


def render_state_guidance(active_page: str) -> None:
    """Offer one concise explanation and next step for common journal states."""
    state = st.session_state
    if state.get("storage_pending"):
        st.info("Your saved journal is still loading; you can retry the connection.")
        if st.button("Retry loading saved data", key="retry_saved_data"):
            state.browser_storage_loaded = False
            st.rerun()
    elif not state.storage_available:
        st.info(
            "Browser saving is unavailable, so your changes will remain only in "
            "this session."
        )
        st.page_link(
            "views/settings_about.py",
            label="Review data settings",
        )

    purchases = state.get("purchases", [])
    if not purchases:
        st.info("Your journal is empty; your first entry will start your monthly view.")
        st.page_link(
            "views/home.py",
            label="Add your first purchase",
        )
    elif len(purchases) == 1:
        st.info(
            "You have one purchase so far; another entry can help build a useful "
            "monthly picture."
        )
        st.page_link(
            "views/home.py",
            label="Log another purchase",
        )
    elif active_page == "Dashboard" and len(
        {lg.month_of(item["date"]) for item in purchases}
    ) == 1:
        st.info(
            "Your journal covers one month, so there is not yet a month-to-month "
            "trend to compare."
        )
        st.page_link(
            "views/home.py",
            label="Log a purchase in another month",
        )

def month_options() -> list[tuple[int, int]]:
    state = st.session_state
    months = {
        lg.month_of(item["date"]) for item in state.purchases
    } | {lg.month_of(item["date"]) for item in state.plans}
    months.add(lg.month_of(app_today()))
    return sorted(months, reverse=True)


def update_preference(key: str, widget_key: str) -> None:
    value = st.session_state[widget_key]
    if key == "goal_kg":
        update_goal(value, widget_key=widget_key)
        return
    st.session_state[key] = value
    other_widget_key = TOPBAR_SETTING_KEYS[key]
    if widget_key != other_widget_key:
        st.session_state[other_widget_key] = value
    if key == "currency_name":
        st.session_state.price = 25.0 * lg.CURRENCIES[value][1]


def update_goal(value: int, state=None, widget_key: str | None = None) -> None:
    """Set the current goal and record its effective month as an undoable change."""
    state = state or st.session_state
    previous_goal = int(state.goal_kg)
    if value == previous_goal:
        return
    before = capture_state(state)
    before["settings_goal"] = previous_goal
    if widget_key is not None and not widget_key.startswith("topbar_"):
        before[widget_key] = previous_goal

    month = lg.month_of(app_today())
    history = [
        entry
        for entry in state.get("goal_history", [])
        if tuple(entry["from_month"]) != month
    ]
    history.append({"from_month": month, "goal_kg": value})
    history.sort(key=lambda entry: tuple(entry["from_month"]))
    if len(history) > 60:
        history = history[-60:]

    state.goal_kg = value
    state.goal_history = history
    state.settings["goal_kg"] = value
    state.settings["goal_history"] = history
    state.settings_goal = value
    state.topbar_goal_kg = value
    if widget_key is not None:
        state[widget_key] = value
    record_change(before, "Changed monthly goal.", state)


def month_changed() -> None:
    st.session_state.view_month = st.session_state.topbar_month_selector


def render_topbar(
    active_page: str, pages: list[st.Page]
) -> tuple[str, str, float, str, float, bool]:
    """Render the shared studio sidebar and ambient scene on every route."""
    state = st.session_state
    slug = active_page.lower().replace(" ", "-")
    widget_keys = {
        name: key if active_page == "Home" else f"{key}_{slug}"
        for name, key in TOPBAR_SETTING_KEYS.items()
    }
    state.display_mode = normalize_mode(state.display_mode)
    for name, key in widget_keys.items():
        if state.get(key) != state[name]:
            state[key] = state[name]
    months = month_options()
    if state.view_month not in months:
        state.view_month = months[0]
    state.topbar_month_selector = state.view_month
    inject_css(state.display_mode, state.accent_palette, state.reduce_motion,
               state.text_size, state.dyslexia_font)
    st.markdown(background_html(state.display_mode, state.reduce_motion), unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(brand_html(), unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">WORKSPACE</div>', unsafe_allow_html=True)
        icons = {
            "Home": ":material/home:", "Dashboard": ":material/space_dashboard:",
            "Purchases": ":material/shopping_bag:", "Swaps and plan": ":material/swap_horiz:",
            "Impact Lab": ":material/science:", "Garden and badges": ":material/spa:",
            "Month in review": ":material/auto_stories:", "Settings and about": ":material/tune:",
        }
        for item in pages:
            label = {"Garden and badges": "Garden & badges", "Swaps and plan": "Swaps & plans",
                     "Settings and about": "Settings & about"}.get(item.title, item.title)
            with st.container(key=f"studio-nav-{item.title.lower().replace(' ', '-')}{'-active' if item.title == active_page else ''}"):
                st.page_link(item, label=label, icon=icons.get(item.title),
                             help="Current page" if item.title == active_page else None)
        st.markdown('<div class="sidebar-label sidebar-period">YOUR PERSPECTIVE</div>', unsafe_allow_html=True)
        st.selectbox("Selected month", months,
                     index=months.index(state.view_month), key="topbar_month_selector",
                     on_change=month_changed,
                     format_func=lambda ym: dt.date(ym[0], ym[1], 1).strftime("%b %Y"))
        with st.expander("Appearance & preferences"):
            st.radio("Display mode", ["Light", "Dark"],
                     index=["Light", "Dark"].index(state.display_mode), horizontal=True,
                     key=widget_keys["display_mode"], on_change=update_preference,
                     args=("display_mode", widget_keys["display_mode"]))
            st.selectbox("Currency", list(lg.CURRENCIES),
                         index=list(lg.CURRENCIES).index(state.currency_name),
                         key=widget_keys["currency_name"], on_change=update_preference,
                         args=("currency_name", widget_keys["currency_name"]))
            st.slider("Monthly CO₂ goal (kg)", 20, 300, value=int(state.goal_kg), step=5,
                      key=widget_keys["goal_kg"], on_change=update_preference,
                      args=("goal_kg", widget_keys["goal_kg"]),
                      help="A personal comparison, not a scientific target.")
            st.selectbox("Text size", ["S", "M", "L", "XL"],
                         index=["S", "M", "L", "XL"].index(state.text_size),
                         key=widget_keys["text_size"], on_change=update_preference,
                         args=("text_size", widget_keys["text_size"]))
            for label, name in (("Dyslexia-friendly font", "dyslexia_font"),
                                ("Badge unlock sound", "sound_enabled"),
                                ("Reduce motion", "reduce_motion")):
                st.checkbox(label, value=bool(state[name]), key=widget_keys[name],
                            on_change=update_preference, args=(name, widget_keys[name]))
        status = "Saved in this browser" if state.storage_available else "Session storage only"
        st.markdown(f'<div class="sidebar-footer"><span class="status-dot"></span>{status}'
                    '<p>A little awareness. Every day.</p></div>', unsafe_allow_html=True)
    symbol, rate = lg.CURRENCIES[state.currency_name]
    return state.display_mode, symbol, rate, state.currency_name, float(state.goal_kg), bool(state.reduce_motion)


def page_header(
    title: str,
    description: str,
    *,
    action_label: str | None = None,
    action_page: str | None = None,
) -> None:
    st.markdown('<a class="skip-link" href="#main-content">Skip to content</a>', unsafe_allow_html=True)
    render_undo_control()
    if title == "Home":
        with st.container(key="studio-home-header"):
            st.title(title, anchor="main-content")
        return
    with st.container(key="studio-page-heading"):
        title_col, action_col = st.columns([4, 1], vertical_alignment="center")
        with title_col:
            st.markdown('<div class="page-eyebrow">SHOPIMPACT / EVERYDAY INTELLIGENCE</div>', unsafe_allow_html=True)
            st.title(title, anchor="main-content")
            st.caption(description)
        if action_label and action_page:
            with action_col:
                st.page_link(action_page, label=action_label)
    with st.expander("Journal status and getting started"):
        render_state_guidance(title)


def whats_next(page: str, title: str, description: str) -> None:
    st.markdown(
        f'<aside class="whats-next"><strong>What’s next · {html.escape(title)}</strong>'
        f"<span>{html.escape(description)}</span></aside>",
        unsafe_allow_html=True,
    )
    st.page_link(page, label=f"Continue to {title} →")


def money(value_usd: float, rate: float, symbol: str) -> str:
    return f"{symbol}{value_usd * rate:,.2f}"


def render_stat_chip(label: str, value: str, trend: list[float]) -> None:
    sparkline = charts.sparkline_svg(trend or [0.0], label)
    value_markup = html.escape(value)
    st.markdown(
        '<div class="stat-chip">'
        f'<div class="stat-copy"><span>{html.escape(label)}</span>'
        f"<strong>{value_markup}</strong></div>"
        f'<div class="stat-sparkline">{sparkline}</div></div>',
        unsafe_allow_html=True,
    )


@st.fragment
def render_tilly(mood: str, mode: str, reduce_motion: bool) -> None:
    svg = cached_mascot_svg(mood, mode, animate=not reduce_motion)
    static_svg = cached_mascot_svg(mood, mode, animate=False)
    encoded = b64encode(svg.encode("utf-8")).decode("ascii")
    static_encoded = b64encode(static_svg.encode("utf-8")).decode("ascii")
    st.markdown(
        f'<img class="tilly-image svg-motion-animated" '
        f'src="data:image/svg+xml;base64,{encoded}" '
        f'alt="Tilly the turtle looking {html.escape(mood, quote=True)}." '
        'style="display:block;width:100%;max-width:280px;height:auto;margin:0 auto">'
        f'<img class="tilly-image svg-motion-static" '
        f'src="data:image/svg+xml;base64,{static_encoded}" '
        f'alt="Tilly the turtle looking {html.escape(mood, quote=True)}." '
        'style="display:block;width:100%;max-width:280px;height:auto;margin:0 auto">',
        unsafe_allow_html=True,
    )


def render_svg(
    svg: str, alt: str, max_width: int, *, static_svg: str | None = None
) -> None:
    encoded = b64encode(svg.encode("utf-8")).decode("ascii")
    static_image = ""
    if static_svg is not None:
        static_encoded = b64encode(static_svg.encode("utf-8")).decode("ascii")
        escaped_alt = html.escape(alt, quote=True)
        static_image = (
            '<img class="svg-turtle-image svg-motion-static" '
            f'src="data:image/svg+xml;base64,{static_encoded}" '
            f'alt="{escaped_alt}" '
            f'style="display:block;width:100%;max-width:{max_width}px;height:auto;margin:0 auto">'
        )
    st.markdown(
        f'<img class="svg-turtle-image svg-motion-animated" '
        f'src="data:image/svg+xml;base64,{encoded}" '
        f'alt="{html.escape(alt, quote=True)}" '
        f'style="display:block;width:100%;max-width:{max_width}px;height:auto;margin:0 auto">'
        f"{static_image}",
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _cached_monthly_summary(
    digest: str,
    month: tuple[int, int],
    _month_index: dict,
) -> dict:
    return lg.monthly_summary([], month, _month_index)


def monthly_summary(purchases: list[dict], month: tuple[int, int]) -> dict:
    state = st.session_state
    month_index = state.get("purchase_month_index")
    if month_index is None:
        month_index = lg.build_month_index(purchases)
    digest = state.get("purchase_digest")
    if digest is None:
        serialized = json.dumps(
            purchases, sort_keys=True, default=str, separators=(",", ":")
        )
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return _cached_monthly_summary(digest, month, month_index)


def refresh_purchase_month_index(state=None) -> None:
    """Rebuild the per-run month index and content digest after journal changes."""
    state = state or st.session_state
    state.purchase_month_index = lg.build_month_index(state.purchases)
    serialized = json.dumps(
        state.purchases, sort_keys=True, default=str, separators=(",", ":")
    )
    state.purchase_digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def theme_colors(mode: str) -> dict:
    return THEMES[mode]
