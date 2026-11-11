from io import BytesIO

from PIL import Image

from summary_image import render_monthly_summary


def test_monthly_summary_download_is_a_valid_theme_aware_png():
    summary = {
        "co2_kg": 12.5,
        "spend_usd": 40.0,
        "n": 2,
        "by_category": {
            "Clothing": {"co2_kg": 10.0},
            "Books & Stationery": {"co2_kg": 2.5},
        },
    }

    for theme in ("Light", "Dark", "Ivory", "Obsidian", "High contrast"):
        image_bytes = render_monthly_summary(
            "October 2026",
            summary,
            10.0,
            ["First Step"],
            theme,
        )
        with Image.open(BytesIO(image_bytes)) as image:
            assert image.format == "PNG"
            assert image.size == (1200, 800)
