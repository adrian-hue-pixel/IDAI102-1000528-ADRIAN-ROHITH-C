"""Create downloadable monthly snapshot images without external services."""

from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw, ImageFont

import logic as lg

PALETTES = {
    "Ivory": {
        "page": "#f5f3ee",
        "surface": "#fffefa",
        "ink": "#1a2924",
        "muted": "#53625c",
        "accent": "#087653",
    },
    "Obsidian": {
        "page": "#07110f",
        "surface": "#0d1b18",
        "ink": "#edf5f1",
        "muted": "#aebfb7",
        "accent": "#53d9a7",
    },
    "High contrast": {
        "page": "#000000",
        "surface": "#000000",
        "ink": "#ffffff",
        "muted": "#ffff00",
        "accent": "#00ff00",
    },
}


def render_monthly_summary(
    month_label: str,
    summary: dict[str, Any],
    goal_kg: float,
    earned_badges: list[str],
    theme: str = "Ivory",
    goal_history: list[dict[str, Any]] | None = None,
    month: tuple[int, int] | None = None,
    swap_savings: dict[str, Any] | None = None,
) -> bytes:
    """Render a portable PNG card for the current monthly snapshot."""
    if goal_history is not None and month is not None:
        goal_kg = lg.goal_for_month(goal_history, month, goal_kg)
    theme = {"Light": "Ivory", "Dark": "Obsidian"}.get(theme, theme)
    colors = PALETTES[theme]
    image = Image.new("RGB", (1200, 800), colors["page"])
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.rounded_rectangle(
        (60, 55, 1140, 745),
        radius=30,
        fill=colors["surface"],
        outline=colors["accent"],
        width=3,
    )
    draw.text((100, 95), "ShopImpact monthly summary", fill=colors["ink"], font=font)
    draw.text((100, 140), month_label, fill=colors["muted"], font=font)
    draw.text(
        (100, 215),
        f"Estimated CO2e: {summary['co2_kg']:.1f} kg",
        fill=colors["ink"],
        font=font,
    )
    draw.text(
        (100, 260),
        f"Purchases: {summary['n']}    Spend (USD): ${summary['spend_usd']:.2f}",
        fill=colors["ink"],
        font=font,
    )

    if summary["co2_kg"] > goal_kg:
        goal_text = (
            f"{summary['co2_kg'] - goal_kg:.1f} kg above your {goal_kg:.1f} kg goal"
        )
    else:
        goal_text = (
            f"{goal_kg - summary['co2_kg']:.1f} kg within your {goal_kg:.1f} kg goal"
        )
    draw.text((100, 320), f"Goal status: {goal_text}", fill=colors["accent"], font=font)

    draw.text(
        (100, 395), "Top categories (estimated CO2e)", fill=colors["ink"], font=font
    )
    categories = sorted(
        summary["by_category"].items(),
        key=lambda item: item[1]["co2_kg"],
        reverse=True,
    )[:3]
    for index, (category, values) in enumerate(categories):
        draw.text(
            (125, 435 + index * 35),
            f"- {category}: {values['co2_kg']:.1f} kg",
            fill=colors["muted"],
            font=font,
        )
    draw.text(
        (100, 570),
        "Badges earned: " + (", ".join(earned_badges) or "None this month"),
        fill=colors["ink"],
        font=font,
    )
    if swap_savings and swap_savings["saved_kg"] > 0:
        draw.text(
            (100, 630),
            f"Swaps: {swap_savings['saved_kg']:.1f} kg CO2e lower by illustrative estimate "
            f"({swap_savings['saved_equivalents']['car_km']:.1f} car-km equivalent); "
            "not a verified saving.",
            fill=colors["muted"],
            font=font,
        )
    draw.text(
        (100, 680),
        "Illustrative estimates only; not measured product data.",
        fill=colors["muted"],
        font=font,
    )

    result = BytesIO()
    image.save(result, format="PNG")
    return result.getvalue()
