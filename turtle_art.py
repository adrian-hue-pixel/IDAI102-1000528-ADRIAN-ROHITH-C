"""
ShopImpact - Turtle graphics.

WHY NOT THE STANDARD `turtle` MODULE?
The standard library `turtle` opens a desktop window (it needs Tk and a screen).
A deployed Streamlit app runs on a server with no screen, so it would crash.

SOLUTION: `TurtleCanvas` below is a tiny "headless turtle". It has the same
commands you know from turtle (forward, left, right, penup, goto, circle,
begin_fill, ...) but, instead of opening a window, it records the drawing and
renders it as a PNG (or an animated GIF that "draws itself" step by step).
The drawing functions underneath are written exactly like normal turtle code.
"""

import io
import math
from typing import Any

from PIL import Image, ImageDraw, ImageFont

BG = "#f6f1e4"  # warm beige, matches the app theme


# ----------------------------------------------------------------------------
# 1. THE HEADLESS TURTLE
# ----------------------------------------------------------------------------
class TurtleCanvas:
    """A turtle that draws onto an image. Origin (0, 0) is the centre, y points up."""

    def __init__(self, width: int = 300, height: int = 300, bg: str = BG) -> None:
        self.w, self.h, self.bg = width, height, bg
        self.x = self.y = 0.0
        self.heading = 0.0  # degrees, 0 = east, counter-clockwise
        self._pen_down = True
        self._pen_color, self._fill_color, self._width = "black", "black", 2
        self._ops = []  # recorded drawing operations
        self._seq = 0  # order in which things were drawn
        self._fill_pts = None
        self._fill_index = 0

    # --- pen & colour ------------------------------------------------------
    def penup(self) -> None:
        self._pen_down = False

    def pendown(self) -> None:
        self._pen_down = True

    def pensize(self, width: int) -> None:
        self._width = width

    def color(self, pen: str, fill: str | None = None) -> None:
        self._pen_color = pen
        self._fill_color = fill if fill is not None else pen

    def pencolor(self, c: str) -> None:
        self._pen_color = c

    def fillcolor(self, c: str) -> None:
        self._fill_color = c

    def speed(self, *_: Any) -> None:  # accepted for turtle-compatibility
        pass

    def hideturtle(self) -> None:
        pass

    # --- movement ----------------------------------------------------------
    def _next(self) -> int:
        self._seq += 1
        return self._seq

    def goto(self, x: float, y: float) -> None:
        if self._pen_down:
            self._ops.append(
                (
                    "line",
                    (self.x, self.y),
                    (x, y),
                    self._pen_color,
                    self._width,
                    self._next(),
                )
            )
        self.x, self.y = x, y
        if self._fill_pts is not None:
            self._fill_pts.append((x, y))

    def forward(self, distance: float) -> None:
        rad = math.radians(self.heading)
        self.goto(self.x + distance * math.cos(rad), self.y + distance * math.sin(rad))

    def backward(self, distance: float) -> None:
        self.forward(-distance)

    def left(self, angle: float) -> None:
        self.heading = (self.heading + angle) % 360

    def right(self, angle: float) -> None:
        self.left(-angle)

    def setheading(self, angle: float) -> None:
        self.heading = angle % 360

    def circle(self, radius: float, extent: float = 360) -> None:
        """Same as turtle.circle: centre is `radius` to the turtle's left."""
        sign = 1 if radius >= 0 else -1
        steps = max(10, int(abs(extent) / 4))
        step_angle = extent / steps
        chord = 2 * abs(radius) * math.sin(math.radians(abs(step_angle) / 2))
        for _ in range(steps):
            self.left(sign * step_angle / 2)
            self.forward(chord)
            self.left(sign * step_angle / 2)

    def dot(self, size: float = 6, color: str | None = None) -> None:
        self._ops.append(
            ("dot", (self.x, self.y), size, color or self._pen_color, self._next())
        )

    def write(
        self, text: str, size: int = 14, color: str = "black", bold: bool = True
    ) -> None:
        self._ops.append(
            ("text", (self.x, self.y), text, size, color, bold, self._next())
        )

    # --- filling -----------------------------------------------------------
    def begin_fill(self) -> None:
        self._fill_pts = [(self.x, self.y)]
        self._fill_index = len(self._ops)  # fill is inserted UNDER later outlines

    def end_fill(self) -> None:
        if self._fill_pts and len(self._fill_pts) > 2:
            self._ops.insert(
                self._fill_index,
                ("poly", list(self._fill_pts), self._fill_color, self._next()),
            )
        self._fill_pts = None

    # --- rendering ---------------------------------------------------------
    @property
    def steps(self) -> int:
        return self._seq

    def render(
        self, scale: float = 2.0, upto: int | None = None, supersample: int = 3
    ) -> Image.Image:
        """Draw everything (or only the first `upto` steps) and return a PIL image."""
        s = scale * supersample
        size = (int(self.w * s), int(self.h * s))
        img = Image.new("RGB", size, self.bg)
        draw = ImageDraw.Draw(img)

        def px(p):
            return ((p[0] + self.w / 2) * s, (self.h / 2 - p[1]) * s)

        for op in self._ops:
            if upto is not None and op[-1] > upto:
                continue
            kind = op[0]
            if kind == "poly":
                draw.polygon([px(p) for p in op[1]], fill=op[2])
            elif kind == "line":
                _, p1, p2, color, width, _ = op
                a, b, w = px(p1), px(p2), max(1, round(width * s))
                draw.line([a, b], fill=color, width=w)
                r = w / 2  # round the joints
                draw.ellipse([b[0] - r, b[1] - r, b[0] + r, b[1] + r], fill=color)
            elif kind == "dot":
                _, p, size, color, _ = op
                c, r = px(p), size * s / 2
                draw.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=color)
            elif kind == "text":
                _, p, text, size, color, bold, _ = op
                draw.text(
                    px(p),
                    text,
                    fill=color,
                    font=_font(int(size * s), bold),
                    anchor="mm",
                )
        final = (int(self.w * scale), int(self.h * scale))
        return img.resize(final, Image.LANCZOS)

    def to_png(self, scale: float = 2.0) -> bytes:
        buf = io.BytesIO()
        self.render(scale).save(buf, format="PNG")
        return buf.getvalue()

    def to_gif(
        self,
        frames: int = 34,
        scale: float = 1.4,
        step_ms: int = 55,
        hold_ms: int = 2500,
    ) -> bytes:
        """Animated GIF that re-draws the picture step by step (turtle-style)."""
        total = self.steps
        images = []
        for i in range(1, frames + 1):
            upto = int(total * i / frames)
            images.append(
                self.render(scale, upto=upto, supersample=2).convert(
                    "P", palette=Image.ADAPTIVE, colors=64
                )
            )
        durations = [step_ms] * (len(images) - 1) + [hold_ms]
        buf = io.BytesIO()
        images[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=images[1:],
            duration=durations,
            loop=0,
        )
        return buf.getvalue()


def _font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    """Try a nice font; fall back to Pillow's built-in one on any server."""
    names = ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf"] if bold else ["DejaVuSans.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# ----------------------------------------------------------------------------
# 2. DRAWING HELPERS (normal turtle-style code)
# ----------------------------------------------------------------------------
def draw_leaf(
    t: TurtleCanvas,
    x: float,
    y: float,
    axis: float,
    size: float,
    fill: str,
    outline: str = "#1b5e20",
) -> None:
    """A leaf: two 90-degree arcs make a lens shape, plus a centre vein.
    `axis` is the direction the leaf points (degrees)."""
    t.penup()
    t.goto(x, y)
    t.setheading(axis - 45)
    t.color(outline, fill)
    t.pensize(2)
    t.pendown()
    t.begin_fill()
    t.circle(size, 90)
    t.left(90)
    t.circle(size, 90)
    t.left(90)
    t.end_fill()
    # vein
    t.penup()
    t.goto(x, y)
    t.setheading(axis)
    t.pencolor(outline)
    t.pendown()
    t.forward(size * 1.25)
    t.penup()


def draw_ellipse(
    t: TurtleCanvas,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    rotation: float,
    fill: str,
) -> None:
    """Filled ellipse made from many small turtle moves (used for footprints)."""
    rot = math.radians(rotation)

    def point(deg):
        a = math.radians(deg)
        ex, ey = rx * math.cos(a), ry * math.sin(a)
        return (
            cx + ex * math.cos(rot) - ey * math.sin(rot),
            cy + ex * math.sin(rot) + ey * math.cos(rot),
        )

    t.penup()
    t.goto(*point(0))  # move to the start BEFORE filling
    t.color(fill, fill)
    t.pensize(1)
    t.pendown()
    t.begin_fill()
    for deg in range(15, 361, 15):
        t.goto(*point(deg))
    t.end_fill()
    t.penup()


def draw_footprint(
    t: TurtleCanvas,
    x: float,
    y: float,
    rotation: float,
    color: str,
    left_foot: bool = True,
) -> None:
    """One footprint: sole + heel + five toes, rotated and mirrored for the right foot."""
    mirror = 1 if left_foot else -1
    rot = math.radians(rotation)

    def place(dx, dy):  # local coords -> canvas coords
        dx *= mirror
        return (
            x + dx * math.cos(rot) - dy * math.sin(rot),
            y + dx * math.sin(rot) + dy * math.cos(rot),
        )

    sx, sy = place(0, 2)
    draw_ellipse(t, sx, sy, 9, 14, rotation, color)  # sole
    hx, hy = place(0, -16)
    draw_ellipse(t, hx, hy, 7, 7, rotation, color)  # heel
    for dx, dy, size in [
        (-8, 20, 7),
        (-2, 25, 6),
        (4, 24, 5.4),
        (9, 21, 4.8),
        (12, 16, 4.2),
    ]:
        tx, ty = place(dx, dy)
        t.penup()
        t.goto(tx, ty)
        t.dot(size, color)


# ----------------------------------------------------------------------------
# 3. THE THREE SCENES USED BY THE APP
# ----------------------------------------------------------------------------
def leaf_scene(n_leaves: int = 5, bg: str = BG) -> TurtleCanvas:
    """A little sprout that grows leaves - drawn when a user makes an eco-friendly choice."""
    n_leaves = max(3, min(n_leaves, 8))
    t = TurtleCanvas(280, 300, bg=bg)
    soil = "#8d6e63"
    pot = "#996b4d"
    rim = "#5d3a2d"
    stem = "#2e7d32"

    t.penup(); t.goto(-58, -130); t.color(rim, pot); t.pendown(); t.begin_fill()
    for p in [(-58, -130), (58, -130), (70, -82), (-70, -82)]:
        t.goto(*p)
    t.goto(-58, -130); t.end_fill()
    t.penup(); t.goto(-52, -118); t.color(soil, soil); t.pendown(); t.begin_fill()
    for p in [(-52, -118), (52, -118), (56, -92), (-56, -92)]:
        t.goto(*p)
    t.goto(-52, -118); t.end_fill()

    t.penup(); t.goto(0, -80); t.setheading(90); t.color(stem); t.pensize(5); t.pendown()
    steps = [18, 36, 54, 72, 90, 110, 120]
    for step in steps[: max(3, n_leaves)]:
        t.forward(step)
        if step < 100:
            t.left(12)
            draw_leaf(t, 0, -80 + step, 30 if step % 2 else 150, 18, "#76b86a", stem)
    draw_leaf(t, 0, 15, 90, 26, "#2e7d32", stem)
    for x, y, axis in [(-22, 22, 35), (20, 12, 145), (-18, 60, 25), (18, 58, 155)]:
        draw_leaf(t, x, y, axis, 20, "#8ed79a", stem)
    t.penup(); t.goto(0, 118); t.dot(8, "#f4d367"); t.dot(4, "#fff5c3")
    t.penup(); t.goto(0, 138); t.write("Eco win!", 16, "#2e7d32")
    return t


def footprint_scene(n_prints: int, color: str, bg: str = BG) -> TurtleCanvas:
    """A trail of footprints: more footprints = a bigger monthly carbon footprint."""
    n_prints = max(1, min(n_prints, 8))
    t = TurtleCanvas(280, 300, bg=bg)
    for i in range(n_prints):
        left = i % 2 == 0
        x = (-24 if left else 24) + (i % 3 - 1) * 4
        y = -110 + i * 30
        draw_footprint(t, x, y, -8 if left else 8, color, left_foot=left)
    return t


def garden_scene(level: int, bg: str = BG) -> TurtleCanvas:
    """Draw an ever-growing garden stage from seedlings to a small habitat."""
    if level < 0 or level > 5:
        raise ValueError("Garden level must be between 0 and 5.")
    t = TurtleCanvas(320, 230, bg=bg)
    soil = "#8d6e63"
    green = "#287452"
    t.penup()
    t.goto(-150, -84)
    t.setheading(0)
    t.color(soil)
    t.pensize(3)
    t.pendown()
    t.forward(300)
    for index in range(max(1, min(level + 1, 6))):
        x = -112 + index * 43
        height = 22 if level < 2 else 38 + (index % 2) * 8
        t.penup()
        t.goto(x, -82)
        t.setheading(90)
        t.color(green)
        t.pensize(3)
        t.pendown()
        t.forward(height)
        t.penup()
        draw_leaf(t, x, -68 + height // 2, 35, 17, "#88bd69", green)
        if level >= 3 and index % 2 == 0:
            t.penup()
            t.goto(x, -82 + height)
            t.dot(8, "#e2b84b")
            t.dot(4, "#ffffff")
        if level >= 2:
            t.penup()
            t.goto(x - 8, -82 + height)
            t.setheading(90)
            t.color(green)
            t.pensize(4)
            t.pendown()
            t.forward(height + 12)
            draw_ellipse(t, x - 8, -40 + height, 17, 24, -20, "#70a85a")
            draw_ellipse(t, x - 8, -4 + height, 15, 22, 18, "#82b76a")
    if level >= 4:
        draw_ellipse(t, 102, -72, 34, 12, 0, "#8bc6d0")
        t.penup()
        t.goto(100, -69)
        t.dot(5, "#f3d36b")
        t.penup()
        t.goto(111, -67)
        t.dot(4, "#f3d36b")
    if level >= 5:
        draw_ellipse(t, 124, -58, 14, 9, 0, "#e6ab76")
        t.penup()
        t.goto(130, -56)
        t.dot(2, "#173a2b")
    return t


def _symbol(t: TurtleCanvas, name: str, ring: str) -> None:
    """Little picture in the middle of a badge."""
    t.pensize(2)
    if name == "star":
        t.penup()
        t.goto(-32, -11)
        t.setheading(0)
        t.color(ring, "#ffd54f")
        t.pendown()
        t.begin_fill()
        for _ in range(5):
            t.forward(64)
            t.left(144)
        t.end_fill()
    elif name == "leaf":
        draw_leaf(t, -22, -26, 45, 36, "#66bb6a", ring)
    elif name == "sprout":
        t.penup()
        t.goto(0, -30)
        t.setheading(90)
        t.color("#2e7d32")
        t.pensize(4)
        t.pendown()
        t.forward(34)
        t.penup()
        draw_leaf(t, 0, 0, 40, 20, "#81c784", "#2e7d32")
        draw_leaf(t, 0, 8, 140, 20, "#a5d6a7", "#2e7d32")
    elif name == "heart":
        t.penup()
        t.goto(0, -28)
        t.setheading(0)
        t.color(ring, "#e91e63")
        t.pendown()
        t.begin_fill()
        t.left(50)
        t.forward(44)
        t.circle(17, 200)
        t.right(140)
        t.circle(17, 200)
        t.forward(44)
        t.end_fill()
    elif name == "arrow":
        t.penup()
        t.color(ring, "#26a69a")
        t.goto(-9, 30)
        t.pendown()
        t.begin_fill()
        for p in [(9, 30), (9, 4), (22, 4), (0, -26), (-22, 4), (-9, 4), (-9, 30)]:
            t.goto(*p)
        t.end_fill()
    elif name == "cycle":
        t.penup()
        t.goto(0, -24)
        t.setheading(0)
        t.color(ring)
        t.pensize(6)
        t.pendown()
        t.circle(24, 270)
        t.pensize(2)
        t.pencolor(ring)
        t.fillcolor(ring)
        t.begin_fill()
        t.left(135)
        t.forward(16)
        t.left(120)
        t.forward(16)
        t.left(120)
        t.forward(16)
        t.end_fill()
    elif name == "link":
        t.pensize(6)
        t.color(ring)
        for cx in (-11, 11):
            t.penup()
            t.goto(cx, -17)
            t.setheading(0)
            t.pendown()
            t.circle(17)
    t.penup()


def badge_scene(
    name: str,
    symbol: str,
    ring: str,
    fill: str,
    earned: bool = True,
    bg: str = BG,
) -> TurtleCanvas:
    """A turtle-drawn medal. Locked badges are drawn in grey."""
    if not earned:
        ring, fill = "#9e9e9e", "#e0e0e0"
    t = TurtleCanvas(220, 250, bg=bg)
    # ribbons
    for pts, col in [
        (
            [(-30, 40), (-6, 40), (-34, 108), (-52, 90)],
            "#5b8def" if earned else "#bdbdbd",
        ),
        ([(30, 40), (6, 40), (34, 108), (52, 90)], "#e07a5f" if earned else "#bdbdbd"),
    ]:
        t.penup()
        t.color(col, col)
        t.goto(*pts[0])
        t.pendown()
        t.begin_fill()
        for p in pts[1:]:
            t.goto(*p)
        t.goto(*pts[0])
        t.end_fill()
    # medal
    for radius, col, edge in [(62, fill, ring), (50, "#fffdf5", ring)]:
        t.penup()
        t.goto(0, -radius - 5)
        t.setheading(0)
        t.color(edge, col)
        t.pensize(4)
        t.pendown()
        t.begin_fill()
        t.circle(radius)
        t.end_fill()
    t.penup()
    t.goto(0, -5)
    if earned:
        _symbol(t, symbol, ring)
    else:
        t.goto(0, 0)
        t.write("?", 40, "#9e9e9e")
    t.penup()
    t.goto(0, -88)
    t.write(name, 13, ring if earned else "#757575")
    return t
