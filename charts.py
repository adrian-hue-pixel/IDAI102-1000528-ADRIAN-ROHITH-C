"""Altair chart builders used by the ShopImpact dashboard."""

import math
from collections.abc import Mapping, Sequence
from html import escape
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

import logic as lg

DEFAULT_CATEGORY_COLORS = [
    "#287452",
    "#547c90",
    "#a66d50",
    "#8a7b45",
    "#668b72",
    "#70658f",
    "#a65f66",
    "#627a9a",
    "#957458",
    "#557d7a",
    "#8a8650",
    "#865f88",
    "#658565",
    "#9b6b4e",
]


def sparkline_svg(values: Sequence[float], label: str) -> str:
    """Return a compact, screen-reader-labelled SVG for a short time series."""
    if not values:
        raise ValueError("A sparkline needs at least one value.")
    numeric = [float(value) for value in values]
    if any(not math.isfinite(value) for value in numeric):
        raise ValueError("Sparkline values must be finite numbers.")
    low, high = min(numeric), max(numeric)
    span = high - low or 1.0
    points = [
        (
            4 + index * 72 / max(len(numeric) - 1, 1),
            12 if high == low else 20 - (value - low) / span * 16,
        )
        for index, value in enumerate(numeric)
    ]
    if len(points) == 1:
        points = [(4, points[0][1]), (76, points[0][1])]
    path = " ".join(
        f"{'M' if index == 0 else 'L'} {x:.1f} {y:.1f}"
        for index, (x, y) in enumerate(points)
    )
    safe_label = escape(label, quote=True)
    return (
        '<svg viewBox="0 0 80 24" role="img" '
        f'aria-label="{safe_label} trend across recent months" focusable="false">'
        f"<title>{safe_label} trend across recent months</title>"
        f'<path d="{path}"/></svg>'
    )


def category_chart(
    rows: Sequence[Mapping[str, Any]],
    currency_symbol: str,
    measure: str,
    colors: Sequence[str] = DEFAULT_CATEGORY_COLORS,
) -> alt.Chart | None:
    """Build a single, toggleable monthly category comparison chart."""
    if not rows:
        return None
    frame = pd.DataFrame(rows)
    co2_field = "Estimated CO₂e (kg)"
    spend_field = f"Spend ({currency_symbol})"
    field = co2_field if measure == "Estimated CO₂e" else spend_field
    axis_title = (
        "Estimated kg CO₂e"
        if measure == "Estimated CO₂e"
        else f"Spend ({currency_symbol})"
    )
    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=5, size=18)
        .encode(
            y=alt.Y("Category:N", sort="-x", title=None),
            x=alt.X(
                f"{field}:Q",
                title=axis_title,
                axis=alt.Axis(format=",.1f" if measure == "Estimated CO₂e" else ",.0f"),
            ),
            color=alt.Color(
                "Category:N",
                scale=alt.Scale(domain=list(lg.PRODUCTS), range=list(colors)),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Category:N"),
                alt.Tooltip(f"{co2_field}:Q", format=",.1f"),
                alt.Tooltip(f"{spend_field}:Q", format=",.2f"),
            ],
        )
        .properties(height=max(180, 28 * len(rows)))
    )


def trend_charts(
    totals: Sequence[Mapping[str, Any]],
    goal_kg: float,
    currency_rate: float,
    currency_symbol: str,
    line_color: str = "#287452",
    spend_color: str = "#547c90",
    goal_color: str = "#a64c3e",
    forecast_kg: float | None = None,
    goal_history: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[alt.LayerChart | None, alt.Chart | None]:
    """Build monthly impact/spend charts and an optional dashed pace projection."""
    if len(totals) < 2 and forecast_kg is None:
        return None, None
    frame = pd.DataFrame(
        {
            "Month": [row["label"] for row in totals],
            "kg CO₂e": [row["co2_kg"] for row in totals],
            "Spend": [round(row["spend_usd"] * currency_rate, 2) for row in totals],
        }
    )
    co2_line = (
        alt.Chart(frame)
        .mark_line(
            point=alt.OverlayMarkDef(filled=True, size=55),
            color=line_color,
            strokeWidth=2.5,
        )
        .encode(
            x=alt.X("Month:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "kg CO₂e:Q", title="Estimated kg CO₂e", axis=alt.Axis(format=",.1f")
            ),
            tooltip=[alt.Tooltip("Month:N"), alt.Tooltip("kg CO₂e:Q", format=",.1f")],
        )
    )
    if goal_history is None:
        goal_rule = (
            alt.Chart(pd.DataFrame({"goal": [goal_kg]}))
            .mark_rule(
                color=goal_color,
                strokeDash=[6, 4],
                strokeWidth=1.5,
            )
            .encode(y=alt.Y("goal:Q"))
        )
    else:
        goal_frame = pd.DataFrame(
            {
                "Month": [row["label"] for row in totals],
                "goal": [
                    lg.goal_for_month(goal_history, tuple(row["ym"]), goal_kg)
                    for row in totals
                ],
            }
        )
        goal_rule = (
            alt.Chart(goal_frame)
            .mark_line(
                color=goal_color,
                strokeDash=[6, 4],
                strokeWidth=1.5,
                point=True,
            )
            .encode(
                x=alt.X("Month:N", sort=None, title=None),
                y=alt.Y("goal:Q"),
                tooltip=[
                    alt.Tooltip("Month:N"),
                    alt.Tooltip("goal:Q", title="Goal (kg)"),
                ],
            )
        )
    layers = [co2_line, goal_rule]
    if forecast_kg is not None and totals:
        forecast_frame = pd.DataFrame(
            {
                "Month": [
                    totals[-1]["label"],
                    f"{totals[-1]['label']} forecast",
                ],
                "kg CO₂e": [totals[-1]["co2_kg"], forecast_kg],
            }
        )
        forecast_line = (
            alt.Chart(forecast_frame)
            .mark_line(color=goal_color, strokeDash=[5, 4], strokeWidth=2)
            .encode(
                x=alt.X(
                    "Month:N",
                    sort=[row["label"] for row in totals]
                    + [f"{totals[-1]['label']} forecast"],
                    title=None,
                    axis=alt.Axis(labelAngle=0),
                ),
                y=alt.Y("kg CO₂e:Q", title="Estimated kg CO₂e"),
                tooltip=[
                    alt.Tooltip("Month:N"),
                    alt.Tooltip("kg CO₂e:Q", format=",.1f"),
                ],
            )
        )
        layers.append(forecast_line)
    co2_chart = alt.layer(*layers).properties(height=240)
    spend_chart = (
        alt.Chart(frame)
        .mark_bar(
            color=spend_color,
            cornerRadiusEnd=5,
        )
        .encode(
            x=alt.X("Month:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "Spend:Q",
                title=f"Spend ({currency_symbol})",
                axis=alt.Axis(format=",.0f"),
            ),
            tooltip=[alt.Tooltip("Month:N"), alt.Tooltip("Spend:Q", format=",.2f")],
        )
        .properties(height=220)
    )
    return co2_chart, spend_chart


@st.cache_data(show_spinner=False)
def cached_trend_charts(
    purchase_digest: str,
    totals: list[dict[str, Any]],
    goal_kg: float,
    currency_rate: float,
    currency_symbol: str,
    line_color: str,
    spend_color: str,
    goal_color: str,
    forecast_kg: float | None = None,
    goal_history: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[alt.LayerChart | None, alt.Chart | None]:
    """Cache dashboard trend charts against the journal's content digest."""
    return trend_charts(
        totals,
        goal_kg,
        currency_rate,
        currency_symbol,
        line_color,
        spend_color,
        goal_color,
        forecast_kg,
        goal_history,
    )


@st.cache_data(show_spinner=False)
def cached_category_chart(
    purchase_digest: str,
    rows: list[dict[str, Any]],
    currency_symbol: str,
    measure: str,
    colors: list[str],
) -> alt.Chart | None:
    """Cache category charts against the journal's content digest."""
    return category_chart(rows, currency_symbol, measure, colors)
