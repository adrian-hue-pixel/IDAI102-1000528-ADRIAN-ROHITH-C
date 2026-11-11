"""Theme palette contrast checks for text and chart marks."""

from styles import ACCENT_PALETTES, CHART_COLORS, DISPLAY_MODES, THEMES, normalize_mode


def _luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_theme_muted_text_meets_wcag_aa_and_chart_marks_are_distinguishable():
    for mode, theme in THEMES.items():
        assert _contrast_ratio(theme["muted"], theme["page"]) >= 4.5, mode
        colors = CHART_COLORS[mode]
        marks = [colors["line"], colors["spend"], colors["goal"], *colors["categories"]]
        assert min(_contrast_ratio(color, theme["page"]) for color in marks) >= 3.0


def test_seasonal_accent_palettes_meet_wcag_aa_in_every_display_mode():
    assert set(ACCENT_PALETTES) == {"Evergreen", "Spring canopy", "Autumn harvest"}
    for palette, colors in ACCENT_PALETTES.items():
        for mode, color in colors.items():
            assert _contrast_ratio(color, THEMES[mode]["page"]) >= 4.5, (
                palette,
                mode,
            )


def test_widget_text_meets_wcag_aa_in_every_theme():
    for mode, theme in THEMES.items():
        assert _contrast_ratio(theme["muted"], theme["surface"]) >= 4.5, (
            mode,
            "disabled button",
        )
        assert _contrast_ratio(theme["ink"], theme["page"]) >= 4.5, (
            mode,
            "selectbox value",
        )
        assert _contrast_ratio(theme["muted"], theme["page"]) >= 4.5, (
            mode,
            "selectbox placeholder",
        )
        assert _contrast_ratio(theme["ink"], theme["surface"]) >= 4.5, (
            mode,
            "dropdown options and popover button",
        )
        assert _contrast_ratio(theme["button_text"], theme["button"]) >= 4.5, (
            mode,
            "primary button",
        )


def test_impact_pills_have_wcag_aa_text_contrast():
    for background in ("#287452", "#765500", "#a64c3e"):
        assert _contrast_ratio("#ffffff", background) >= 4.5


def test_only_light_and_dark_are_public_display_modes():
    assert DISPLAY_MODES == ("Light", "Dark")
    assert set(THEMES) == set(DISPLAY_MODES)
    assert set(CHART_COLORS) == set(DISPLAY_MODES)


def test_previous_display_mode_preferences_migrate():
    assert normalize_mode("Ivory") == "Light"
    assert normalize_mode("Obsidian") == "Dark"
    assert normalize_mode("High contrast") == "Dark"
