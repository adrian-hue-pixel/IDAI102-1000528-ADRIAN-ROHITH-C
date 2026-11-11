"""Tilly, ShopImpact's renewed animated turtle companion.

The historic module/function name stays stable for existing imports. Artwork is
self-contained SVG: no remote assets, scripts, raster images or font dependency.
"""
from __future__ import annotations

PALETTES = {
    "Earth (default)": {
        "body_top": "#edf4de", "body_mid": "#b7d4ac", "body_edge": "#6e9a7e",
        "leaf_top": "#99c7a3", "leaf_edge": "#3e7960", "ink": "#1b3d31",
        "cheek": "#d89789", "aura": "#9bc5ac", "spark": "#8aa491",
        "ring": "#6f9a85", "shadow": "#355645", "hand": "#8bb79a",
    },
    "Dark": {
        "body_top": "#e6f3df", "body_mid": "#abd0b0", "body_edge": "#649784",
        "leaf_top": "#b1ddbb", "leaf_edge": "#529e81", "ink": "#193e32",
        "cheek": "#d99b94", "aura": "#6fa88e", "spark": "#9bc9b3",
        "ring": "#83b39d", "shadow": "#000000", "hand": "#83b79b",
    },
}
MOODS = ("happy", "proud", "curious", "encouraging", "sleepy")
THEME_ALIASES = {
    "Light": "Earth (default)", "Ivory": "Earth (default)",
    "Obsidian": "Dark", "High contrast": "Dark",
}
THEMES = (*PALETTES, *THEME_ALIASES)


def _eyes(mood: str, ink: str) -> str:
    if mood == "sleepy":
        return f'<path d="M116 112q6 5 12 0m24 0q6 5 12 0" fill="none" stroke="{ink}" stroke-width="3.5" stroke-linecap="round"/>'
    if mood == "proud":
        return f'<path d="M116 113q6-9 12 0m24 0q6-9 12 0" fill="none" stroke="{ink}" stroke-width="3.5" stroke-linecap="round"/>'
    left = f'<ellipse cx="122" cy="111" rx="4.4" ry="6" fill="{ink}"/><circle cx="123.5" cy="109" r="1.4" fill="#fff"/>'
    if mood == "encouraging":
        right = f'<path d="M152 112q6-7 12 0" fill="none" stroke="{ink}" stroke-width="3.5" stroke-linecap="round"/>'
    else:
        right = f'<ellipse cx="158" cy="111" rx="4.4" ry="6" fill="{ink}"/><circle cx="159.5" cy="109" r="1.4" fill="#fff"/>'
    return f'<g class="tilly-eyes">{left}{right}</g>'


def _mouth(mood: str, ink: str) -> str:
    if mood == "curious":
        return f'<ellipse cx="140" cy="131" rx="3.4" ry="4.3" fill="{ink}"/>'
    if mood == "sleepy":
        return f'<path d="M136 132h8" stroke="{ink}" stroke-width="2.8" stroke-linecap="round"/>'
    return f'<path d="M131 129q9 10 18 0" stroke="{ink}" stroke-width="3" stroke-linecap="round" fill="none"/>'


def _accessory(mood: str, color: str) -> str:
    if mood == "curious":
        return f'<g class="tilly-mote"><path d="M207 66a7 7 0 1111 6c-4 2-5 3-5 7" stroke="{color}" stroke-width="2.8" stroke-linecap="round" fill="none"/><circle cx="213" cy="86" r="1.8" fill="{color}"/></g>'
    if mood == "sleepy":
        return f'<path class="tilly-mote" d="M206 64h10l-10 11h10m8-27h12l-12 13h12" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
    if mood == "encouraging":
        return f'<path class="tilly-mote" d="M214 72c-10-13-21 1-12 9l12 11 12-11c9-8-2-22-12-9z" fill="{color}" opacity=".8"/>'
    return f'<path class="tilly-mote" d="m216 66 3 9 9 3-9 3-3 9-3-9-9-3 9-3z" fill="{color}"/>'


def mascot_svg(mood: str = "happy", theme: str = "Light", animate: bool = True) -> str:
    """Return turtle-based Tilly; static output has no animation styles."""
    mood = mood if mood in MOODS else "happy"
    c = PALETTES.get(THEME_ALIASES.get(theme, theme), PALETTES["Earth (default)"])
    css = ""
    if animate:
        css = """<style>
.tilly-body{animation:tilly-breathe 4.8s ease-in-out infinite;transform-origin:123px 143px}
.tilly-head{animation:tilly-look 6.4s ease-in-out infinite;transform-origin:184px 123px}
.tilly-eyes{animation:tilly-blink 5.2s infinite;transform-box:fill-box;transform-origin:center}
.tilly-foot{animation:tilly-step 5s ease-in-out infinite;transform-origin:center;transform-box:fill-box}
.tilly-foot.back{animation-delay:-2.5s}
.tilly-mote{animation:tilly-mote 4.2s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
.tilly-shell-glint{animation:tilly-glint 7s ease-in-out infinite}
@keyframes tilly-breathe{0%,100%{transform:scale(1,1)}50%{transform:scale(1.015,1.025)}}
@keyframes tilly-look{0%,65%,100%{transform:rotate(0)}35%,45%{transform:rotate(-5deg)}}
@keyframes tilly-blink{0%,90%,96%,100%{transform:scaleY(1)}93%{transform:scaleY(.06)}}
@keyframes tilly-step{0%,60%,100%{transform:translateY(0) rotate(0)}75%{transform:translateY(-3px) rotate(-6deg)}}
@keyframes tilly-mote{0%,100%{opacity:.3;transform:translateY(0)}50%{opacity:.7;transform:translateY(-4px)}}
@keyframes tilly-glint{0%,70%,100%{opacity:.16}80%{opacity:.36}}
@media(prefers-reduced-motion:reduce){*{animation:none!important}}
</style>"""
    tilt = ' transform="rotate(-5 210 113)"' if mood == "curious" else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 200" role="img" aria-label="Tilly the turtle looking {mood}">
{css}<defs>
<radialGradient id="tilly-aura"><stop stop-color="{c['aura']}" stop-opacity=".17"/><stop offset="1" stop-color="{c['aura']}" stop-opacity="0"/></radialGradient>
<radialGradient id="tilly-shell" cx="32%" cy="15%" r="90%"><stop stop-color="{c['leaf_top']}"/><stop offset=".6" stop-color="{c['leaf_edge']}"/><stop offset="1" stop-color="{c['ink']}"/></radialGradient>
<radialGradient id="tilly-skin" cx="30%" cy="20%" r="85%"><stop stop-color="{c['body_top']}"/><stop offset=".6" stop-color="{c['body_mid']}"/><stop offset="1" stop-color="{c['body_edge']}"/></radialGradient>
<linearGradient id="tilly-rim" x2="0" y2="1"><stop stop-color="{c['body_top']}"/><stop offset="1" stop-color="{c['body_edge']}"/></linearGradient>
</defs>
<ellipse cx="138" cy="112" rx="126" ry="86" fill="url(#tilly-aura)"/>
<ellipse cx="139" cy="172" rx="96" ry="8" fill="{c['shadow']}" opacity=".12"/>
<path d="m52 129-23 13 25 7" fill="{c['body_edge']}"/>
<g class="tilly-foot back"><rect x="66" y="136" width="24" height="31" rx="11" fill="url(#tilly-skin)"/><path d="M72 161v3m6-3v4m6-4v3" stroke="{c['body_edge']}" stroke-width="1.4" stroke-linecap="round"/></g>
<g class="tilly-foot"><rect x="155" y="138" width="25" height="30" rx="11" fill="url(#tilly-skin)"/><path d="M161 162v3m6-3v4m6-4v3" stroke="{c['body_edge']}" stroke-width="1.4" stroke-linecap="round"/></g>
<ellipse cx="124" cy="140" rx="77" ry="16" fill="{c['body_edge']}"/>
<g class="tilly-head"><path d="M174 116q19-15 30-8l6 24q-20 19-36 9z" fill="url(#tilly-skin)"/>
<g{tilt}><ellipse cx="214" cy="108" rx="31" ry="29" fill="url(#tilly-skin)"/>
<ellipse cx="205" cy="88" rx="10" ry="4" fill="#fff" opacity=".25" transform="rotate(-20 205 88)"/>
<ellipse cx="194" cy="115" rx="5" ry="3" fill="{c['cheek']}" opacity=".4"/><ellipse cx="233" cy="115" rx="5" ry="3" fill="{c['cheek']}" opacity=".4"/>
<g transform="translate(143 48) scale(.5)">{_eyes(mood, c['ink'])}{_mouth(mood, c['ink'])}</g>
<circle cx="236" cy="106" r="1.3" fill="{c['body_edge']}"/>
</g></g>
<g class="tilly-body"><path d="M49 137C45 78 76 49 120 49s77 32 74 88z" fill="url(#tilly-shell)" stroke="{c['leaf_edge']}" stroke-width="1.8"/>
<g fill="none" stroke="{c['ink']}" stroke-opacity=".25" stroke-width="1.7" stroke-linejoin="round">
<path d="m107 79 23-2 16 19-9 24-26 3-15-20z"/>
<path d="M107 79 92 56m38 21 15-22m1 41 35-13m-44 37 23 18m-49-15-12 17m-3-37-38 3"/>
</g>
<path class="tilly-shell-glint" d="M63 105c8-28 25-42 54-44" stroke="#fff" stroke-width="7" stroke-linecap="round" fill="none" opacity=".16"/>
<path d="M47 138q74 17 148 0" fill="none" stroke="url(#tilly-rim)" stroke-width="10" stroke-linecap="round"/>
<path d="M50 136q74 13 141 0" fill="none" stroke="{c['body_top']}" stroke-width="1.6" opacity=".65"/>
</g>
<g transform="translate(24 -22) scale(.95)">{_accessory(mood, c['spark'])}</g>
<path class="tilly-mote" d="M42 77v7m-3.5-3.5h7" stroke="{c['spark']}" stroke-width="1.5" stroke-linecap="round" opacity=".55"/>
</svg>'''
