"""Headless rendering checks for the Turtle scenes used in the Streamlit app."""

import io

from PIL import Image

import turtle_art


def test_turtle_scenes_render_valid_png_images():
    scenes = [
        turtle_art.leaf_scene(4),
        turtle_art.footprint_scene(3, "#2e7d32"),
        turtle_art.badge_scene("First Step", "sprout", "#2e7d32", "#c8e6c9"),
    ]
    for scene in scenes:
        image = Image.open(io.BytesIO(scene.to_png()))
        assert image.format == "PNG"
        assert image.width > 0 and image.height > 0


def test_turtle_leaf_animation_is_a_multiframe_gif():
    gif = turtle_art.leaf_scene(3).to_gif(frames=5)
    image = Image.open(io.BytesIO(gif))
    assert image.format == "GIF"
    assert image.n_frames == 5


def test_scene_background_can_match_display_theme():
    bg = "#111d17"
    scenes = [
        turtle_art.leaf_scene(3, bg=bg),
        turtle_art.footprint_scene(2, "#287452", bg=bg),
        turtle_art.badge_scene("First Step", "sprout", "#2e7d32", "#c8e6c9", bg=bg),
    ]
    for scene in scenes:
        image = Image.open(io.BytesIO(scene.to_png()))
        assert image.getpixel((0, 0)) == (17, 29, 23)


def test_garden_stages_grow_and_validate_level():
    images = [
        Image.open(io.BytesIO(turtle_art.garden_scene(level).to_png(scale=1)))
        for level in range(6)
    ]
    assert all(image.size == (320, 230) for image in images)
    assert len({image.tobytes() for image in images}) == 6
    for invalid_level in (-1, 6):
        try:
            turtle_art.garden_scene(invalid_level)
        except ValueError as error:
            assert "between 0 and 5" in str(error)
        else:
            raise AssertionError("Out-of-range garden levels must fail explicitly.")


def test_live_drawing_animation_stays_under_cloud_asset_budget():
    gif = turtle_art.leaf_scene(4).to_gif(frames=12, scale=0.8, step_ms=70, hold_ms=800)
    image = Image.open(io.BytesIO(gif))
    assert image.format == "GIF"
    assert image.n_frames == 12
    assert len(gif) < 400_000
