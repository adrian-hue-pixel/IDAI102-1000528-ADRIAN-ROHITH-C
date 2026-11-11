"""Contract and turtle-command tests for animated SVG drawings."""

import math
import xml.etree.ElementTree as ET

import pytest

from turtle_svg import SvgTurtle, footprint_svg, garden_svg, plant_svg

SVG_NS = "{http://www.w3.org/2000/svg}"
THEMES = ("Light", "Dark")
DRAWINGS = (
    ("plant", range(1, 9), plant_svg),
    ("footprints", range(9), footprint_svg),
    ("garden", range(6), garden_svg),
)


@pytest.mark.parametrize(
    ("drawing", "values", "render"),
    [
        (name, value, render)
        for name, value_range, render in DRAWINGS
        for value in value_range
    ],
)
@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("animate", (True, False))
def test_every_svg_variant_is_accessible_valid_and_deterministic(
    drawing, values, render, theme, animate
):
    svg = render(values, theme, animate)
    root = ET.fromstring(svg)

    assert root.tag == f"{SVG_NS}svg"
    assert root.get("viewBox")
    assert root.get("aria-label")
    assert len(svg.encode("utf-8")) < 80 * 1024
    assert render(values, theme, animate) == svg


@pytest.mark.parametrize(
    ("render", "value"),
    [
        (plant_svg, 4),
        (footprint_svg, 4),
        (garden_svg, 3),
    ],
)
def test_motion_setting_controls_svg_styles(render, value):
    static = render(value, "Ivory", False)
    animated = render(value, "Ivory", True)

    assert "<style" not in static
    assert "<style" in animated
    assert "@keyframes" in animated
    assert "@media (prefers-reduced-motion:reduce)" in animated


@pytest.mark.parametrize(
    ("render", "value"),
    [
        (plant_svg, 5),
        (footprint_svg, 4),
        (garden_svg, 3),
    ],
)
@pytest.mark.parametrize("time", (0.0, 0.4, 1.0, 2.0, 4.0))
def test_svg_frame_rendering_accepts_animation_times(render, value, time):
    root = ET.fromstring(render(value, "Obsidian", True, t=time))

    assert root.tag == f"{SVG_NS}svg"


def test_turtle_forward_and_turn_move_as_expected():
    turtle = SvgTurtle(100, 100)

    turtle.forward(10)
    assert math.isclose(turtle.x, 0, abs_tol=1e-9)
    assert math.isclose(turtle.y, 10)

    turtle.left(90)
    turtle.forward(5)
    assert math.isclose(turtle.x, -5)
    assert math.isclose(turtle.y, 10)


def test_turtle_full_circle_returns_to_its_start():
    turtle = SvgTurtle(100, 100)
    start = (turtle.x, turtle.y)

    turtle.circle(20, 360)

    assert turtle.x == pytest.approx(start[0], abs=1e-9)
    assert turtle.y == pytest.approx(start[1], abs=1e-9)


def test_turtle_fill_produces_a_fill_path():
    turtle = SvgTurtle(100, 100)
    turtle.fillcolor("#123456")
    turtle.begin_fill()
    turtle.goto(10, 0)
    turtle.goto(10, 10)
    turtle.goto(0, 10)
    turtle.end_fill()

    root = ET.fromstring(turtle.render("filled shape", animate=False))
    fills = root.findall(f"{SVG_NS}path[@class='f']")

    assert len(fills) == 1
    assert fills[0].get("fill") == "#123456"


def test_turtle_penup_records_no_stroke():
    turtle = SvgTurtle(100, 100)

    turtle.penup()
    turtle.goto(10, 10)
    turtle.forward(20)

    root = ET.fromstring(turtle.render("pen up", animate=False))
    assert root.findall(f"{SVG_NS}path[@class='s']") == []


def test_nested_turtle_groups_render_balanced_svg_groups():
    turtle = SvgTurtle(100, 100)
    with turtle.group("pop"), turtle.group("grow"):
        turtle.forward(10)

    svg = turtle.render("nested groups")
    root = ET.fromstring(svg)

    assert root.tag == f"{SVG_NS}svg"
    assert svg.count("<g ") == svg.count("</g>")
    assert len(root.findall(f".//{SVG_NS}g")) == 2


@pytest.mark.parametrize(("mode", "legacy"), [("Light", "Ivory"), ("Dark", "Obsidian")])
def test_current_display_modes_use_compatible_drawing_palettes(mode, legacy):
    assert plant_svg(4, mode, False) == plant_svg(4, legacy, False)
