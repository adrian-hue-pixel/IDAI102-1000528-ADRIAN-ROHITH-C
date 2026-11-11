"""Two accessible display modes and the shared ShopImpact studio stylesheet."""

from pathlib import Path

import altair as alt
import streamlit as st

BLUE = "#547c90"
BROWN = "#a66d50"
STYLE_PATH = Path(__file__).with_name("studio.css")
DISPLAY_MODES = ("Light", "Dark")
LEGACY_MODES = {"Ivory": "Light", "Obsidian": "Dark", "High contrast": "Dark"}


def normalize_mode(mode: str) -> str:
    """Migrate saved appearance names without losing the user's journal."""
    normalized = LEGACY_MODES.get(mode, mode)
    if normalized not in DISPLAY_MODES:
        raise ValueError("Saved display mode is unsupported.")
    return normalized


THEMES = {
    "Light": {
        "page": "#f6f8f7", "surface": "#ffffff", "surface_raised": "#ffffff",
        "surface_high": "#edf2ef", "ink": "#1b2823", "muted": "#58675f",
        "line": "#dce5df", "accent": "#24694f", "accent_glow": "#4e9277",
        "hero": "#ffffff", "button": "#24694f", "button_text": "#ffffff",
        "goal_over": "#98554c", "shadow": "rgba(27, 40, 35, .07)",
    },
    "Dark": {
        "page": "#0b0d10", "surface": "#15191d", "surface_raised": "#1b2025",
        "surface_high": "#22292e", "ink": "#f0f3f1", "muted": "#a6b2ac",
        "line": "#2b3438", "accent": "#8bcdb5", "accent_glow": "#a5dcc8",
        "hero": "#15191d", "button": "#8bcdb5", "button_text": "#10251d",
        "goal_over": "#e3a396", "shadow": "rgba(0, 0, 0, .28)",
    },
}

CHART_COLORS = {
    "Light": {
        "line": "#24694f", "spend": "#276d78", "goal": "#98554c",
        "categories": ["#24694f", "#276d78", "#694a91", "#934b43", "#496b2b",
                       "#315d91", "#995b23", "#786044", "#17665d", "#704568",
                       "#535f8e", "#84542c", "#365f50", "#874c65"],
    },
    "Dark": {
        "line": "#8bcdb5", "spend": "#81c7cb", "goal": "#e3a396",
        "categories": ["#8bcdb5", "#9bc4d6", "#e3a985", "#e1d990", "#d6a7d1",
                       "#c8bbf0", "#ffb3b8", "#a8d5c6", "#f0c98d", "#89d8df",
                       "#d2e68b", "#ffcb9a", "#aad5ff", "#e6a5c8"],
    },
}

# Legacy preference keys remain valid on import; all use the studio accent.
ACCENT_PALETTES = {
    name: {mode: theme["accent"] for mode, theme in THEMES.items()}
    for name in ("Evergreen", "Spring canopy", "Autumn harvest")
}


def load_stylesheet() -> str:
    """Load one stylesheet, avoiding accumulated redesign overrides."""
    return STYLE_PATH.read_text(encoding="utf-8")


def inject_css(
    mode: str,
    accent_palette: str = "Evergreen",
    reduce_motion: bool = False,
    text_size: str = "M",
    dyslexia_font: bool = False,
) -> None:
    """Apply the studio stylesheet, accessibility settings, and active palette."""
    mode = normalize_mode(mode)
    theme = THEMES[mode]
    size_scale = {"S": 0.92, "M": 1.0, "L": 1.08, "XL": 1.18}.get(text_size, 1.0)
    font_family = (
        "'Atkinson Hyperlegible', 'Segoe UI', sans-serif" if dyslexia_font
        else "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    )
    variables = {
        **{name.replace("_", "-"): value for name, value in theme.items()},
        "blue": BLUE, "brown": BROWN,
        "motion-duration": "0ms" if reduce_motion else "220ms",
        "polish-duration": "0ms" if reduce_motion else "600ms",
        "motion-play-state": "paused" if reduce_motion else "running",
        "motion-ease": "cubic-bezier(.2,.8,.2,1)",
        "font-scale": str(size_scale), "font-family": font_family,
        "font-display": font_family,
        "accent-muted": "#e4eee8" if mode == "Light" else "#21332b",
        "button-background": theme["button"],
        "radius-small": "10px", "radius-card": "18px", "radius-large": "24px",
        "color-scheme": mode.lower(),
        "bg": theme["page"], "text": theme["ink"], "border": theme["line"],
        "card": theme["surface"], "card2": theme["surface_raised"],
        "field": theme["surface_raised"], "pop": theme["surface"],
        "side": theme["surface"], "accent-soft": "#e4eee8" if mode == "Light" else "#21332b",
        "btn-text": theme["button_text"],
        "ambient-one": "rgba(94, 150, 125, .15)" if mode == "Light" else "rgba(83, 148, 122, .13)",
        "ambient-two": "rgba(122, 153, 191, .12)" if mode == "Light" else "rgba(91, 114, 175, .11)",
    }
    declarations = ";".join(f"--{name}:{value}" for name, value in variables.items())
    motion_override = (
        "*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important;}"
        if reduce_motion else ""
    )
    st.markdown(
        f"<style>{load_stylesheet()}\n:root{{{declarations};color-scheme:{mode.lower()}}}"
        f"{motion_override}</style>", unsafe_allow_html=True,
    )


def style_chart(chart: alt.TopLevelMixin, mode: str) -> alt.TopLevelMixin:
    """Match charts to the active display mode without decorative chart frames."""
    theme = THEMES[normalize_mode(mode)]
    return (
        chart.configure(background="transparent")
        .configure_view(stroke=None)
        .configure_axis(labelColor=theme["muted"], titleColor=theme["ink"],
                        gridColor=theme["line"], tickColor=theme["line"])
        .configure_legend(labelColor=theme["ink"], titleColor=theme["ink"])
    )
