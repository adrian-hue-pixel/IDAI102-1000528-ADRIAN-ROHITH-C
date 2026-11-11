"""Theme-aware cached SVG illustrations used by page views."""

import streamlit as st

import turtle_svg
from tilly_svg import mascot_svg


@st.cache_data(show_spinner=False)
def cached_mascot_svg(mood: str, theme: str, animate: bool) -> str:
    return mascot_svg(mood, theme, animate=animate)


@st.cache_data(show_spinner=False)
def cached_plant_svg(leaves: int, theme: str, animate: bool) -> str:
    return turtle_svg.plant_svg(leaves, theme, animate)


@st.cache_data(show_spinner=False)
def cached_footprint_svg(
    n_prints: int, theme: str, animate: bool, total: int = 8
) -> str:
    return turtle_svg.footprint_svg(n_prints, theme, animate, total=total)


@st.cache_data(show_spinner=False)
def cached_garden_svg(level: int, theme: str, animate: bool) -> str:
    return turtle_svg.garden_svg(level, theme, animate)
