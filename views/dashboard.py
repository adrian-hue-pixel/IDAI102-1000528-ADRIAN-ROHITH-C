"""Monthly dashboard and trend exploration."""

import calendar

import pandas as pd
import streamlit as st

import charts
import logic as lg
import plan_tools as pt
from styles import CHART_COLORS, style_chart
from ui.common import (
    app_today,
    money,
    monthly_summary,
    page_header,
    render_stat_chip,
    whats_next,
)

NEXT = ("views/purchases.py", "Purchases", "Review, edit, or export your journal.")


def _show_chart_skeleton():
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(
            '<div class="chart-skeleton" role="status" '
            'aria-label="Preparing chart">'
            "<span></span><span></span><span></span>"
            "</div>",
            unsafe_allow_html=True,
        )
    return placeholder


@st.fragment
def _render_chart(
    purchases: list[dict],
    summary: dict,
    month: tuple[int, int],
    mode: str,
    goal: float,
    symbol: str,
    rate: float,
    goal_history: list[dict],
) -> None:
    chart_mode = st.radio(
        "Explore",
        ["Trend", "Category"],
        horizontal=True,
        key="dashboard_chart_mode",
    )
    if chart_mode == "Category":
        rows = [
            {
                "Category": category,
                "Estimated CO₂e (kg)": values["co2_kg"],
                f"Spend ({symbol})": round(values["spend_usd"] * rate, 2),
            }
            for category, values in summary["by_category"].items()
        ]
        measure = st.radio(
            "Compare categories by",
            ["Estimated CO₂e", "Spend"],
            horizontal=True,
            key="category_measure",
        )
        skeleton = _show_chart_skeleton()
        chart = charts.cached_category_chart(
            st.session_state.purchase_digest,
            rows,
            symbol,
            measure,
            list(CHART_COLORS[mode]["categories"]),
        )
        skeleton.empty()
        if chart is None:
            st.info("Category comparisons will appear after purchases are logged.")
        else:
            if len(rows) == 1:
                st.caption(
                    "One category logged this month."
                )
            st.altair_chart(style_chart(chart, mode), width="stretch")
            if st.checkbox("View as table", key="category_chart_as_table"):
                st.dataframe(
                    pd.DataFrame(rows),
                    hide_index=True,
                    width="stretch",
                    alt="Monthly category estimates and spending",
                )
        intent_items = [
            purchase
            for purchase in st.session_state.purchase_month_index.get(month, [])
            if purchase.get("intent") in lg.INTENTS
        ]
        if len(intent_items) >= 3 and st.checkbox(
            "Show purchase intent split", key="show_intent_split"
        ):
            intent_totals = []
            for intent in lg.INTENTS:
                matching = [
                    purchase for purchase in intent_items
                    if purchase["intent"] == intent
                ]
                if matching:
                    intent_totals.append(
                        {
                            "Intent": intent,
                            "Purchases": len(matching),
                            "Estimated CO₂e (kg)": round(
                                sum(item["co2_kg"] for item in matching), 1
                            ),
                        }
                    )
            st.markdown("**Purchase intent · illustrative estimates**")
            st.bar_chart(
                pd.DataFrame(intent_totals).set_index("Intent")[
                    ["Estimated CO₂e (kg)"]
                ],
                horizontal=True,
            )
            if st.checkbox(
                "View intent split as a text table",
                key="intent_split_as_table",
            ):
                st.dataframe(
                    pd.DataFrame(intent_totals),
                    hide_index=True,
                    width="stretch",
                    alt="Purchase intent split with purchase counts and estimated CO2e",
                )
        return

    month_index = st.session_state.purchase_month_index
    totals = lg.monthly_totals(purchases, month_index)
    forecast = None
    today = app_today()
    if month == lg.month_of(today) and summary["n"]:
        forecast = pt.forecast_month_end(
            summary["co2_kg"],
            today.day,
            calendar.monthrange(today.year, today.month)[1],
        )
    colors = CHART_COLORS[mode]
    if len(totals) == 1 and forecast is not None:
        st.caption(
            "This chart shows one month and a simple pace projection; it is not "
            "a month-to-month trend."
        )
    skeleton = _show_chart_skeleton()
    co2_chart, spend_chart = charts.cached_trend_charts(
        st.session_state.purchase_digest,
        totals,
        goal,
        rate,
        symbol,
        colors["line"],
        colors["spend"],
        colors["goal"],
        forecast_kg=forecast,
        goal_history=goal_history,
    )
    skeleton.empty()
    if co2_chart is None:
        st.caption(
            "Log purchases in two months to see a trend."
        )
    else:
        st.markdown("**Estimated CO₂e by month**")
        st.altair_chart(style_chart(co2_chart, mode), width="stretch")
        if st.checkbox("View as table", key="trend_co2_as_table"):
            st.dataframe(
                pd.DataFrame(totals)[["label", "co2_kg"]].rename(
                    columns={"label": "Month", "co2_kg": "Estimated CO₂e (kg)"}
                ),
                hide_index=True,
                width="stretch",
                alt="Estimated CO2e by month",
            )
        if forecast is not None:
            st.caption(
                f"Current pace: {forecast:.1f} kg CO₂e by month end. A projection, not a prediction."
            )
        st.markdown(f"**Spending by month · {symbol}**")
        st.altair_chart(style_chart(spend_chart, mode), width="stretch")
        if st.checkbox("View as table", key="trend_spend_as_table"):
            st.dataframe(
                pd.DataFrame(totals).assign(
                    Spend=lambda frame: frame["spend_usd"] * rate
                )[["label", "Spend"]].rename(columns={"label": "Month"}),
                hide_index=True,
                width="stretch",
                alt=f"Monthly spending in {symbol}",
            )


def render() -> None:
    page_header(
        "Dashboard",
        "Your spending, patterns and possibilities.",
        action_label="Open purchases",
        action_page=NEXT[0],
    )
    state = st.session_state
    purchases = state.purchases
    month = state.view_month
    mode = state.display_mode
    goal = lg.goal_for_month(state.goal_history, month, float(state.goal_kg))
    symbol, rate = lg.CURRENCIES[state.currency_name]
    summary = monthly_summary(purchases, month)
    monthly_low, monthly_high = lg.estimate_range(
        summary["co2_kg"], state.uncertainty_band / 100
    )
    month_index = state.purchase_month_index
    previous = lg.monthly_summary(
        purchases, lg.previous_month(month), month_index
    )

    if not purchases:
        st.markdown(
            '<section class="studio-empty dashboard-empty">'
            '<span class="section-label">YOUR MONTH, MADE VISIBLE</span>'
            '<h2>Start with one purchase.</h2>'
            '<p>See your spending and estimated footprint here, or try an example.</p>'
            '<div class="empty-metrics"><span>Spending<br><b>—</b></span>'
            '<span>Estimated CO₂e<br><b>—</b></span><span>Purchases<br><b>—</b></span></div>'
            '</section>',
            unsafe_allow_html=True,
        )
        start, demo = st.columns(2)
        start.page_link("views/home.py", label="Add your first purchase →")
        if demo.button("Try with 15 synthetic demo purchases", key="dashboard_load_demo"):
            from ui.actions import load_demo

            load_demo()
            st.rerun()
        st.page_link("views/impact_lab.py", label="Explore the model in Impact Lab →")
        return

    st.markdown("## Monthly overview")
    demo_count = sum(
        item.get("source") == "demo" for item in month_index.get(month, [])
    )
    month_caption = lg.month_label(month)
    if demo_count:
        month_caption += f" · Includes {demo_count} synthetic demo entries"
    st.caption(month_caption)
    monthly_rows = lg.monthly_totals(purchases, month_index)[-6:]
    monthly_counts = [len(month_index.get(row["ym"], [])) for row in monthly_rows]
    stats = [
        (
            "Spent",
            money(summary["spend_usd"], rate, symbol),
            [row["spend_usd"] * rate for row in monthly_rows],
        ),
        (
            "Estimated CO₂e",
            f"{summary['co2_kg']:.1f} kg",
            [row["co2_kg"] for row in monthly_rows],
        ),
        ("Purchases", str(summary["n"]), monthly_counts),
    ]
    swap_result = lg.swap_savings(purchases, month)
    if swap_result["count"]:
        stats.append(
            (
                "Saved through swaps",
                f"{swap_result['saved_kg']:.1f} kg CO₂e",
                [swap_result["saved_kg"]],
            )
        )
    chips = st.columns(len(stats))
    for col, (label, value, trend) in zip(chips, stats):
        with col:
            render_stat_chip(label, value, trend)
    st.caption(
        f"Monthly estimate: about {summary['co2_kg']:.0f} kg, model range between "
        f"{monthly_low:.0f} and {monthly_high:.0f} kilograms."
    )
    if swap_result["count"]:
        st.caption("Swap differences are illustrative, not verified savings.")

    left, right = st.columns([1.65, 1], vertical_alignment="top")
    with left, st.container(border=True, key="dashboard-charts"):
        st.markdown("### Patterns")
        _render_chart(
            purchases, summary, month, mode, goal, symbol, rate, state.goal_history,
        )
    with right:
        with st.container(border=True, key="dashboard-goal"):
            st.markdown("### Goal and momentum")
            ratio = summary["co2_kg"] / goal if goal else 0
            st.progress(
                min(ratio, 1),
                text=f"{summary['co2_kg']:.1f} of {goal:.0f} kg CO₂e",
            )
            st.caption("Your personal monthly goal.")
            streak = lg.goal_streak(
                purchases, goal, month, month_index, goal_history=state.goal_history,
            )
            st.metric("Goal streak", f"{streak} month(s)")
            momentum = lg.month_momentum(purchases, month, month_index)
            st.metric("Monthly momentum", momentum["status"])
            if previous["n"]:
                st.caption(
                    f"{summary['co2_kg'] - previous['co2_kg']:+.1f} kg vs last month."
                )
            if monthly_low <= goal <= monthly_high:
                st.caption("Your goal falls inside the model range.")
        with st.container(border=True, key="dashboard-insights"):
            st.markdown("### Insights")
            insights = lg.monthly_insights(purchases, month, month_index)
            if insights:
                for insight in insights:
                    st.markdown(f"- {insight}")
            else:
                st.caption("Add more entries to reveal patterns.")
            st.page_link("views/impact_lab.py", label="Test a change in Impact Lab →")

    st.markdown("### Highlights")
    peak = lg.peak_highlights(
        purchases, month, goal, month_index, goal_history=state.goal_history,
    )
    highlight_cols = st.columns(3)
    highlights = [
        ("Lowest impact", peak["best_choice"]["note"] if peak["best_choice"] else "No entries yet."),
        ("Leading category", peak["top_category"]["note"] if peak["top_category"] else "No category trend yet."),
        ("Goal status", peak["goal_status"]["message"]),
    ]
    for col, (title, text) in zip(highlight_cols, highlights):
        with col, st.container(border=True):
            st.markdown(f"#### {title}")
            st.write(text)
    st.caption("Illustrative model estimates. Personal goals are not scientific targets.")
    whats_next(*NEXT)


render()
