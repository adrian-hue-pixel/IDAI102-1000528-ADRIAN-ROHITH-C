"""Animated Turtle drawings for ShopImpact, rendered as crisp SVG.

Every picture is made with real turtle commands (forward, left, right, circle,
goto, begin_fill, end_fill, penup, pendown, pencolor, pensize, fillcolor).
SvgTurtle records the pen path, then renders it as vector paths that the
browser animates (the pen "draws" the stems, shapes pop and grow, plants sway).

Public API (all return an SVG string; embed as a base64 data-URI <img> and give
it alt text, exactly like the Tilly mascot):

    plant_svg(leaves, theme, animate)       growing plant ("eco win" sprout)
    footprint_svg(n_prints, theme, animate) footprint trail, n of total filled
    garden_svg(level, theme, animate)       Eco Garden, level 0-5 (0 = resting)

animate=False gives the finished picture with no CSS animation (Reduce motion).
The CSS also switches animation off under prefers-reduced-motion.
render(..., t=seconds) returns a still frame of the animation (for tests/previews).
"""
from __future__ import annotations

import itertools
import math
from contextlib import contextmanager

# --------------------------------------------------------------------------
# Palettes (keys match the app's theme names)
# --------------------------------------------------------------------------
PALETTES: dict[str, dict[str, str]] = {
    "Ivory": {
        "leaf": "#3f9b6b", "leaf_dark": "#1f6b47", "leaf_light": "#86d3a6", "stem": "#2e7d55",
        "pot": "#c4774a", "pot_dark": "#8f4f2c", "soil": "#5a3b2a", "ground": "#a6d9b2", "ground2": "#7fc194",
        "trunk": "#8a5a3b", "petal": "#f08fa6", "centre": "#f5c542", "foot": "#087653", "ghost": "#c3cfc8",
        "sun": "#f5b83d", "cloud": "#e3ece7", "ink": "#16352a", "star": "#e9a825",
    },
    "Obsidian": {
        "leaf": "#3fc794", "leaf_dark": "#1a7f5b", "leaf_light": "#8cf0c8", "stem": "#2fae82",
        "pot": "#c8805a", "pot_dark": "#8f5434", "soil": "#3b271d", "ground": "#1b5444", "ground2": "#236b57",
        "trunk": "#a8704c", "petal": "#ff9fb8", "centre": "#ffd166", "foot": "#53d9a7", "ghost": "#2f4d44",
        "sun": "#ffd166", "cloud": "#2a463e", "ink": "#d9f5ea", "star": "#ffd166",
    },
    "High contrast": {
        "leaf": "#00ff6a", "leaf_dark": "#009c42", "leaf_light": "#a8ffc9", "stem": "#00d45a",
        "pot": "#ff9d00", "pot_dark": "#a86100", "soil": "#7a5200", "ground": "#007a35", "ground2": "#00a847",
        "trunk": "#ffb84d", "petal": "#ff7ac8", "centre": "#ffff00", "foot": "#00ff00", "ghost": "#6b6b6b",
        "sun": "#ffff00", "cloud": "#5a5a5a", "ink": "#ffffff", "star": "#ffff00",
    },
}
# Cohesive studio artwork: ceramic planters, sage foliage and muted highlights.
PALETTES["Ivory"].update({
    "leaf": "#7ba88b", "leaf_dark": "#39664f", "leaf_light": "#b9d4ab",
    "stem": "#4c7e61", "pot": "#e5e8de", "pot_dark": "#9aab9b",
    "soil": "#6d7665", "ground": "#dce7dc", "ground2": "#e8eee3",
    "petal": "#d8b5aa", "centre": "#d9c48c", "foot": "#7eaa90",
    "ghost": "#e2e8e1", "sun": "#d4c18f", "cloud": "#e4e9e6",
    "star": "#a4b5a1", "ink": "#345745",
})
PALETTES["Obsidian"].update({
    "leaf": "#82b297", "leaf_dark": "#477d66", "leaf_light": "#b4d9ba",
    "stem": "#6e9e84", "pot": "#52665f", "pot_dark": "#344b41",
    "soil": "#253a2f", "ground": "#263e33", "ground2": "#1e3129",
    "petal": "#cba9aa", "centre": "#d2c394", "foot": "#8fc0a6",
    "ghost": "#293d34", "sun": "#c9bb8c", "cloud": "#2b3c35",
    "star": "#a0c4ac", "ink": "#c8ded0",
})
_ALIASES = {"Earth (default)": "Ivory", "Light": "Ivory", "Dark": "Obsidian"}


def palette(theme: str) -> dict[str, str]:
    return PALETTES[_ALIASES.get(theme, theme)] if _ALIASES.get(theme, theme) in PALETTES else PALETTES["Ivory"]


# --------------------------------------------------------------------------
# The turtle
# --------------------------------------------------------------------------
class SvgTurtle:
    """A tiny turtle. Origin is bottom-centre of the canvas, +y is up, heading in
    degrees counter-clockwise from east (like Python's turtle). Starts facing up."""

    def __init__(self, width: int, height: int):
        self.w, self.h = width, height
        self.x = self.y = 0.0
        self.heading = 90.0
        self.down = True
        self._color, self._width, self._fill = "#000000", 2.0, "#000000"
        self.elements: list[dict] = []
        self.groups: list[dict] = []
        self._gstack: list[int] = []
        self._cur: dict | None = None
        self._filling: dict | None = None

    # -- coordinates ------------------------------------------------------
    def _s(self, x: float, y: float) -> tuple[float, float]:
        return (self.w / 2 + x, self.h - y)

    # -- pen state --------------------------------------------------------
    def penup(self) -> None:
        self._flush()
        self.down = False

    def pendown(self) -> None:
        self.down = True

    def pencolor(self, color: str) -> None:
        self._flush()
        self._color = color

    def pensize(self, width: float) -> None:
        self._flush()
        self._width = width

    def fillcolor(self, color: str) -> None:
        self._fill = color

    def setheading(self, angle: float) -> None:
        self.heading = angle % 360

    def left(self, angle: float) -> None:
        self.heading = (self.heading + angle) % 360

    def right(self, angle: float) -> None:
        self.heading = (self.heading - angle) % 360

    # -- movement ---------------------------------------------------------
    def _move_to(self, x: float, y: float) -> None:
        if self.down:
            if self._cur is None:
                self._cur = {"kind": "stroke", "pts": [self._s(self.x, self.y)], "stroke": self._color,
                                 "width": self._width, "groups": tuple(self._gstack)}
            self._cur["pts"].append(self._s(x, y))
        if self._filling is not None:
            self._filling["pts"].append(self._s(x, y))
        self.x, self.y = x, y

    def forward(self, dist: float) -> None:
        r = math.radians(self.heading)
        self._move_to(self.x + dist * math.cos(r), self.y + dist * math.sin(r))

    def backward(self, dist: float) -> None:
        self.forward(-dist)

    def goto(self, x: float, y: float) -> None:
        self._move_to(x, y)

    def circle(self, radius: float, extent: float = 360, steps: int | None = None) -> None:
        """Python-turtle semantics: centre is to the left of the heading for radius > 0."""
        n = steps or max(10, int(abs(extent) / 6))
        step = extent / n
        chord = 2 * abs(radius) * math.sin(math.radians(abs(step)) / 2)
        sign = 1 if radius > 0 else -1
        for _ in range(n):
            self.left(sign * step / 2)
            self.forward(chord)
            self.left(sign * step / 2)

    # -- fills ------------------------------------------------------------
    def begin_fill(self) -> None:
        self._flush()
        self._filling = {"kind": "fill", "pts": [self._s(self.x, self.y)], "fill": self._fill,
                             "groups": tuple(self._gstack), "at": len(self.elements)}

    def end_fill(self) -> None:
        self._flush()
        f, self._filling = self._filling, None
        if f and len(f["pts"]) > 2:
            self.elements.insert(f.pop("at"), f)

    def _flush(self) -> None:
        if self._cur and len(self._cur["pts"]) > 1:
            self.elements.append(self._cur)
        self._cur = None

    # -- animation groups -------------------------------------------------
    @contextmanager
    def group(self, anim: str | None = None, delay: float = 0.0, dur: float = 0.6,
              origin: tuple[float, float] = (0, 0), **extra):
        self._flush()
        self.groups.append(dict(anim=anim, delay=delay, dur=dur, origin=self._s(*origin), **extra))
        self._gstack.append(len(self.groups) - 1)
        try:
            yield
        finally:
            self._flush()
            self._gstack.pop()

    # ======================================================================
    # Rendering
    # ======================================================================
    def render(self, label: str, animate: bool = True, t: float | None = None) -> str:
        body: list[str] = []
        open_ids: list[int] = []
        for el in self.elements:
            gids = list(el["groups"])
            common = 0
            while common < len(open_ids) and common < len(gids) and open_ids[common] == gids[common]:
                common += 1
            for _ in range(len(open_ids) - common):
                body.append("</g>")
            open_ids = open_ids[:common]
            for gid in gids[common:]:
                body.append(self._open_group(self.groups[gid], animate, t))
                open_ids.append(gid)
            body.append(self._element(el, open_ids, animate, t))
        body.extend("</g>" for _ in open_ids)
        css = _CSS if (animate and t is None) else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'role="img" aria-label="{label}">{css}{"".join(body)}</svg>')

    @staticmethod
    def _path(pts, close=False) -> str:
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        return d + ("Z" if close else "")

    def _element(self, el, open_ids, animate, t) -> str:
        if el["kind"] == "fill":
            extra = ""
            if t is not None:
                op = _frame_fill_opacity(self, open_ids, t)
                extra = f' opacity="{op:.2f}"' if op < 1 else ""
            return f'<path class="f" d="{self._path(el["pts"], True)}" fill="{el["fill"]}"{extra}/>'
        pts = el["pts"]
        base = (f'class="s" d="{self._path(pts)}" fill="none" stroke="{el["stroke"]}" '
                f'stroke-width="{el["width"]}" stroke-linecap="round" stroke-linejoin="round"')
        if t is not None:
            prog = _frame_draw_progress(self, open_ids, t)
            if prog < 1:
                length = sum(math.dist(a, b) for a, b in itertools.pairwise(pts))
                if prog <= 0:
                    return ""
                return (f'<path {base} stroke-dasharray="{length:.1f} {length + 5:.1f}" '
                        f'stroke-dashoffset="{length * (1 - prog):.1f}"/>')
            return f"<path {base}/>"
        if animate and any(self.groups[g]["anim"] == "draw" for g in open_ids):
            return f'<path {base} pathLength="1"/>'
        return f"<path {base}/>"

    def _open_group(self, g, animate, t) -> str:
        ox, oy = g["origin"]
        if t is not None:
            tx, ty, sx, sy, rot, op = _frame_transform(g, t)
            tr = (f'translate({ox + tx:.2f} {oy + ty:.2f}) rotate({rot:.2f}) scale({sx:.3f} {sy:.3f}) '
                  f'translate({-ox:.2f} {-oy:.2f})')
            return f'<g transform="{tr}" opacity="{op:.2f}">'
        if not animate or not g["anim"]:
            return "<g>"
        return (f'<g class="a-{g["anim"]}" style="--d:{g["delay"]}s;--t:{g["dur"]}s;'
                f'transform-origin:{ox:.1f}px {oy:.1f}px">')


# --------------------------------------------------------------------------
# CSS animation (draw-on, pop, grow, sway, spin, twinkle, drift, flit, flap, pulse)
# --------------------------------------------------------------------------
_CSS = """<style>
g{transform-box:view-box}
.a-draw path.s{animation:draw var(--t) ease-out var(--d) backwards}
.a-draw path.f{animation:fade .5s ease-out calc(var(--d) + var(--t)*.55) backwards}
.a-pop{animation:pop var(--t) cubic-bezier(.3,1.5,.5,1) var(--d) backwards}
.a-grow{animation:grow var(--t) cubic-bezier(.3,1.4,.5,1) var(--d) backwards}
.a-fade{animation:fade var(--t) ease-out var(--d) backwards}
.a-sway{animation:sway var(--t) ease-in-out var(--d) infinite alternate}
.a-spin{animation:spin var(--t) linear var(--d) infinite}
.a-twinkle{animation:twinkle var(--t) ease-in-out var(--d) infinite}
.a-pulse{animation:pulse var(--t) ease-in-out var(--d) infinite}
.a-drift{animation:drift var(--t) ease-in-out var(--d) infinite alternate}
.a-flit{animation:flit var(--t) ease-in-out var(--d) infinite}
.a-flap{animation:flap .28s ease-in-out infinite alternate}
@keyframes draw{from{stroke-dasharray:1;stroke-dashoffset:1}to{stroke-dasharray:1;stroke-dashoffset:0}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes pop{0%{transform:scale(0);opacity:0}100%{transform:scale(1);opacity:1}}
@keyframes grow{0%{transform:scale(.3,0);opacity:0}100%{transform:scale(1,1);opacity:1}}
@keyframes sway{from{transform:rotate(-1.8deg)}to{transform:rotate(1.8deg)}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes twinkle{0%,100%{transform:scale(.7);opacity:.55}50%{transform:scale(1.15);opacity:1}}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.07)}}
@keyframes drift{from{transform:translateX(-7px)}to{transform:translateX(9px)}}
@keyframes flit{0%,100%{transform:translate(0,0)}25%{transform:translate(30px,-12px)}50%{transform:translate(56px,8px)}75%{transform:translate(24px,18px)}}
@keyframes flap{from{transform:scaleX(1)}to{transform:scaleX(.35)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style>"""


# --------------------------------------------------------------------------
# Frame maths (mirror of the CSS, used only when render(t=...) is called)
# --------------------------------------------------------------------------
def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _ease_out(p: float) -> float:
    return 1 - (1 - p) ** 3


def _overshoot(p: float) -> float:
    c1, c3 = 1.4, 2.4
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2


def _frame_transform(g, t):
    a, d, dur = g["anim"], g["delay"], g["dur"]
    p = _clamp((t - d) / dur) if dur else 1.0
    tx = ty = rot = 0.0
    sx = sy = op = 1.0
    if a == "pop":
        s = max(0.0, _overshoot(p)) if p > 0 else 0.0
        sx = sy = s if t >= d else 0.0
        op = 1.0 if t >= d else 0.0
    elif a == "grow":
        s = max(0.0, _overshoot(p))
        sx, sy = (0.3 + 0.7 * s, s) if t >= d else (0.3, 0.0)
        op = 1.0 if t >= d else 0.0
    elif a == "fade":
        op = _ease_out(p)
    elif a == "sway":
        k = ((t - d) / dur) % 2 if t > d else 0
        k = k if k <= 1 else 2 - k
        rot = -1.8 + 3.6 * k
    elif a == "spin":
        rot = ((t - d) / dur * 360) % 360 if t > d else 0
    elif a == "twinkle":
        k = ((t - d) / dur) % 1 if t > d else 0
        w = 0.5 - 0.5 * math.cos(2 * math.pi * k)
        sx = sy = 0.7 + 0.45 * w
        op = 0.55 + 0.45 * w
    elif a == "pulse":
        k = ((t - d) / dur) % 1 if t > d else 0
        sx = sy = 1 + 0.07 * (0.5 - 0.5 * math.cos(2 * math.pi * k))
    elif a == "drift":
        k = ((t - d) / dur) % 2 if t > d else 0
        k = k if k <= 1 else 2 - k
        tx = -7 + 16 * k
    elif a == "flit":
        k = ((t - d) / dur) % 1 if t > d else 0
        pts = [(0, 0), (30, -12), (56, 8), (24, 18), (0, 0)]
        i = min(int(k * 4), 3)
        f = k * 4 - i
        tx = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f
        ty = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f
    elif a == "flap":
        sx = 0.675 + 0.325 * math.cos(2 * math.pi * t / 0.56)
    return tx, ty, sx, sy, rot, op


def _frame_draw_progress(tt, open_ids, t) -> float:
    for gid in reversed(open_ids):
        g = tt.groups[gid]
        if g["anim"] == "draw":
            return _clamp((t - g["delay"]) / g["dur"])
    return 1.0


def _frame_fill_opacity(tt, open_ids, t) -> float:
    for gid in reversed(open_ids):
        g = tt.groups[gid]
        if g["anim"] == "draw":
            return _clamp((t - (g["delay"] + g["dur"] * 0.55)) / 0.5)
    return 1.0


# --------------------------------------------------------------------------
# Shape helpers (all drawn with turtle commands)
# --------------------------------------------------------------------------
def _disc(t: SvgTurtle, cx: float, cy: float, r: float, fill: str, outline: str | None, w: float = 2) -> None:
    t.penup()
    t.goto(cx, cy - r)
    t.setheading(0)
    t.fillcolor(fill)
    if outline:
        t.pencolor(outline)
        t.pensize(w)
        t.pendown()
    t.begin_fill()
    t.circle(r)
    t.end_fill()
    t.penup()


def _ellipse(t, cx, cy, rx, ry, fill, outline=None, w=2, rot=0.0, n=26) -> None:
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    pts = []
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        px, py = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + px * c - py * s, cy + px * s + py * c))
    t.penup()
    t.goto(*pts[0])
    t.fillcolor(fill)
    if outline:
        t.pencolor(outline)
        t.pensize(w)
        t.pendown()
    t.begin_fill()
    for p in pts[1:]:
        t.goto(*p)
    t.end_fill()
    t.penup()


def _leaf(t, x, y, axis, length, fill, outline, vein) -> None:
    """Almond leaf with its tip `length` away along heading `axis`."""
    t.penup()
    t.goto(x, y)
    t.setheading(axis - 30)
    t.fillcolor(fill)
    t.pencolor(outline)
    t.pensize(2)
    t.pendown()
    t.begin_fill()
    t.circle(length, 60)
    t.left(120)
    t.circle(length, 60)
    t.end_fill()
    t.penup()
    t.goto(x, y)
    t.setheading(axis)
    t.pencolor(vein)
    t.pensize(1.6)
    t.pendown()
    t.forward(length * 0.82)
    t.penup()


def _star(t, cx, cy, r, color) -> None:
    pts = []
    for i in range(8):
        a = math.pi / 2 + i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.36
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    t.penup()
    t.goto(*pts[0])
    t.fillcolor(color)
    t.begin_fill()
    for p in pts[1:] + pts[:1]:
        t.goto(*p)
    t.end_fill()
    t.penup()


def _round_rect(t, x, y, w, h, r, fill, outline, lw=2) -> None:
    """Rounded rectangle with bottom-left corner (x, y), drawn with arcs."""
    t.penup()
    t.goto(x + r, y)
    t.setheading(0)
    t.fillcolor(fill)
    t.pencolor(outline)
    t.pensize(lw)
    t.pendown()
    t.begin_fill()
    for side in (w - 2 * r, h - 2 * r, w - 2 * r, h - 2 * r):
        t.forward(side)
        t.circle(r, 90)
    t.end_fill()
    t.penup()


def _stem(t, base, length, curve, color, width, steps=28):
    """Grow a curved stem upward; returns [(x, y, heading)] along it."""
    t.penup()
    t.goto(*base)
    t.setheading(90)
    t.pencolor(color)
    t.pensize(width)
    t.pendown()
    pts = [(t.x, t.y, t.heading)]
    for i in range(steps):
        t.left(curve * math.sin(i / steps * math.pi * 1.6) / 3)
        t.forward(length / steps)
        pts.append((t.x, t.y, t.heading))
    t.penup()
    return pts


def _at(pts, frac):
    i = min(int(frac * (len(pts) - 1)), len(pts) - 2)
    return pts[i]


def _data_label(text: str) -> str:
    return text.replace('"', "'")


# --------------------------------------------------------------------------
# 1. Growing plant (eco win)
# --------------------------------------------------------------------------
def plant_svg(leaves: int = 5, theme: str = "Ivory", animate: bool = True, t: float | None = None) -> str:
    c = palette(theme)
    leaves = max(1, min(int(leaves), 8))
    tt = SvgTurtle(300, 300)
    _ellipse(tt, 0, 16, 65, 7, c["ground"], None)
    with tt.group("pop", 0.0, 0.55, origin=(0, 14)):
        _round_rect(tt, -48, 20, 96, 67, 14, c["pot"], c["pot_dark"], 1.5)
        _round_rect(tt, -53, 78, 106, 14, 6, c["pot"], c["pot_dark"], 1.3)
        _ellipse(tt, 0, 92, 44, 5, c["soil"], None)
        _round_rect(tt, -28, 39, 6, 28, 3, c["leaf_light"], c["leaf_light"], .8)
    length = 40 + 13 * leaves
    sway_origin = (0, 92)
    with tt.group("sway", 0.9, 3.6, origin=sway_origin):
        with tt.group("draw", 0.5, 1.25, origin=sway_origin):
            stem = _stem(tt, (0, 92), length, 5, c["stem"], 4)
        for i in range(leaves):
            frac = 0.16 + 0.78 * i / max(leaves - 1, 1) if leaves > 1 else 0.5
            x, y, h = _at(stem, frac)
            side = -1 if i % 2 == 0 else 1
            axis = h + side * 52
            size = 42 - 2.7 * i
            with tt.group("pop", 0.5 + 1.25 * frac + 0.05, 0.5, origin=(x, y)):
                _leaf(tt, x, y, axis, size, c["leaf"], c["leaf_dark"], c["leaf_dark"])
        x, y, h = stem[-1]
        top_delay = 0.5 + 1.25 + 0.05
        if leaves >= 6:
            with tt.group("pop", top_delay, 0.6, origin=(x, y + 10)):
                for k in range(6):
                    a = k * 60 + 30
                    _disc(tt, x + 14 * math.cos(math.radians(a)), y + 10 + 14 * math.sin(math.radians(a)),
                          9, c["petal"], c["leaf_dark"], 1.6)
                _disc(tt, x, y + 10, 8, c["centre"], c["leaf_dark"], 1.6)
        else:
            for side in (-1, 1):
                with tt.group("pop", top_delay, 0.5, origin=(x, y)):
                    _leaf(tt, x, y, h + side * 38, 30, c["leaf_light"], c["leaf_dark"], c["leaf_dark"])
    for k, (sx, sy, r) in enumerate([(-82, 218, 7), (86, 252, 5), (72, 164, 4)]):
        with tt.group("twinkle", 2.2 + 0.5 * k, 2.2, origin=(sx, sy)):
            _star(tt, sx, sy, r, c["star"])
    return tt.render(_data_label(f"Turtle-drawn plant with {leaves} leaves"), animate, t)


# --------------------------------------------------------------------------
# 2. Footprint trail
# --------------------------------------------------------------------------
def _foot(t: SvgTurtle, cx, cy, ang, side, fill, outline=None):
    """One footprint at (cx, cy) rotated `ang` deg; side=-1 left foot, +1 right foot."""
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)

    def tr(px, py):
        px *= -side  # big toe on the inside
        return (cx + px * ca - py * sa, cy + px * sa + py * ca)

    def part(px, py, rx, ry, rot=0):
        gx, gy = tr(px, py)
        _ellipse(t, gx, gy, rx, ry, fill, outline, 1.4, rot + ang)

    part(0, 12, 13.5, 17)
    part(0, -4, 9, 10)
    part(0, -19, 10.5, 10)
    for px, py, r in [(-10.5, 33, 5.4), (-4.2, 37.5, 4.6), (2.4, 38.2, 4.1), (8.2, 35.6, 3.7), (12.5, 30.5, 3.2)]:
        gx, gy = tr(px, py)
        _disc(t, gx, gy, r, fill, outline, 1.2)


def footprint_svg(n_prints: int = 4, theme: str = "Ivory", animate: bool = True,
                  total: int = 8, t: float | None = None) -> str:
    """A compact horizontal stepping-stone trail drawn with turtle commands."""
    c = palette(theme)
    total = max(1, min(int(total), 12))
    n = max(0, min(int(n_prints), total))
    tt = SvgTurtle(360, 96)
    spacing = min(40.0, 312.0 / max(total - 1, 1))
    start = -spacing * (total - 1) / 2
    with tt.group("draw", 0, .85, origin=(start, 42)):
        tt.penup()
        tt.goto(start, 42)
        tt.pencolor(c["ghost"])
        tt.pensize(2)
        tt.pendown()
        tt.forward(spacing * (total - 1))
        tt.penup()
    for i in range(total):
        x, y = start + spacing * i, 42 + 3 * math.sin(i * .9)
        fill = c["foot"] if i < n else c["ghost"]
        with tt.group("pop", .1 + .12 * i, .42, origin=(x, y)):
            _ellipse(tt, x, y, 12, 9, fill, None)
            if i < n:
                _ellipse(tt, x - 2, y + 2.5, 4, 1.6, c["leaf_light"], None, rot=20)
                if i == n - 1:
                    with tt.group("twinkle", 1.2, 3.2, origin=(x, y + 21)):
                        _star(tt, x, y + 21, 4, c["star"])
    return tt.render(_data_label(f"Turtle-drawn footprint trail, {n} of {total} footprints"), animate, t)


# --------------------------------------------------------------------------
# 3. Eco Garden
# --------------------------------------------------------------------------
def _hill_y(x: float, which: str) -> float:
    return 52 + 11 * math.sin((x + 40) / 70) if which == "back" else 34 + 9 * math.sin((x - 30) / 55)


def _hill(t: SvgTurtle, which: str, fill: str) -> None:
    t.penup()
    t.goto(-180, 0)
    t.fillcolor(fill)
    t.begin_fill()
    for xi in range(-180, 181, 6):
        t.goto(xi, _hill_y(xi, which))
    t.goto(180, 0)
    t.end_fill()


def _sprout(t, bx, by, c):
    pts = _stem(t, (bx, by), 30, 20, c["stem"], 4, 14)
    x, y, h = pts[-1]
    _leaf(t, x, y, h + 42, 24, c["leaf"], c["leaf_dark"], c["leaf_dark"])
    _leaf(t, x, y, h - 42, 24, c["leaf_light"], c["leaf_dark"], c["leaf_dark"])


def _bush(t, bx, by, c):
    for cx, cy, r in [(-15, 14, 15), (15, 14, 15), (0, 22, 19)]:
        _disc(t, bx + cx, by + cy, r, c["leaf"], c["leaf_dark"], 2)
    _disc(t, bx - 4, by + 28, 5, c["leaf_light"], None)
    for cx, cy in [(-12, 14), (10, 22), (14, 10)]:
        _disc(t, bx + cx, by + cy, 3.2, c["petal"], c["leaf_dark"], 1)


def _flower(t, bx, by, c):
    pts = _stem(t, (bx, by), 58, 14, c["stem"], 4, 16)
    x, y, h = _at(pts, 0.45)
    _leaf(t, x, y, h - 45, 22, c["leaf"], c["leaf_dark"], c["leaf_dark"])
    x, y, h = pts[-1]
    for k in range(6):
        a = math.radians(k * 60 + 30)
        _disc(t, x + 9 * math.cos(a), y + 6 + 9 * math.sin(a), 6.5, c["petal"], c["leaf_dark"], 1.2)
    _disc(t, x, y + 6, 5.5, c["centre"], c["leaf_dark"], 1.2)


def _tree(t, bx, by, c, big=False):
    tw, th = (14, 60) if big else (10, 42)
    _round_rect(t, bx - tw / 2, by - 2, tw, th, 4, c["trunk"], c["pot_dark"], 1.8)
    base = by + th
    layout = ([(0, 26, 32), (-27, 8, 25), (27, 8, 25), (0, 50, 22)] if big
              else [(0, 20, 23), (-17, 6, 17), (17, 6, 17)])
    for cx, cy, r in layout:
        _disc(t, bx + cx, base + cy, r, c["leaf"], c["leaf_dark"], 2)
    hx, hy, hr = (bx - 8, base + (34 if big else 26), 7 if big else 5)
    _disc(t, hx, hy, hr, c["leaf_light"], None)
    if big:
        for cx, cy in [(-22, 4), (20, 12), (6, 38), (-6, 18)]:
            _disc(t, bx + cx, base + cy, 4.2, c["petal"], c["leaf_dark"], 1)


def garden_svg(level: int = 3, theme: str = "Ivory", animate: bool = True, t: float | None = None) -> str:
    c = palette(theme)
    level = max(0, min(int(level), 5))
    tt = SvgTurtle(360, 240)
    _hill(tt, "back", c["ground2"])
    _hill(tt, "front", c["ground"])
    slots = [-142, -82, -22, 38, 112]
    makers = [_sprout, _bush, _flower, _tree, lambda t_, x, y, cc: _tree(t_, x, y, cc, True)]
    if level == 0:  # the garden rests, it never withers
        for i, sx in enumerate(slots):
            by = _hill_y(sx, "front")
            _ellipse(tt, sx, by + 2, 15, 7, c["soil"], None)
            _disc(tt, sx, by + 6, 2.6, c["leaf_light"], None)
        for k, (sx, sy, r) in enumerate([(-120, 190, 9), (-40, 205, 7), (110, 196, 8), (60, 175, 6)]):
            with tt.group("twinkle", 0.3 * k, 2.6, origin=(sx, sy)):
                _star(tt, sx, sy, r, c["star"])
    else:
        with tt.group("spin", 0, 26, origin=(-140, 198)):
            tt.pencolor(c["sun"])
            tt.pensize(3)
            for k in range(8):
                a = math.radians(k * 45)
                tt.penup()
                tt.goto(-140 + 22 * math.cos(a), 198 + 22 * math.sin(a))
                tt.pendown()
                tt.goto(-140 + 30 * math.cos(a), 198 + 30 * math.sin(a))
            tt.penup()
        with tt.group("pulse", 0, 3.4, origin=(-140, 198)):
            _disc(tt, -140, 198, 16, c["sun"], None)
        if level >= 2:
            with tt.group("drift", 0, 7, origin=(100, 204)):
                for cx, cy, r in [(84, 202, 11), (100, 208, 15), (118, 202, 12), (134, 200, 9)]:
                    _disc(tt, cx, cy, r, c["cloud"], None)
        for i in range(level):
            sx = slots[i]
            by = _hill_y(sx, "front") - 2
            with (
                tt.group("sway", 0.6 + 0.3 * i, 3.2 + 0.4 * i, origin=(sx, by)),
                tt.group("grow", 0.25 + 0.4 * i, 0.9, origin=(sx, by)),
            ):
                makers[i](tt, sx, by, c)
        if level >= 3:
            with tt.group("flit", 0.5, 9, origin=(-40, 140)):
                with tt.group("flap", 0, 1, origin=(-40, 140)):
                    _ellipse(tt, -46, 143, 7, 5, c["petal"], c["leaf_dark"], 1, 30)
                    _ellipse(tt, -34, 143, 7, 5, c["petal"], c["leaf_dark"], 1, -30)
                tt.pencolor(c["leaf_dark"])
                tt.pensize(2.4)
                tt.penup()
                tt.goto(-40, 138)
                tt.pendown()
                tt.goto(-40, 148)
                tt.penup()
    return tt.render(_data_label(f"Turtle-drawn eco garden, level {level} of 5"), animate, t)
