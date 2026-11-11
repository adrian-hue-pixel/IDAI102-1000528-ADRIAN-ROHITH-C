"""Code-native visual components for ShopImpact's two-mode studio."""

import html

import streamlit as st

ICONS = {
    "bag": '<path d="M5 8h14l1 13H4L5 8z"/><path d="M9 9V6a3 3 0 016 0v3"/>',
    "chart": '<path d="M4 20h17M7 16v-4m5 4V5m5 11V9"/>',
    "swap": '<path d="M4 8h15l-4-4M20 16H5l4 4"/>',
    "lab": '<path d="M9 3h6m-5 0v6l-5 9a2 2 0 002 3h10a2 2 0 002-3l-5-9V3M8 15h8"/>',
    "leaf": '<path d="M5 20C3 9 10 4 20 4c0 11-5 17-15 16zm0 0L15 10"/>',
    "book": '<path d="M4 4h6l2 2 2-2h6v16h-6l-2 1-2-1H4V4zm8 2v15"/>',
}


def icon(name: str) -> str:
    return ('<svg class="studio-icon" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def brand_html() -> str:
    return ('<div class="studio-brand">' + icon("leaf") + '<strong>ShopImpact<span>CONSUMPTION, CONSIDERED.</span></strong></div>')


def background_html(mode: str, reduce_motion: bool) -> str:
    """Bounded decorative layers with no JavaScript or network assets."""
    particles = ''.join(f'<i style="--x:{(i * 37 + 11) % 100}%;--y:{(i * 23 + 7) % 100}%;--delay:-{i % 7}s;--duration:{6 + i % 5}s"></i>' for i in range(22))
    return (f'<div class="studio-scene {"still" if reduce_motion else ""} {html.escape(mode.lower())}" aria-hidden="true">'
             '<div class="ambient ambient-one"></div><div class="ambient ambient-two"></div><div class="ambient ambient-three"></div>'
            '<svg class="scene-flow" viewBox="0 0 1440 1000" preserveAspectRatio="xMidYMid slice" fill="none">'
            '<path class="flow-track" d="M-140 820C160 330 400 1190 830 560S1420 160 1610-100"/>'
            '<path class="flow-track" d="M-100 80C360 540 540-230 1000 240S1370 1090 1550 830"/>'
            '<path class="flow-beam beam-one" d="M-140 820C160 330 400 1190 830 560S1420 160 1610-100"/>'
            '<path class="flow-beam beam-two" d="M-100 80C360 540 540-230 1000 240S1370 1090 1550 830"/>'
            '</svg>' 
            '<div class="scene-grid"></div><div class="scene-particles">' + particles + '</div></div>')


def home_hero() -> str:
    return ('<section class="studio-hero" aria-label="Welcome to ShopImpact">'
            '<div class="hero-emblem" aria-hidden="true"><div class="emblem-orbit"></div>'
            '<span class="orbit-point point-one"></span><span class="orbit-point point-two"></span>' + icon("bag") + '</div>'
            '<p class="hero-eyebrow">YOUR EVERYDAY IMPACT, EXPLAINED</p>'
            '<h2>Shop thoughtfully.<br><span class="hero-accent">See the bigger picture.</span></h2>'
            '<p class="hero-description">Track your purchases, test alternatives, '
            'and see how your habits add up.</p>'
            '<div class="hero-capabilities"><span>Purchase journal</span><span>Transparent estimates</span>'
            '<span>What-if experiments</span><span>Your growing garden</span></div></section>')


def render_tools() -> None:
    tools = [
        ("chart", "Dashboard", "Spending, categories and estimated footprint.", "views/dashboard.py", "Dashboard"),
        ("bag", "Purchase journal", "Keep, edit and export your purchase history.", "views/purchases.py", "Purchases"),
        ("lab", "Impact Lab", "Test the model and build a focused action plan.", "views/impact_lab.py", "Impact Lab"),
        ("swap", "Compare & plan", "Compare two choices before you buy.", "views/swaps_plan.py", "Swaps & plans"),
        ("leaf", "Your garden", "Meet Tilly and watch your journal grow.", "views/garden_badges.py", "Garden & badges"),
        ("book", "Month in review", "Keep a reflection and export your snapshot.", "views/month_review.py", "Month in review"),
    ]
    st.markdown('<div class="studio-section"><span>MADE FOR EVERYDAY CURIOSITY</span><h2>Your workspace</h2></div>', unsafe_allow_html=True)
    for start in range(0, len(tools), 3):
        for col, (glyph, title, description, page, label) in zip(st.columns(3), tools[start:start + 3]):
            with col, st.container(key=f"tool-{glyph}", border=True):
                st.markdown(f'<div class="tool-copy">{icon(glyph)}<h3>{title}</h3><p>{description}</p></div>', unsafe_allow_html=True)
                st.page_link(page, label=f"{label} →")
