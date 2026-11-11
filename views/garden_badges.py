"""Tilly, the Eco Garden, footprint trail, badges, and playful progress."""

import html
import math

import streamlit as st

import gamification as gm
import logic as lg
from ui.actions import badge_progress
from ui.common import (
    app_today,
    monthly_summary,
    page_header,
    render_stat_chip,
    render_svg,
    render_tilly,
    whats_next,
)
from ui.illustrations import (
    cached_footprint_svg,
    cached_garden_svg,
    cached_plant_svg,
)

NEXT = (
    "views/month_review.py",
    "Month in review",
    "Turn this month into a shareable snapshot.",
)


def _toggle_weekly_challenges() -> None:
    st.session_state.weekly_challenges_dismissed = (
        not st.session_state.weekly_challenges_dismissed
    )


@st.fragment
def _render_weekly_challenges(purchases: list[dict]) -> None:
    state = st.session_state
    st.markdown("## Optional weekly challenges")
    if state.weekly_challenges_dismissed:
        st.button("Show weekly challenges", on_click=_toggle_weekly_challenges)
    else:
        for challenge in gm.weekly_challenges(
            purchases, app_today(), state.month_review_last_visit
        ):
            st.progress(
                challenge["progress"] / challenge["target"],
                text=(
                    f"{challenge['title']} · {challenge['progress']} of "
                    f"{challenge['target']}"
                ),
            )
            if challenge["complete"]:
                st.caption("Complete whenever it suits you.")
        st.button("Hide weekly challenges", on_click=_toggle_weekly_challenges)


def render() -> None:
    page_header(
        "Garden and badges",
        "A playful view of your journal’s progress. These drawings do not change the estimate.",
        action_label="Review this month",
        action_page=NEXT[0],
    )
    state = st.session_state
    month = state.view_month
    purchases = state.purchases
    mode = state.display_mode
    goal = lg.goal_for_month(state.goal_history, month, float(state.goal_kg))
    reduce_motion = bool(state.reduce_motion)
    summary = monthly_summary(purchases, month)

    badges = lg.evaluate_badges(
        purchases,
        month,
        goal,
        state.purchase_month_index,
        goal_history=state.goal_history,
    )
    low_choices = sum(
        item["rating"] == "Low" for item in state.purchase_month_index.get(month, [])
    )
    garden_stats = st.columns(3)
    for column, label, value in zip(
        garden_stats,
        ("This month's entries", "Low model estimates", "Badges earned"),
        (summary["n"], low_choices, sum(badge["earned"] for badge in badges)),
    ):
        with column:
            render_stat_chip(label, str(value), [value])
    st.caption(
        "A visual record of your journal. Growth and badges are playful feedback, not evidence of environmental outcomes."
    )
    ratio = summary["co2_kg"] / goal if goal else 0
    event = state.get("last_event")
    if event and event.get("new_badges"):
        mood, message = "proud", "A new badge to celebrate. Nice thoughtful step!"
    elif event and event.get("eco"):
        mood, message = "happy", "That choice stood out in the estimate."
    elif not summary["n"]:
        mood, message = "curious", "What would you like to explore this month?"
    elif ratio <= 0.8:
        mood, message = "happy", "Your month is within your personal goal."
    elif ratio <= 1.0 or ratio > 1.25:
        mood, message = (
            "encouraging",
            "A fresh month is always ahead; there is no pressure.",
        )
    else:
        mood, message = (
            "sleepy",
            "A gentle pause can be part of thoughtful choices, too.",
        )
    companion_col, garden_col = st.columns([0.85, 1.15], vertical_alignment="top")
    with companion_col:
        st.markdown("## Your companion")
        render_tilly(mood, mode, reduce_motion)
        st.markdown(
            f'<div class="speech-bubble">{message}</div>', unsafe_allow_html=True
        )
        st.markdown("### Your journey")
        if not state.xp_scoring_notice_dismissed:
            notice_col, dismiss_col = st.columns([5, 1])
            notice_col.info("XP now rewards low-impact choices and swaps")
            if dismiss_col.button("Dismiss", key="dismiss_xp_scoring_notice"):
                state.xp_scoring_notice_dismissed = True
                state.setdefault("settings", {})["xp_scoring_notice_dismissed"] = True
                st.rerun()
        journey = gm.experience_summary(
            purchases,
            goal_history=state.goal_history,
            today=app_today(),
        )
        st.metric(f"Level {journey['level']}", f"{journey['experience']} XP")
        st.progress(
            journey["progress"] / 100,
            text=f"{journey['progress']} of 100 XP to next level",
        )
        with st.expander("How XP works"):
            for reason in journey["reasons"]:
                st.write(reason)
            st.markdown("**XP earned from your records**")
            for reason, points in journey["breakdown"].items():
                st.write(f"{reason}: {points} XP")
            st.caption(
                "XP is calculated from the records you keep. If records are "
                "deleted, XP may fall; XP is never removed as a penalty."
            )
        current_streak = gm.current_activity_streak(purchases, app_today())
        best_streak = gm.best_activity_streak(purchases)
        st.metric("Current streak", f"{current_streak} days")
        st.metric("Best streak", f"{best_streak} days")
        if current_streak == 0:
            st.caption("Start a new run whenever you like.")
        st.caption("Streaks reflect purchase dates, not when entries were logged.")
    with garden_col:
        st.markdown("## Eco Garden")
        month_index = state.purchase_month_index
        months = sorted(month_index, reverse=True)
        if months:
            if state.garden_month not in months:
                state.garden_month = month if month in months else months[0]
            garden_month = st.selectbox(
                "Garden month",
                months,
                index=months.index(state.garden_month),
                key="garden_month",
                format_func=lg.month_label,
            )
            garden_items = month_index.get(garden_month, [])
            level = min(5, sum(item["rating"] == "Low" for item in garden_items))
            garden = cached_garden_svg(level, mode, not reduce_motion)
            static_garden = cached_garden_svg(level, mode, False)
            render_svg(
                garden,
                f"Turtle-drawn eco garden, level {level} of 5.",
                360,
                static_svg=static_garden,
            )
            st.caption(
                f"Garden image alternative: {level} of 5 growth stages in "
                f"{lg.month_label(garden_month)}. It rests; it never withers."
            )
        else:
            st.caption("Your garden is ready when you choose to log a purchase.")
        if purchases:
            prints = max(1, min(8, math.ceil(ratio * 5)))
            trail = cached_footprint_svg(prints, mode, not reduce_motion, total=8)
            static_trail = cached_footprint_svg(prints, mode, False, total=8)
            st.markdown("### Footprint trail")
            render_svg(
                trail,
                f"Turtle-drawn footprint trail with {prints} prints.",
                280,
                static_svg=static_trail,
            )
            st.caption(
                f"{prints} of 8 footprints · a visual reflection of this month’s estimate."
            )
            low_count = sum(
                item["rating"] == "Low" and lg.month_of(item["date"]) == month
                for item in purchases
            )
            leaves = min(8, max(1, low_count + 3))
            plant = cached_plant_svg(leaves, mode, not reduce_motion)
            static_plant = cached_plant_svg(leaves, mode, False)
            st.markdown("### Growing plant")
            render_svg(
                plant,
                "Turtle-drawn plant illustration showing monthly progress.",
                280,
                static_svg=static_plant,
            )

    st.markdown("## Badges")
    glyphs = {
        "sprout": '<path d="M12 21V11M12 15C4 15 3 10 3 5c6 0 9 3 9 8M12 11c0-6 4-9 9-9 0 6-3 9-9 9"/>',
        "leaf": '<path d="M4 20C2 9 10 3 21 3c0 11-6 18-17 17zm0 0L16 9"/>',
        "star": '<path d="m12 2 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z"/>',
        "cycle": '<path d="M20 7a9 9 0 0 0-15 0L2 10m0-6v6h6M4 17a9 9 0 0 0 15 0l3-3m0 6v-6h-6"/>',
        "link": '<path d="m10 14 4-4m-5 7-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m0-1 2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0"/>',
        "heart": '<path d="M12 21 3 12C-3 5 6-1 12 6c6-7 15-1 9 6z"/>',
        "arrow": '<path d="M12 3v18m-7-7 7 7 7-7M5 5h14"/>',
    }
    for start in range(0, len(badges), 4):
        for column, badge in zip(st.columns(4), badges[start : start + 4]):
            with column, st.container(border=True, key=f"badge-card-{badge['id']}"):
                path = glyphs.get(badge["symbol"], glyphs["star"])
                st.markdown(
                    '<div class="badge-emblem"><svg viewBox="0 0 24 24" fill="none" '
                    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
                    f'stroke-linejoin="round" role="img" aria-label="{html.escape(badge["name"], quote=True)} badge">{path}</svg></div>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"### {badge['name']}")
                if badge["earned"]:
                    st.markdown(f"**Earned · {badge.get('tier', 'Bronze')} tier**")
                    st.caption(badge["reason"])
                else:
                    current, target = badge_progress(
                        badge["id"], purchases, month, state.purchase_month_index
                    )
                    st.progress(
                        min(current / target, 1),
                        text=f"{current} of {target} toward next tier",
                    )
                    st.caption(badge["desc"])

    challenge_col, inbox_col = st.columns(2)
    with challenge_col:
        _render_weekly_challenges(purchases)
    with inbox_col:
        st.markdown(f"## Achievements inbox · {len(state.achievement_inbox)}")
        if state.achievement_inbox:
            for achievement in reversed(state.achievement_inbox):
                st.markdown(
                    f"**{achievement['name']}** · {achievement['month']}  \n"
                    f"{achievement['reason']}"
                )
            if st.button("Dismiss achievements", key="dismiss_achievements"):
                state.achievement_inbox = []
                st.rerun()
        else:
            st.caption("New badge unlocks stay here for you to revisit.")
    whats_next(*NEXT)


render()
