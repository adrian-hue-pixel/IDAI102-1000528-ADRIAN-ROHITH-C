"""Streamlit interaction checks for purchase validation and session-state behavior."""

import base64
import datetime as dt
import json
import os
import re
import xml.etree.ElementTree as ET

import pytest
from streamlit.testing.v1 import AppTest

import browser_storage as bs
import gamification as gm
import logic as lg
import plan_tools as pt
import purchase_series as ps
from browser_persistence import encode_saved_state
from data_io import export_purchases
from ui import common

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")


def make_app_test(
    purchases=None,
    storage_available=False,
    saved_signature=None,
    page="views/home.py",
    display_mode="Dark",
):
    """Run without browser storage; AppTest has no embedded browser component."""
    app = AppTest.from_file(APP_PATH)
    app.session_state["guest_access"] = True
    app.session_state["browser_storage_loaded"] = True
    app.session_state["storage_available"] = storage_available
    app.session_state["storage_error"] = (
        None if storage_available else "Browser storage is unavailable in AppTest."
    )
    app.session_state["browser_storage_signature"] = saved_signature
    app.session_state["display_mode"] = display_mode
    if purchases is not None:
        app.session_state["purchases"] = purchases
        app.session_state["next_id"] = max((p["id"] for p in purchases), default=0) + 1
    app.run()
    if page != "views/home.py":
        app.switch_page(page).run()
    return app


PAGE_PATHS = (
    "views/home.py",
    "views/dashboard.py",
    "views/purchases.py",
    "views/swaps_plan.py",
    "views/impact_lab.py",
    "views/garden_badges.py",
    "views/month_review.py",
    "views/settings_about.py",
)


@pytest.mark.parametrize("page", PAGE_PATHS)
@pytest.mark.parametrize("display_mode", ("Light", "Dark"))
def test_every_page_renders_in_every_display_mode(page, display_mode):
    app = make_app_test(page=page, display_mode=display_mode)

    assert not app.exception


def test_month_review_visit_is_recorded_as_iso_date(monkeypatch):
    viewer_today = dt.date(2026, 11, 2)
    monkeypatch.setattr(common, "app_today", lambda: viewer_today)
    app = make_app_test(page="views/month_review.py")

    assert app.session_state["month_review_last_visit"] == "2026-11-02"
    assert app.session_state["settings"]["month_review_last_visit"] == "2026-11-02"
    assert not app.exception
    assert app.session_state["display_mode"] == "Dark"


@pytest.mark.parametrize("page", PAGE_PATHS)
def test_empty_journal_has_friendly_next_action_on_every_page(page):
    app = make_app_test(page=page, storage_available=True)

    assert any("journal is empty" in item.value for item in app.info)
    assert any(
        element.proto.label == "Add your first purchase"
        for element in app.get("page_link")
    )
    assert not app.exception


@pytest.mark.parametrize("page", PAGE_PATHS)
def test_single_purchase_has_friendly_next_action_on_every_page(page):
    purchase = lg.make_purchase(
        1, common.app_today(), "Clothing", "Local shop", 24
    )
    app = make_app_test([purchase], page=page, storage_available=True)

    assert any("one purchase so far" in item.value for item in app.info)
    assert any(
        element.proto.label == "Log another purchase"
        for element in app.get("page_link")
    )
    assert not app.exception


@pytest.mark.parametrize("page", PAGE_PATHS)
def test_storage_unavailable_has_friendly_next_action_on_every_page(page):
    app = make_app_test(page=page, storage_available=False)

    assert any("Browser saving is unavailable" in item.value for item in app.info)
    assert any(
        element.proto.label == "Review data settings"
        for element in app.get("page_link")
    )
    assert not app.exception


def test_pending_saved_state_has_retry_action():
    app = make_app_test(storage_available=True)
    app.session_state["storage_pending"] = True
    app.run()

    assert any("saved journal is still loading" in item.value for item in app.info)
    assert any(button.label == "Retry loading saved data" for button in app.button)
    assert not app.exception


def test_dashboard_single_month_explains_missing_trend_and_offers_next_action(monkeypatch):
    monkeypatch.setattr(common, "app_today", lambda: dt.date(2026, 10, 15))
    purchases = [
        lg.make_purchase(1, dt.date(2026, 10, 1), "Clothing", "Shop", 24),
        lg.make_purchase(2, dt.date(2026, 10, 2), "Books & Stationery", "Bookshop", 12),
    ]
    app = make_app_test(purchases, page="views/dashboard.py", storage_available=True)

    assert any("one month" in item.value for item in app.info)
    assert any(
        element.proto.label == "Log a purchase in another month"
        for element in app.get("page_link")
    )
    assert any(
        "one month and a simple pace projection" in item.value
        for item in app.caption
    )
    assert not app.exception


def test_invalid_csv_has_friendly_recovery_action_and_preserves_journal():
    purchase = lg.make_purchase(
        1, dt.date(2026, 10, 1), "Clothing", "Local shop", 24
    )
    app = make_app_test(
        [purchase], page="views/purchases.py", storage_available=True
    )
    app.file_uploader[0].set_value(
        ("invalid.csv", b"\xff\xfe", "text/csv")
    ).run()
    next(button for button in app.button if button.label == "Preview restore").click().run()

    assert app.session_state["purchases"] == [purchase]
    assert any("could not be restored" in item.value for item in app.info)
    assert any(button.label == "Choose a different CSV" for button in app.button)
    assert not app.exception


def test_dashboard_chart_table_toggle_exposes_monthly_values():
    purchases = [
        lg.make_purchase(1, dt.date(2026, 9, 1), "Clothing", "Shop", 24),
        lg.make_purchase(2, dt.date(2026, 10, 1), "Clothing", "Shop", 30),
    ]
    app = make_app_test(purchases, page="views/dashboard.py", storage_available=True)
    toggle = next(
        widget for widget in app.checkbox if widget.label == "View as table"
    )
    toggle.set_value(True).run()

    assert len(app.dataframe) >= 1
    assert not app.exception


def test_month_and_currency_state_survive_page_navigation():
    app = make_app_test()
    month = app.session_state["view_month"]
    next(
        widget for widget in app.selectbox if widget.key == "topbar_currency_name"
    ).select("Indian Rupee (₹)").run()

    assert app.session_state["currency_name"] == "Indian Rupee (₹)"
    assert app.session_state["view_month"] == month
    app.switch_page("views/dashboard.py").run()

    assert app.session_state["currency_name"] == "Indian Rupee (₹)"
    assert app.session_state["view_month"] == month
    assert not app.exception


def test_current_viewer_day_sets_default_month_and_date_picker_max(monkeypatch):
    viewer_today = dt.date(2027, 1, 1)
    monkeypatch.setattr(common, "app_today", lambda: viewer_today)
    app = make_app_test()

    assert app.session_state["view_month"] == (2027, 1)
    date_widget = next(widget for widget in app.date_input if widget.label == "Purchase date")
    assert date_widget.value == viewer_today
    assert date_widget.proto.max == "2027-01-01"
    assert date_widget.proto.min == "2000-01-01"
    next(widget for widget in app.radio if widget.key == "entry_mode").set_value(
        "Plan a purchase"
    ).run()
    date_widget = next(widget for widget in app.date_input if widget.label == "Purchase date")
    assert date_widget.proto.max == "2029-01-01"
    assert not app.exception


def test_new_session_default_month_advances_after_midnight_rollover(monkeypatch):
    monkeypatch.setattr(common, "app_today", lambda: dt.date(2026, 12, 31))
    december = make_app_test()
    assert december.session_state["view_month"] == (2026, 12)

    monkeypatch.setattr(common, "app_today", lambda: dt.date(2027, 1, 1))
    january = make_app_test()
    assert january.session_state["view_month"] == (2027, 1)


def test_weekly_challenge_window_uses_current_viewer_day(monkeypatch):
    viewer_today = dt.date(2026, 11, 2)
    purchase = lg.make_purchase(
        1, dt.date(2026, 10, 28), "Clothing", "Local shop", 24, "Second-hand"
    )
    purchase["date"] = viewer_today
    monkeypatch.setattr(common, "app_today", lambda: viewer_today)
    original_weekly_challenges = gm.weekly_challenges
    evaluated = []

    def track_weekly_window(purchases, today, month_review_last_visit=None):
        challenges = original_weekly_challenges(
            purchases, today, month_review_last_visit
        )
        evaluated.append((today, challenges))
        return challenges

    monkeypatch.setattr(gm, "weekly_challenges", track_weekly_window)
    app = make_app_test([purchase])
    app.switch_page("views/garden_badges.py").run()

    assert evaluated
    assert evaluated[-1][0] == viewer_today
    assert evaluated[-1][1][0]["title"] == "Review your month's impact this week"
    assert evaluated[-1][1][0]["progress"] == 0
    assert not app.exception


def test_quick_add_can_be_saved_managed_and_applied():
    app = make_app_test()
    next(
        widget for widget in app.radio if widget.label == "Product type"
    ).set_value("Books & Stationery").run()
    next(
        widget
        for widget in app.selectbox
        if widget.key == "brand_Books & Stationery"
    ).select("Local library").run()
    app.number_input[0].set_value(32.0).run()
    app.text_input[0].set_value("Do not save this note").run()
    next(widget for widget in app.selectbox if widget.key == "entry_intent").select(
        "Want"
    ).run()
    next(button for button in app.button if button.label == "Save as quick add").click().run()

    assert len(app.session_state["favorites"]) == 1
    assert app.session_state["favorites"][0]["intent"] == "Want"
    assert "note" not in app.session_state["favorites"][0]
    app.switch_page("views/purchases.py").run()
    assert any("Local library" in item.value for item in app.markdown if hasattr(item, "value"))
    app.switch_page("views/home.py").run()
    next(
        widget for widget in app.selectbox if widget.key == "quick_add_selection"
    ).select(0).run()
    next(button for button in app.button if button.label == "Use quick add").click().run()

    assert app.session_state["entry_product_type"] == "Books & Stationery"
    assert app.session_state["price"] == 32.0
    assert app.session_state["entry_intent"] == "Want"
    assert app.session_state["entry_note"] == ""
    assert not app.exception


def test_empty_state_and_missing_brand_prevent_logging():
    app = make_app_test()

    assert not app.exception
    assert app.session_state["purchases"] == []
    add_button = next(
        button for button in app.button if button.label == "Log this purchase"
    )
    assert add_button.disabled
    assert any(button.label == "Try with demo data" for button in app.button)
    assert any(button.label == "Dismiss tour" for button in app.button)


def test_onboarding_guide_dismissal_is_remembered_in_session():
    app = make_app_test()

    next(
        button for button in app.button if button.label == "Dismiss tour"
    ).click().run()

    assert app.session_state["guide_dismissed"] is True
    assert not app.exception


def test_settings_can_reopen_the_guide():
    app = make_app_test(page="views/settings_about.py")

    next(
        button for button in app.button
        if button.label == "Replay the Home → Dashboard tour"
    ).click().run()

    assert app.session_state["guide_dismissed"] is False
    assert any(button.label == "Dismiss tour" for button in app.button)
    assert not app.exception


def test_home_keeps_purchase_entry_with_month_snapshot_and_companion():
    app = make_app_test()
    assert any(widget.label == "Product type" for widget in app.radio)
    assert any(widget.label == "Entry type" for widget in app.radio)
    assert any(button.label == "Show another tip" for button in app.button)
    assert any("This month" in item.value for item in app.markdown if hasattr(item, "value"))
    assert not app.exception


def test_purchase_is_added_once_and_survives_widget_reruns():
    app = make_app_test()
    category = next(
        widget for widget in app.radio if widget.label == "Product type"
    )
    category.set_value("Smartphone").run()

    brand = next(
        widget
        for widget in app.selectbox
        if widget.label == "Brand or shop" and widget.key == "brand_Smartphone"
    )
    brand.select("Fairphone").run()
    app.number_input[0].set_value(100.0).run()
    app.text_input[0].set_value("Original note").run()
    next(widget for widget in app.selectbox if widget.key == "entry_intent").select(
        "Gift"
    ).run()

    add_button = next(
        button for button in app.button if button.label == "Log this purchase"
    )
    assert not add_button.disabled
    add_button.click().run()

    purchases = app.session_state["purchases"]
    assert len(purchases) == 1
    assert purchases[0]["product_type"] == "Smartphone"
    assert purchases[0]["price_usd"] == 100.0
    assert app.session_state["achievement_inbox"][0]["name"] == "First Step"
    assert any(
        "Undo: Logged 1 Smartphone purchase." in toast.value
        for toast in app.toast
    )
    app.run()
    assert any(
        button.label == "Undo: Logged 1 Smartphone purchase."
        for button in app.button
    )
    assert not app.exception

    app.number_input[0].set_value(150.0).run()
    assert len(app.session_state["purchases"]) == 1
    assert app.session_state["last_event"]["co2"] == purchases[0]["co2_kg"]
    assert app.session_state["undo_stack"][-1]["description"] == (
        "Logged 1 Smartphone purchase."
    )
    next(
        button for button in app.button
        if button.label == "Undo: Logged 1 Smartphone purchase."
    ).click().run()
    assert app.session_state["purchases"] == []
    assert app.session_state["achievement_inbox"] == []
    assert not app.exception


def test_logging_past_month_selects_that_month_in_the_dashboard():
    app = make_app_test()
    next(widget for widget in app.radio if widget.label == "Product type").set_value(
        "Books & Stationery"
    ).run()
    next(
        widget
        for widget in app.selectbox
        if widget.label == "Brand or shop" and widget.key == "brand_Books & Stationery"
    ).select("Local library").run()
    app.date_input[0].set_value(dt.date(2026, 5, 12)).run()
    app.number_input[0].set_value(20.0).run()

    next(
        button for button in app.button if button.label == "Log this purchase"
    ).click().run()

    assert app.session_state["view_month"] == (2026, 5)
    assert not app.exception


def test_display_modes_switch_without_app_exceptions():
    app = make_app_test()
    display_mode = next(
        widget for widget in app.radio if widget.label == "Display mode"
    )

    for mode in ("Dark", "Light"):
        display_mode.set_value(mode).run()
        assert not app.exception


def test_two_modes_and_reduce_motion_settings_are_remembered():
    app = make_app_test()
    modes = next(widget for widget in app.radio if widget.key == "topbar_display_mode")
    assert modes.options == ["Light", "Dark"]
    assert not any(widget.label == "Accent palette" for widget in app.selectbox)
    next(widget for widget in app.checkbox if widget.key == "topbar_reduce_motion").check().run()
    assert app.session_state["reduce_motion"] is True
    assert not app.exception


def test_companion_svg_uses_the_reduce_motion_setting():
    app = make_app_test()

    def rendered_svg():
        markdown = next(
            element.value
            for element in app.markdown
            if 'class="tilly-image svg-motion-animated"' in element.value
        )
        match = re.search(r'data:image/svg\+xml;base64,([^"]+)', markdown)
        assert match is not None
        return ET.fromstring(base64.b64decode(match.group(1)))

    animated_svg = rendered_svg()
    assert animated_svg.find("{http://www.w3.org/2000/svg}style") is not None

    app.session_state["reduce_motion"] = True
    app.run()

    static_svg = rendered_svg()
    assert static_svg.find("{http://www.w3.org/2000/svg}style") is None
    assert app.session_state["reduce_motion"] is True
    assert not app.exception


def test_turtle_svg_displays_are_static_for_reduce_motion_and_stable_on_rerun():
    app = make_app_test(
        purchases=lg.demo_purchases(), page="views/garden_badges.py"
    )

    def rendered_art():
        artwork = {}
        for element in app.markdown:
            if 'class="svg-turtle-image svg-motion-animated"' not in element.value:
                continue
            match = re.search(r'data:image/svg\+xml;base64,([^"]+)', element.value)
            assert match is not None
            svg = base64.b64decode(match.group(1)).decode("utf-8")
            root = ET.fromstring(svg)
            label = root.get("aria-label")
            if "plant with" in label:
                key = "plant"
            elif "footprint trail" in label:
                key = "footprints"
            elif "eco garden" in label:
                key = "garden"
            else:
                continue
            artwork[key] = svg
        return artwork

    animated = rendered_art()
    assert set(animated) == {"plant", "footprints", "garden"}
    assert all("<style>" in svg for svg in animated.values())

    app.session_state["reduce_motion"] = True
    app.run()
    static = rendered_art()
    assert all("<style>" not in svg for svg in static.values())

    app.run()
    assert rendered_art() == static
    assert not app.exception


def test_eco_win_svg_changes_only_for_a_new_low_impact_purchase():
    app = make_app_test()

    def log_purchase(price):
        next(widget for widget in app.radio if widget.label == "Product type").set_value(
            "Books & Stationery"
        ).run()
        next(
            widget
            for widget in app.selectbox
            if widget.label == "Brand or shop" and widget.key == "brand_Books & Stationery"
        ).select("Local library").run()
        app.number_input[0].set_value(price).run()
        next(
            button for button in app.button if button.label == "Log this purchase"
        ).click().run()

    def event_plant():
        for element in app.markdown:
            if 'class="svg-turtle-image svg-motion-animated"' not in element.value:
                continue
            match = re.search(r'data:image/svg\+xml;base64,([^"]+)', element.value)
            assert match is not None
            svg = base64.b64decode(match.group(1)).decode("utf-8")
            if "purchase:" in svg:
                return svg
        raise AssertionError("The low-impact purchase SVG must include its purchase id.")

    log_purchase(1)
    first_svg = event_plant()
    assert "purchase:1" in first_svg

    app.run()
    assert event_plant() == first_svg

    log_purchase(2)
    second_svg = event_plant()
    assert "purchase:2" in second_svg
    assert second_svg != first_svg
    assert not app.exception


def test_settings_page_exposes_preferences_and_data_management():
    app = make_app_test(page="views/settings_about.py")

    assert any(item.label == "Appearance & preferences" for item in app.expander)
    assert any(widget.key == "settings_display_mode" for widget in app.radio)
    assert any(widget.key == "settings_currency" for widget in app.selectbox)
    assert any(widget.key == "settings_goal" for widget in app.slider)
    assert any(widget.key == "settings_reduce_motion" for widget in app.checkbox)
    assert any(button.label == "Load labelled synthetic demo data" for button in app.button)
    assert any(button.label == "Clear all purchases in this session" for button in app.button)
    assert any(button.label == "Replay the Home → Dashboard tour" for button in app.button)


def test_goal_presets_set_the_custom_slider_value():
    app = make_app_test(page="views/settings_about.py")

    next(
        button for button in app.button if button.label == "Ambitious · 40 kg"
    ).click().run()

    assert app.session_state["goal_kg"] == 40
    assert app.session_state["goal_history"][-1]["goal_kg"] == 40
    assert not app.exception


def test_goal_change_updates_current_month_history_and_can_be_undone():
    app = make_app_test(page="views/settings_about.py")
    old_history = app.session_state["goal_history"].copy()

    next(widget for widget in app.slider if widget.key == "settings_goal").set_value(
        60
    ).run()

    assert app.session_state["goal_kg"] == 60
    assert app.session_state["goal_history"] == [
        {
            "from_month": common.lg.month_of(common.app_today()),
            "goal_kg": 60,
        }
    ]
    next(
        button for button in app.button if button.label == "Undo: Changed monthly goal."
    ).click().run()

    assert app.session_state["goal_kg"] == 80
    assert app.session_state["goal_history"] == old_history
    assert not app.exception


def test_topbar_goal_change_updates_history_and_can_be_undone():
    app = make_app_test()
    old_history = app.session_state["goal_history"].copy()

    next(widget for widget in app.slider if widget.key == "topbar_goal_kg").set_value(
        60
    ).run()

    assert app.session_state["goal_kg"] == 60
    assert app.session_state["goal_history"][-1]["goal_kg"] == 60
    next(
        button for button in app.button if button.label == "Undo: Changed monthly goal."
    ).click().run()

    assert app.session_state["goal_kg"] == 80
    assert app.session_state["goal_history"] == old_history
    assert not app.exception


def test_goal_suggestion_presets_appear_with_two_logged_months():
    purchases = [
        lg.make_purchase(
            index,
            dt.date(2026, month, 5),
            "Clothing",
            "Local shop",
            100,
        )
        for index, month in enumerate((8, 9), start=1)
    ]
    app = make_app_test(
        purchases, page="views/settings_about.py", storage_available=True
    )

    assert {button.label for button in app.button} >= {
        "Same as my average",
        "10% lower",
        "20% lower",
    }
    assert any("average of your last 2 logged months" in item.value for item in app.caption)
    next(button for button in app.button if button.label == "10% lower").click().run()
    assert app.session_state["goal_kg"] == lg.suggested_goal_presets(purchases)[1][
        "10% lower"
    ]
    assert not app.exception


def test_compare_options_uses_estimator_without_exceptions():
    app = make_app_test(page="views/swaps_plan.py")

    assert any(metric.label == "Option A estimate" for metric in app.metric)
    assert any(metric.label == "Option B estimate" for metric in app.metric)
    assert not app.exception


def test_daily_tip_show_another_changes_the_tip():
    app = make_app_test()
    original = app.session_state["tip"]

    next(
        button for button in app.button if button.label == "Show another tip"
    ).click().run()

    assert app.session_state["tip"] != original
    assert not app.exception


def test_low_impact_purchase_has_one_toast_and_no_balloons():
    app = make_app_test()
    category = next(
        widget for widget in app.radio if widget.label == "Product type"
    )
    category.set_value("Books & Stationery").run()
    brand = next(
        widget
        for widget in app.selectbox
        if widget.label == "Brand or shop" and widget.key == "brand_Books & Stationery"
    )
    brand.select("Local library").run()
    app.number_input[0].set_value(1.0).run()
    next(
        button for button in app.button if button.label == "Log this purchase"
    ).click().run()

    assert len(app.toast) == 1
    assert len(app.get("balloons")) == 0
    assert app.session_state["last_event"]["eco"] is True
    assert any(
        "A small eco win" in element.value
        for element in app.markdown
        if hasattr(element, "value")
    )
    assert any(
        "Badge unlocked: First Step" in element.value
        for element in app.success
        if hasattr(element, "value")
    )
    next(
        button for button in app.button if button.label == "Dismiss celebration"
    ).click().run()
    assert app.session_state["last_event"] is None
    assert not app.exception


def test_low_impact_feedback_honors_in_app_reduce_motion_setting():
    app = make_app_test()
    next(widget for widget in app.checkbox if widget.key == "topbar_reduce_motion").set_value(
        True
    ).run()
    next(widget for widget in app.radio if widget.label == "Product type").set_value(
        "Books & Stationery"
    ).run()
    next(
        widget
        for widget in app.selectbox
        if widget.label == "Brand or shop" and widget.key == "brand_Books & Stationery"
    ).select("Local library").run()
    app.number_input[0].set_value(1.0).run()
    next(
        button for button in app.button if button.label == "Log this purchase"
    ).click().run()

    assert app.session_state["reduce_motion"] is True
    assert app.session_state["last_event"]["eco"] is True
    assert not app.exception


def test_gentle_progress_and_weekly_challenges_can_be_dismissed_and_restored():
    app = make_app_test(page="views/garden_badges.py")
    next(
        button for button in app.button if button.label == "Hide weekly challenges"
    ).click().run()
    assert app.session_state["weekly_challenges_dismissed"] is True
    next(
        button for button in app.button if button.label == "Show weekly challenges"
    ).click().run()
    assert app.session_state["weekly_challenges_dismissed"] is False

    app.session_state["purchases"] = lg.demo_purchases()
    app.run()
    assert any(metric.label.startswith("Level ") for metric in app.metric)
    assert {metric.label for metric in app.metric} >= {
        "Current streak",
        "Best streak",
    }
    assert any(
        "Optional weekly challenges" in item.value
        for item in app.markdown
        if hasattr(item, "value")
    )
    assert any(item.label == "How XP works" for item in app.expander)
    assert any(
        "XP now rewards low-impact choices and swaps" in item.value
        for item in app.info
    )
    assert not app.exception


def test_currency_change_resets_price_to_currency_default():
    app = make_app_test()
    currency = next(widget for widget in app.selectbox if widget.label == "Currency")
    currency.select("Indian Rupee (₹)").run()

    assert app.number_input[0].value == 2200.0
    assert app.number_input[0].label == "Price (₹)"
    assert not app.exception


def test_demo_data_can_be_loaded_and_cleared():
    app = make_app_test()

    next(
        button for button in app.button if button.label == "Try with demo data"
    ).click().run()
    assert len(app.session_state["purchases"]) == 15
    assert not app.exception

    app.switch_page("views/settings_about.py").run()
    next(
        button for button in app.button
        if button.label == "Clear all purchases in this session"
    ).click().run()
    next(button for button in app.button if button.label == "Confirm clear").click().run()
    assert app.session_state["purchases"] == []
    assert not app.exception


def test_month_navigation_changes_the_selected_month():
    app = make_app_test()
    next(
        button for button in app.button if button.label == "Try with demo data"
    ).click().run()
    current_month = app.session_state["view_month"]

    previous_month = lg.previous_month(current_month)
    month_select = next(
        widget for widget in app.selectbox if widget.key == "topbar_month_selector"
    )
    previous_label = dt.date(*previous_month, 1).strftime("%b %Y")
    assert previous_label in month_select.options
    month_select.select(previous_label).run()

    assert app.session_state["view_month"] == previous_month
    assert not app.exception


def test_purchase_delete_can_be_undone():
    app = make_app_test()
    next(
        button for button in app.button if button.label == "Try with demo data"
    ).click().run()
    app.switch_page("views/purchases.py").run()
    original_count = len(app.session_state["purchases"])

    table = app.dataframe[0]
    app.session_state[table.key] = {
        "selection": {"rows": [0], "columns": [], "cells": []}
    }
    app.run()
    next(
        button for button in app.button if button.label == "Delete selected"
    ).click().run()
    assert len(app.session_state["purchases"]) == original_count - 1
    assert app.session_state["undo_stack"][-1]["description"] == "Deleted 1 purchase."

    next(
        button for button in app.button
        if button.label == "Undo: Deleted 1 purchase."
    ).click().run()
    assert len(app.session_state["purchases"]) == original_count
    assert app.session_state["undo_stack"][-1]["description"] == "Loaded synthetic demo data."
    assert not app.exception


def test_csv_export_import_round_trip_in_purchase_view():
    app = make_app_test()
    next(
        button for button in app.button if button.label == "Try with demo data"
    ).click().run()
    app.switch_page("views/purchases.py").run()
    original = app.session_state["purchases"]
    csv_text = export_purchases(original)
    expected = [
        (
            purchase["date"],
            purchase["product_type"],
            purchase["brand"],
            purchase["condition"],
            purchase["low_packaging"],
            purchase["price_usd"],
            purchase["co2_kg"],
        )
        for purchase in original
    ]

    app.file_uploader[0].set_value(
        ("shopimpact.csv", csv_text.encode("utf-8"), "text/csv")
    ).run()
    next(
        button for button in app.button if button.label == "Preview restore"
    ).click().run()
    next(
        widget for widget in app.checkbox
        if widget.label.startswith("I understand Replace")
    ).set_value(True).run()
    next(button for button in app.button if button.label == "Confirm Replace").click().run()

    restored = app.session_state["purchases"]
    actual = [
        (
            purchase["date"],
            purchase["product_type"],
            purchase["brand"],
            purchase["condition"],
            purchase["low_packaging"],
            purchase["price_usd"],
            purchase["co2_kg"],
        )
        for purchase in restored
    ]
    assert actual == expected
    assert {button.label for button in app.download_button} == {
        "Download all purchases as CSV",
    }
    assert not app.exception


def _upload_and_preview(app, csv_text, filename="restore.csv"):
    app.file_uploader[0].set_value(
        (filename, csv_text.encode("utf-8"), "text/csv")
    ).run()
    next(
        button for button in app.button if button.label == "Preview restore"
    ).click().run()


def _session_backup(state):
    settings = {
        "text_size": state["text_size"],
        "dyslexia_font": bool(state["dyslexia_font"]),
        "sound_enabled": bool(state["sound_enabled"]),
        "display_mode": state["display_mode"],
        "accent_palette": state["accent_palette"],
        "currency_name": state["currency_name"],
        "goal_kg": int(state["goal_kg"]),
        "goal_history": state["goal_history"],
        "uncertainty_band": int(state["uncertainty_band"]),
        "month_review_last_visit": state["month_review_last_visit"],
        "xp_scoring_notice_dismissed": state["xp_scoring_notice_dismissed"],
        "reduce_motion": bool(state["reduce_motion"]),
        "view_month": state["view_month"],
    }
    return encode_saved_state(
        state["purchases"],
        state["guide_dismissed"],
        state["achievement_inbox"],
        state["plans"],
        settings,
    )


def test_full_backup_download_restore_round_trip_and_undo():
    purchase = lg.make_purchase(
        1,
        dt.date(2026, 10, 20),
        "Clothing",
        "Local shop",
        24,
        "Second-hand",
        note='="Gift, packed carefully"',
        intent="Gift",
    )
    purchase.update({"recurring": False, "recurring_group": None, "source": "user"})
    plan = pt.create_plan(
        "backup-plan",
        "Books & Stationery",
        "Local library",
        12,
        "Second-hand",
        True,
        dt.date(2026, 10, 25),
    )
    achievements = [
        {"name": "First Step", "month": "Oct 2026", "reason": "Logged a purchase."}
    ]
    app = make_app_test(
        [purchase], page="views/settings_about.py", storage_available=True
    )
    restored_settings = {
        "text_size": "L",
        "dyslexia_font": True,
        "sound_enabled": False,
        "display_mode": "Light",
        "accent_palette": "Evergreen",
        "currency_name": "US Dollar ($)",
        "goal_kg": 60,
        "goal_history": [
            {"from_month": (2026, 1), "goal_kg": 80},
            {"from_month": common.lg.month_of(common.app_today()), "goal_kg": 60},
        ],
        "uncertainty_band": 40,
        "month_review_last_visit": None,
        "xp_scoring_notice_dismissed": False,
        "reduce_motion": True,
        "view_month": (2026, 10),
    }
    app.session_state["plans"] = [plan]
    app.session_state["achievement_inbox"] = achievements
    app.session_state["settings"] = dict(restored_settings)
    for key, value in restored_settings.items():
        app.session_state[key] = value
    app.run()

    backup = _session_backup(app.session_state)
    download = next(
        button
        for button in app.download_button
        if button.label == "Download full backup (JSON)"
    )
    assert download.proto.url.endswith(".json")

    previous_purchase = lg.make_purchase(
        1, dt.date(2026, 10, 10), "Smartphone", "Old shop", 100, "New"
    )
    app.session_state["purchases"] = [previous_purchase]
    app.session_state["plans"] = []
    app.session_state["achievement_inbox"] = []
    app.session_state["settings"] = {}
    app.session_state["goal_history"] = [
        {"from_month": common.lg.month_of(common.app_today()), "goal_kg": 80}
    ]
    app.session_state["display_mode"] = "Dark"
    app.session_state["text_size"] = "M"
    app.session_state["dyslexia_font"] = False
    app.session_state["sound_enabled"] = False
    app.session_state["currency_name"] = "US Dollar ($)"
    app.session_state["goal_kg"] = 80
    app.session_state["uncertainty_band"] = 30
    app.session_state["reduce_motion"] = False
    app.session_state["accent_palette"] = "Evergreen"
    app.session_state["view_month"] = (2026, 10)
    app.run()
    app.file_uploader[0].set_value(
        ("shopimpact_backup.json", backup.encode("utf-8"), "application/json")
    ).run()

    assert app.session_state["purchases"] == [previous_purchase]
    assert any("1 purchase(s) · 1 plan(s) · 1 achievement(s)" in item.value for item in app.caption)
    assert any(
        "Date range: 2026-10-20 to 2026-10-25" in item.value for item in app.caption
    )
    assert any("Skipped rows: none." in item.value for item in app.caption)
    assert any("This will replace the current purchases" in item.value for item in app.info)
    next(
        widget
        for widget in app.checkbox
        if widget.label == "I understand this will replace the listed data."
    ).set_value(True).run()
    next(
        button for button in app.button if button.label == "Restore full backup"
    ).click().run()

    assert app.session_state["purchases"] == [purchase]
    assert app.session_state["purchases"][0]["note"] == '="Gift, packed carefully"'
    assert app.session_state["purchases"][0]["intent"] == "Gift"
    assert app.session_state["plans"] == [plan]
    assert app.session_state["achievement_inbox"] == achievements
    assert {
        key: app.session_state[key] for key in restored_settings
    } == restored_settings
    assert app.session_state["settings"] == restored_settings
    assert app.session_state["persistence_locked"] is False
    assert app.session_state["undo_stack"][-1]["description"] == "Restore full backup"

    next(
        button for button in app.button if button.label == "Undo: Restore full backup"
    ).click().run()
    assert app.session_state["purchases"] == [previous_purchase]
    assert app.session_state["plans"] == []
    assert app.session_state["achievement_inbox"] == []
    assert app.session_state["display_mode"] == "Dark"
    assert app.session_state["text_size"] == "M"
    assert app.session_state["settings"] == {}
    assert app.session_state["uncertainty_band"] == 30
    assert not app.exception


def test_full_backup_preview_reports_skipped_rows_and_reasons():
    purchase = lg.make_purchase(
        1, dt.date(2026, 10, 20), "Clothing", "Local shop", 24
    )
    backup_payload = json.loads(encode_saved_state([purchase], False))
    backup_payload["purchases_csv"] += (
        "not-a-date,Clothing,Local shop,New,false,24,12,false,,user\n"
    )
    app = make_app_test(page="views/settings_about.py", storage_available=True)
    app.file_uploader[0].set_value(
        (
            "partial.json",
            json.dumps(backup_payload).encode("utf-8"),
            "application/json",
        )
    ).run()

    assert any("1 purchase row(s) will be skipped" in item.value for item in app.warning)
    assert any(
        "Row 3: Date or USD price is not valid." in item.value for item in app.caption
    )
    assert app.session_state["purchases"] == []
    assert not app.exception


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"not-json", "could not be read"),
        (b'{"version":99,"purchases_csv":""}', "unsupported version"),
    ],
)
def test_full_backup_rejects_corrupt_or_wrong_version_without_mutating(payload, message):
    original = lg.make_purchase(
        1, dt.date(2026, 10, 10), "Clothing", "Local shop", 24
    )
    app = make_app_test(
        [original], page="views/settings_about.py", storage_available=True
    )
    app.file_uploader[0].set_value(
        ("invalid.json", payload, "application/json")
    ).run()

    assert app.session_state["purchases"] == [original]
    assert any(message in item.value for item in app.error)
    assert not app.exception


def test_full_backup_rejects_oversize_upload():
    app = make_app_test(page="views/settings_about.py", storage_available=True)
    app.file_uploader[0].set_value(
        ("large.json", b"x" * (2 * 1024 * 1024 + 1), "application/json")
    ).run()

    assert any("larger than the 2 MB upload limit" in item.value for item in app.error)
    assert app.session_state["purchases"] == []
    assert not app.exception


@pytest.mark.parametrize(
    ("model_version", "expected_notice"),
    [
        (lg.MODEL_VERSION, None),
        ("2025.9", "Estimates were recalculated with model 2026.1 (file was 2025.9)."),
        (None, "Estimates were recalculated with model 2026.1 (file was unknown)."),
    ],
)
def test_full_backup_restore_model_version_notice(model_version, expected_notice):
    payload = json.loads(encode_saved_state([], False))
    if model_version is None:
        payload.pop("model_version")
    else:
        payload["model_version"] = model_version
    app = make_app_test(page="views/settings_about.py", storage_available=True)
    app.file_uploader[0].set_value(
        ("versioned.json", json.dumps(payload).encode("utf-8"), "application/json")
    ).run()
    next(
        widget
        for widget in app.checkbox
        if widget.label == "I understand this will replace the listed data."
    ).set_value(True).run()
    next(
        button for button in app.button if button.label == "Restore full backup"
    ).click().run()

    messages = [
        item.value for item in app.info
        if "Estimates were recalculated with model" in item.value
    ]
    assert messages == ([expected_notice] if expected_notice else [])
    assert app.session_state["uncertainty_band"] == 30
    assert not app.exception


@pytest.mark.parametrize("band", [0, 50])
@pytest.mark.parametrize("page", ["views/home.py", "views/dashboard.py", "views/swaps_plan.py"])
def test_estimate_ranges_render_at_uncertainty_extremes(page, band):
    today = common.app_today()
    purchase = lg.make_purchase(1, today, "Clothing", "Local shop", 24)
    plan = pt.create_plan(
        "range-plan",
        "Clothing",
        "Local shop",
        24,
        "New",
        False,
        today,
    )
    app = make_app_test([purchase], page=page, storage_available=True)
    app.session_state["uncertainty_band"] = band
    app.session_state["plans"] = [plan]
    app.run()

    range_low, range_high = lg.estimate_range(purchase["co2_kg"], band / 100)
    if page == "views/swaps_plan.py":
        plan_low, plan_high = lg.estimate_range(plan["co2_kg"], band / 100)
        expected = (
            f"Model range: between {plan_low:.1f} and {plan_high:.1f} "
            "kilograms CO₂e."
        )
    elif page == "views/dashboard.py":
        expected = (
            f"Monthly estimate: about {purchase['co2_kg']:.0f} kg, model range between "
            f"{range_low:.0f} and {range_high:.0f} kilograms."
        )
    else:
        expected = (
            f"Likely range: between {range_low:.1f} and {range_high:.1f} "
            "kilograms CO₂e."
        )
    if page == "views/home.py":
        assert any(
            "Likely range: between" in caption.value
            for caption in app.caption
        )
    else:
        assert any(expected in caption.value for caption in app.caption)
    assert not app.exception


def test_empty_full_backup_cannot_replace_nonempty_journal():
    original = lg.make_purchase(
        1, dt.date(2026, 10, 10), "Clothing", "Local shop", 24
    )
    app = make_app_test(
        [original], page="views/settings_about.py", storage_available=True
    )
    empty_backup = encode_saved_state([], False)
    app.file_uploader[0].set_value(
        ("empty.json", empty_backup.encode("utf-8"), "application/json")
    ).run()
    next(
        widget
        for widget in app.checkbox
        if widget.label == "I understand this will replace the listed data."
    ).set_value(True).run()

    restore_button = next(
        button for button in app.button if button.label == "Restore full backup"
    )
    assert restore_button.disabled
    assert app.session_state["purchases"] == [original]
    assert any("cannot replace a non-empty purchase journal" in item.value for item in app.warning)
    assert not app.exception


def test_csv_restore_preview_reports_rows_dates_estimate_and_skips():
    purchase = lg.make_purchase(
        1, dt.date(2026, 9, 30), "Clothing", "Local shop", 24, "Second-hand"
    )
    csv_text = (
        export_purchases([purchase])
        + "not-a-date,Clothing,Local shop,New,false,24,12,false,,user\n"
    )
    app = make_app_test([purchase], page="views/purchases.py")

    _upload_and_preview(app, csv_text)

    assert app.session_state["purchases"] == [purchase]
    assert len(app.session_state["restore_preview"]["imported"]) == 1
    assert app.session_state["restore_preview"]["skipped"] == [
        (3, "Date or USD price is not valid.")
    ]
    assert any("1 row(s) will be imported" in item.value for item in app.markdown)
    assert any("30 Sep 2026" in item.value for item in app.caption)
    assert any("kg CO₂e" in item.value for item in app.caption)
    assert not app.exception


def test_csv_restore_zero_valid_rows_never_replaces_journal():
    purchase = lg.make_purchase(
        1, dt.date(2026, 9, 30), "Clothing", "Local shop", 24, "Second-hand"
    )
    app = make_app_test([purchase], page="views/purchases.py")
    invalid_csv = (
        "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n"
        "not-a-date,Clothing,Local shop,New,false,24,12\n"
    )

    _upload_and_preview(app, invalid_csv)

    assert app.session_state["purchases"] == [purchase]
    assert app.session_state["restore_preview"]["imported"] == []
    assert any("No valid" in error.value for error in app.error)
    assert not any(button.label == "Confirm Replace" for button in app.button)
    assert not app.exception


def test_csv_replace_requires_confirmation_and_full_journal_can_be_undone():
    original = [
        lg.make_purchase(1, dt.date(2026, 9, 1), "Clothing", "Local shop", 24),
        lg.make_purchase(2, dt.date(2026, 9, 2), "Books & Stationery", "Local library", 12),
    ]
    replacement = lg.make_purchase(
        1, dt.date(2026, 10, 1), "Clothing", "Local shop", 30
    )
    app = make_app_test(original, page="views/purchases.py")

    _upload_and_preview(app, export_purchases([replacement]))
    replace_button = next(
        button for button in app.button if button.label == "Confirm Replace"
    )
    assert replace_button.disabled
    assert app.session_state["purchases"] == original
    assert any("remove 2 current purchase(s)" in item.value for item in app.warning)

    next(
        widget for widget in app.checkbox
        if widget.label.startswith("I understand Replace")
    ).set_value(True).run()
    next(button for button in app.button if button.label == "Confirm Replace").click().run()
    assert app.session_state["purchases"][0]["date"] == replacement["date"]
    assert app.session_state["undo_stack"][-1]["description"] == (
        "Replaced the journal from CSV."
    )
    next(
        button for button in app.button
        if button.label == "Undo: Replaced the journal from CSV."
    ).click().run()
    assert app.session_state["purchases"] == original
    assert not app.exception


def test_csv_add_skips_duplicate_purchase_identity():
    existing = lg.make_purchase(
        1, dt.date(2026, 9, 30), "Clothing", "Local shop", 24, "Second-hand"
    )
    new_purchase = lg.make_purchase(
        2, dt.date(2026, 10, 1), "Books & Stationery", "Local library", 12
    )
    app = make_app_test([existing], page="views/purchases.py")
    next(widget for widget in app.radio if widget.key == "import_mode").set_value(
        "Add to current purchases"
    ).run()

    _upload_and_preview(app, export_purchases([existing, new_purchase]))

    preview = app.session_state["restore_preview"]
    assert len(preview["imported"]) == 1
    assert preview["duplicates"] == 1
    next(button for button in app.button if button.label == "Add 1 purchase").click().run()
    assert len(app.session_state["purchases"]) == 2
    assert app.session_state["purchases"][0] == existing
    assert app.session_state["purchases"][1]["id"] == 2
    assert app.session_state["import_report"]["duplicates"] == 1
    next(
        button for button in app.button
        if button.label == "Undo: Added 1 purchase from CSV."
    ).click().run()
    assert app.session_state["purchases"] == [existing]
    assert not app.exception


@pytest.mark.parametrize(
    ("csv_bytes", "expected_message"),
    [
        (b"x" * (2 * 1024 * 1024 + 1), "larger than 2 MB"),
        (
            (
                "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n"
                + "2026-09-30,Clothing,Local shop,New,false,24,12\n" * 5001
            ).encode(),
            "limit is 5,000",
        ),
    ],
)
def test_csv_restore_rejects_files_over_size_or_row_limit(csv_bytes, expected_message):
    app = make_app_test(page="views/purchases.py")
    app.file_uploader[0].set_value(("large.csv", csv_bytes, "text/csv")).run()

    if b"x" not in csv_bytes:
        next(
            button for button in app.button if button.label == "Preview restore"
        ).click().run()

    assert any(expected_message in error.value for error in app.error)
    assert app.session_state["purchases"] == []
    assert not app.exception


def test_session_preserves_demo_source_label():
    purchase = lg.make_purchase(
        3,
        dt.date(2026, 10, 4),
        "Books & Stationery",
        "Local library",
        12,
    )
    purchase.update({"source": "demo", "recurring": False, "recurring_group": None})
    app = make_app_test([purchase])

    assert len(app.session_state["purchases"]) == 1
    assert app.session_state["purchases"][0]["source"] == "demo"
    assert not app.exception


def test_recurring_purchase_logs_bounded_monthly_entries():
    app = make_app_test()
    category = next(
        widget for widget in app.radio if widget.label == "Product type"
    )
    category.set_value("Books & Stationery").run()
    brand = next(
        widget
        for widget in app.selectbox
        if widget.label == "Brand or shop" and widget.key == "brand_Books & Stationery"
    )
    brand.select("Local library").run()
    app.date_input[0].set_value(dt.date(2026, 1, 15)).run()
    next(
        widget
        for widget in app.checkbox
        if widget.label == "Repeat monthly through the current month"
    ).set_value(True).run()

    expected_count = len(
        ps.monthly_occurrences(
            dt.date(2026, 1, 15),
            dt.datetime.now().astimezone().date(),
        )
    )
    next(
        button for button in app.button if button.label == "Log this purchase"
    ).click().run()

    purchases = app.session_state["purchases"]
    assert len(purchases) == expected_count
    assert all(p["recurring"] for p in purchases)
    assert len({p["recurring_group"] for p in purchases}) == 1
    assert purchases[-1]["date"] <= dt.datetime.now().astimezone().date()
    assert not app.exception


def test_edit_purchase_revalidates_recalculates_and_can_be_undone():
    app = make_app_test()
    category = next(
        widget for widget in app.radio if widget.label == "Product type"
    )
    category.set_value("Smartphone").run()
    brand = next(
        widget
        for widget in app.selectbox
        if widget.label == "Brand or shop" and widget.key == "brand_Smartphone"
    )
    brand.select("Fairphone").run()
    app.number_input[0].set_value(100.0).run()
    app.text_input[0].set_value("Original note").run()
    next(widget for widget in app.selectbox if widget.key == "entry_intent").select(
        "Gift"
    ).run()
    next(
        button for button in app.button if button.label == "Log this purchase"
    ).click().run()
    app.run()
    app.switch_page("views/purchases.py").run()
    table = app.dataframe[0]
    app.session_state[table.key] = {
        "selection": {"rows": [0], "columns": [], "cells": []}
    }
    app.run()
    next(button for button in app.button if button.label == "Edit selected").click().run()

    price_widget = next(
        widget for widget in app.number_input if widget.label == "Price ($)"
    )
    price_widget.set_value(0.0).run()
    assert app.session_state["purchases"][0]["price_usd"] == 100.0
    assert any("greater than zero" in error.value for error in app.error)

    price_widget = next(
        widget for widget in app.number_input if widget.label == "Price ($)"
    )
    price_widget.set_value(40.0).run()
    next(
        widget for widget in app.text_input if widget.label == "Note (optional)"
    ).set_value("Edited note").run()
    next(button for button in app.button if button.label == "Save edit").click().run()
    updated = app.session_state["purchases"][0]
    assert updated["price_usd"] == 40.0
    assert updated["co2_kg"] != 0
    assert updated["note"] == "Edited note"
    assert updated["intent"] == "Gift"

    next(
        button for button in app.button
        if button.label == "Undo: Edited Smartphone purchase."
    ).click().run()
    assert app.session_state["purchases"][0]["price_usd"] == 100.0
    assert app.session_state["purchases"][0]["note"] == "Original note"
    assert app.session_state["purchases"][0]["intent"] == "Gift"
    assert not app.exception


def test_dashboard_intent_split_is_hidden_until_three_purchases_are_tagged(monkeypatch):
    monkeypatch.setattr(common, "app_today", lambda: dt.date(2026, 10, 15))
    purchases = [
        {
            **lg.make_purchase(
                index,
                dt.date(2026, 10, index),
                "Clothing",
                f"Shop {index}",
                10,
                intent="Need" if index < 3 else "",
            )
        }
        for index in range(1, 4)
    ]
    app = make_app_test(purchases, page="views/dashboard.py")
    next(widget for widget in app.radio if widget.key == "dashboard_chart_mode").set_value(
        "Category"
    ).run()
    assert not any(widget.label == "Show purchase intent split" for widget in app.checkbox)

    app.session_state["purchases"][2]["intent"] = "Want"
    app.run()
    next(
        widget for widget in app.radio if widget.key == "dashboard_chart_mode"
    ).set_value("Category").run()
    next(
        widget for widget in app.checkbox if widget.label == "Show purchase intent split"
    ).set_value(True).run()
    next(
        widget
        for widget in app.checkbox
        if widget.label == "View intent split as a text table"
    ).set_value(True).run()
    assert any("Estimated CO₂e (kg)" in item.value.columns for item in app.dataframe)
    assert not app.exception


def test_purchase_history_uses_single_selectable_table_and_paginates_25_rows():
    purchases = [
        lg.make_purchase(
            index,
            dt.date(2026, 10, 1),
            "Clothing",
            f"Shop {index}",
            10 + index,
        )
        for index in range(1, 31)
    ]
    app = make_app_test(purchases, page="views/purchases.py")

    assert len(app.dataframe) == 1
    assert len(app.dataframe[0].value) == 25
    assert any(button.label == "Edit selected" and button.disabled for button in app.button)
    assert any(button.label == "Delete selected" and button.disabled for button in app.button)
    next(button for button in app.button if button.label == "Next").click().run()
    assert len(app.dataframe) == 1
    assert len(app.dataframe[0].value) == 5
    assert any("Page 2 of 2" in caption.value for caption in app.caption)
    next(button for button in app.button if button.label == "Previous").click().run()
    assert len(app.dataframe[0].value) == 25
    assert not app.exception


def test_purchase_edit_dialog_cancel_keeps_purchase_unchanged():
    purchase = lg.make_purchase(
        1, dt.date(2026, 10, 1), "Clothing", "Local shop", 24
    )
    app = make_app_test([purchase], page="views/purchases.py")
    next(widget for widget in app.selectbox if widget.label == "Selected purchase").select(1).run()
    next(button for button in app.button if button.label == "Edit selected").click().run()

    assert any(widget.label == "Price ($)" for widget in app.number_input)
    assert any(button.label == "Save edit" for button in app.button)
    next(button for button in app.button if button.label == "Cancel edit").click().run()

    assert app.session_state["purchases"] == [purchase]
    assert app.session_state["editing_id"] is None
    assert not app.exception


def test_recurring_series_can_be_removed_as_a_group_and_undone():
    app = make_app_test()
    category = next(
        widget for widget in app.radio if widget.label == "Product type"
    )
    category.set_value("Books & Stationery").run()
    brand = next(
        widget
        for widget in app.selectbox
        if widget.label == "Brand or shop" and widget.key == "brand_Books & Stationery"
    )
    brand.select("Local library").run()
    app.date_input[0].set_value(dt.date(2026, 8, 1)).run()
    next(
        widget
        for widget in app.checkbox
        if widget.label == "Repeat monthly through the current month"
    ).set_value(True).run()
    next(
        button for button in app.button if button.label == "Log this purchase"
    ).click().run()
    app.run()
    app.switch_page("views/purchases.py").run()
    original_count = len(app.session_state["purchases"])

    next(
        button for button in app.button if button.label == "Remove selected series"
    ).click().run()
    assert app.session_state["purchases"] == []
    assert app.session_state["undo_stack"][-1]["description"] == (
        f"Removed recurring series ({original_count} purchases)."
    )
    next(
        button for button in app.button
        if button.label.startswith("Undo: Removed recurring series")
    ).click().run()
    assert len(app.session_state["purchases"]) == original_count
    assert not app.exception


def test_clear_saved_data_requires_confirmation_and_browser_ack():
    purchase = lg.make_purchase(
        1,
        dt.date(2026, 10, 1),
        "Books & Stationery",
        "Local library",
        12,
    )
    app = make_app_test(
        [purchase],
        storage_available=True,
        saved_signature=encode_saved_state([purchase], False),
        page="views/settings_about.py",
    )
    next(
        button for button in app.button if button.label == "Clear saved browser data"
    ).click().run()
    assert len(app.session_state["purchases"]) == 1
    next(
        button for button in app.button if button.label == "Confirm clear saved data"
    ).click().run()
    assert len(app.session_state["purchases"]) == 1
    assert app.session_state["clear_saved_data_pending"] is True
    assert not app.exception


def test_undo_stack_is_capped_and_not_in_saved_browser_payload():
    app = make_app_test(page="views/settings_about.py")

    for _ in range(12):
        next(
            button for button in app.button
            if button.label == "Load labelled synthetic demo data"
        ).click().run()

    stack = app.session_state["undo_stack"]
    assert len(stack) == 10
    assert all(item["description"] == "Loaded synthetic demo data." for item in stack)
    assert sum(
        "Loaded synthetic demo data." in item.value
        for item in app.caption
        if hasattr(item, "value")
    ) == 10
    saved = encode_saved_state(
        app.session_state["purchases"],
        app.session_state["guide_dismissed"],
        app.session_state["achievement_inbox"],
        app.session_state["plans"],
        {},
    )
    assert "undo_stack" not in json.loads(saved)
    assert not app.exception


@pytest.mark.parametrize(
    "saved",
    [
        "not-json",
        json.dumps(
            {
                "version": 3,
                "purchases_csv": (
                    "date,product_type,brand,condition,packaging,price_usd,"
                    "co2e_kg,recurring,recurring_group,source\n"
                    "2026-09-30,Clothing,Local shop,New,false,24,12,false,,user\n"
                    "bad-date,Clothing,Local shop,New,false,24,12,false,,user\n"
                ),
            }
        ),
    ],
)
def test_unrestored_browser_data_is_locked_and_never_written(monkeypatch, saved):
    writes = []
    monkeypatch.setattr(bs, "read_saved_value", lambda: (True, saved, None))
    monkeypatch.setattr(
        bs, "write_saved_value", lambda value: (writes.append(value) or True, None)
    )
    app = AppTest.from_file(APP_PATH)
    app.session_state["guest_access"] = True
    app.session_state["browser_storage_loaded"] = False

    app.run()

    assert app.session_state["persistence_locked"] is True
    assert app.session_state["raw_saved_state"] == saved
    assert writes == []
    assert any(
        button.label == "Download my saved data (raw JSON)"
        for button in app.download_button
    )
    assert any(
        button.label == "Discard saved data and start fresh" for button in app.button
    )
    assert not app.exception


def test_locked_saved_data_discard_requires_confirmation(monkeypatch):
    removals = []
    monkeypatch.setattr(
        bs, "remove_saved_value", lambda: (removals.append(True) or True, None)
    )
    app = make_app_test(storage_available=True)
    app.session_state["persistence_locked"] = True
    app.session_state["raw_saved_state"] = "not-json"
    app.run()

    next(
        button
        for button in app.button
        if button.label == "Discard saved data and start fresh"
    ).click().run()

    assert removals == []
    assert any(
        button.label == "Confirm discard and start fresh" for button in app.button
    )
    next(
        button
        for button in app.button
        if button.label == "Confirm discard and start fresh"
    ).click().run()

    assert removals == [True]
    assert app.session_state["persistence_locked"] is False
    assert app.session_state["purchases"] == []
    assert not app.exception


def test_plan_mode_saves_a_plan_without_adding_a_purchase():
    app = make_app_test()
    next(widget for widget in app.radio if widget.key == "entry_mode").set_value(
        "Plan a purchase"
    ).run()
    next(
        widget
        for widget in app.selectbox
        if widget.label == "Brand or shop" and widget.key == "brand_Clothing"
    ).select("Patagonia").run()
    app.number_input[0].set_value(100.0).run()

    next(
        button for button in app.button if button.label == "Save this plan"
    ).click().run()

    assert app.session_state["purchases"] == []
    assert len(app.session_state["plans"]) == 1
    assert app.session_state["plans"][0]["co2_kg"] == 41.25
    assert not app.exception


def test_swapped_plan_is_converted_to_a_logged_alternative():
    from ui.actions import badge_progress

    today = dt.datetime.now().astimezone().date()
    plan = pt.create_plan(
        "test-plan",
        "Clothing",
        "Local shop",
        100,
        "New",
        False,
        today,
    )
    app = make_app_test(page="views/swaps_plan.py")
    app.session_state["plans"] = [plan]
    app.run()
    next(
        button for button in app.button if button.label == "Mark swapped"
    ).click().run()

    assert app.session_state["plans"] == []
    assert len(app.session_state["purchases"]) == 1
    assert app.session_state["purchases"][0]["condition"] == "Second-hand"
    swap = app.session_state["purchases"][0]
    assert swap["source"] == "swap"
    assert swap["swap_from_label"] == "Buy it second-hand"
    assert swap["swap_saved_kg"] == pytest.approx(
        max(0, plan["co2_kg"] - swap["co2_kg"])
    )
    assert badge_progress(
        "swaps_chosen",
        [swap],
        lg.month_of(today),
        app.session_state["purchase_month_index"],
    ) == (1, 3)
    next(
        button
        for button in app.button
        if button.label == "Undo: Marked Clothing plan swapped."
    ).click().run()
    assert app.session_state["purchases"] == []
    assert app.session_state["plans"] == [plan]
    assert not app.exception


def test_swap_savings_are_shown_in_dashboard_and_monthly_story():
    purchase = lg.make_purchase(
        1, common.app_today(), "Clothing", "Local shop", 100, "Second-hand"
    )
    purchase.update(
        {
            "source": "swap",
            "swap_from_label": "Buy it second-hand",
            "swap_saved_kg": 20.0,
            "swap_original_co2_kg": 55.0,
            "swap_original_price_usd": 100.0,
        }
    )
    dashboard = make_app_test([purchase], page="views/dashboard.py")

    assert any(
        "Saved through swaps" in item.value
        and "20.0 kg" in item.value
        for item in dashboard.markdown
    )
    assert not dashboard.exception

    review = make_app_test([purchase], page="views/month_review.py")

    assert any(
        "illustrative estimate" in item.value
        and "not a verified saving" in item.value
        for item in review.markdown
    )
    assert not review.exception


def test_swap_purchase_history_uses_swap_entry_label():
    purchase = lg.make_purchase(
        1, common.app_today(), "Clothing", "Local shop", 100, "Second-hand"
    )
    purchase.update(
        {"source": "swap", "swap_from_label": "Buy it second-hand", "swap_saved_kg": 20}
    )
    app = make_app_test([purchase], page="views/purchases.py")

    assert app.dataframe[0].value.iloc[0]["Entry"] == "Swap"
    assert not app.exception


def test_skipping_a_plan_shows_an_illustrative_avoided_estimate():
    app = make_app_test(page="views/swaps_plan.py")
    app.session_state["plans"] = [
        pt.create_plan(
            "skip-plan",
            "Clothing",
            "Local shop",
            100,
            "New",
            False,
            dt.datetime.now().astimezone().date(),
        )
    ]
    app.run()
    next(button for button in app.button if button.label == "Skip plan").click().run()

    assert app.session_state["plans"] == []
    assert app.session_state["purchases"] == []
    assert any(
        "avoided estimate" in item.value and "illustrative" in item.value
        for item in app.success
    )
    assert not app.exception


def test_what_if_simulator_uses_monthly_purchase_data():
    app = make_app_test(
        purchases=lg.demo_purchases(), page="views/swaps_plan.py"
    )

    assert any(
        widget.label == "Swap this share of new clothing to second-hand"
        for widget in app.slider
    )
    assert any(metric.label == "Current illustrative estimate" for metric in app.metric)
    assert not app.exception


def test_privacy_disclosure_names_hosted_session_processing():
    app = make_app_test(page="views/settings_about.py")

    assert any(item.label == "Privacy and your data" for item in app.get("expander"))
    assert any(
        "Streamlit processes active session data" in item.value
        for item in app.markdown
        if hasattr(item, "value")
    )
    assert not app.exception


def test_settings_and_sidebar_preferences_stay_in_sync_in_both_directions():
    app = make_app_test(page="views/settings_about.py", display_mode="Light")
    side_key = "topbar_display_mode_settings-and-about"
    next(widget for widget in app.radio if widget.key == side_key).set_value("Dark").run()
    assert app.session_state["display_mode"] == "Dark"
    assert next(widget for widget in app.radio if widget.key == "settings_display_mode").value == "Dark"
    next(widget for widget in app.radio if widget.key == "settings_display_mode").set_value("Light").run()
    assert app.session_state["display_mode"] == "Light"
    assert next(widget for widget in app.radio if widget.key == side_key).value == "Light"
    next(widget for widget in app.selectbox if widget.key == "topbar_currency_name_settings-and-about").select("Euro (€)").run()
    assert next(widget for widget in app.selectbox if widget.key == "settings_currency").value == "Euro (€)"
    assert not app.exception
