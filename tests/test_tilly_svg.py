"""Contract checks for Tilly's theme-aware vector artwork."""

import base64
import re
import xml.etree.ElementTree as ET

import pytest

from tilly_svg import MOODS, THEMES, mascot_svg

SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
SVG_DATA_URI = re.compile(r'data:image/svg\+xml;base64,([^"]+)')


@pytest.mark.parametrize("mood", MOODS)
@pytest.mark.parametrize("theme", THEMES)
def test_every_mood_and_theme_returns_accessible_svg(mood, theme):
    svg = mascot_svg(mood, theme)

    root = ET.fromstring(svg)
    assert root.tag == f"{SVG_NAMESPACE}svg"
    assert root.get("viewBox")
    assert root.get("aria-label") == f"Tilly the turtle looking {mood}"


def test_static_mascot_has_no_animation_styles():
    root = ET.fromstring(mascot_svg("happy", "Earth (default)", animate=False))

    assert root.find(f"{SVG_NAMESPACE}style") is None


@pytest.mark.parametrize(
    ("display_mode", "svg_theme"),
    [("Light", "Earth (default)"), ("Dark", "Dark"), ("Ivory", "Earth (default)"), ("Obsidian", "Dark")],
)
def test_current_display_modes_select_the_matching_svg_palette(display_mode, svg_theme):
    assert mascot_svg("happy", display_mode) == mascot_svg("happy", svg_theme)


def test_tilly_data_uri_decodes_to_valid_svg():
    svg = mascot_svg("curious", "High contrast")
    data_uri = f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"
    encoded_svg = SVG_DATA_URI.fullmatch(data_uri)

    assert encoded_svg is not None
    root = ET.fromstring(base64.b64decode(encoded_svg.group(1)))
    assert root.tag == f"{SVG_NAMESPACE}svg"
    assert root.get("viewBox") == "0 0 280 200"
