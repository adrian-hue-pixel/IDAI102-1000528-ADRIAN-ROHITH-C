"""Tests for versioned browser-save serialization and validation."""

import datetime as dt
import json

import pytest

import logic as lg
import plan_tools
from browser_persistence import decode_saved_state, encode_saved_state
from data_io import export_purchases


def test_browser_state_round_trips_records_guide_and_achievement_inbox():
    purchase = lg.make_purchase(
        7,
        dt.date(2026, 9, 30),
        "Clothing",
        "Local shop",
        24,
        "Second-hand",
        True,
    )
    purchase.update(
        {
            "recurring": True,
            "recurring_group": "series-abc",
            "source": "demo",
            "note": 'Gift note, "packed carefully"',
            "intent": "Gift",
        }
    )

    achievements = [
        {"name": "First Step", "month": "Sep 2026", "reason": "You logged a purchase."}
    ]
    plan = {
        "plan_id": "plan-1",
        "date": dt.date(2026, 10, 8),
        "product_type": "Clothing",
        "brand": "Local shop",
        "price_usd": 24.0,
        "condition": "New",
        "low_packaging": False,
        "co2_kg": 13.2,
    }
    encoded = encode_saved_state(
        [purchase],
        guide_dismissed=True,
        achievements=achievements,
        plans=[plan],
        settings={
            "display_mode": "Light",
            "accent_palette": "Spring canopy",
            "currency_name": "US Dollar ($)",
            "goal_kg": 60,
            "goal_history": [
                {"from_month": (2025, 9), "goal_kg": 80},
                {"from_month": (2026, 9), "goal_kg": 60},
            ],
            "reduce_motion": True,
            "view_month": (2026, 9),
            "text_size": "L",
            "dyslexia_font": True,
            "sound_enabled": False,
        },
    )
    (
        restored,
        guide_dismissed,
        skipped,
        restored_achievements,
        restored_plans,
        restored_settings,
    ) = decode_saved_state(encoded)

    assert skipped == []
    assert guide_dismissed is True
    assert restored_achievements == achievements
    assert len(restored) == 1
    assert restored[0]["id"] == 1
    assert restored[0]["recurring"] is True
    assert restored[0]["recurring_group"] == "series-abc"
    assert restored[0]["source"] == "demo"
    assert restored[0]["note"] == 'Gift note, "packed carefully"'
    assert restored[0]["intent"] == "Gift"
    assert restored[0]["co2_kg"] == purchase["co2_kg"]
    assert restored_plans[0]["plan_id"] == plan["plan_id"]
    assert restored_plans[0]["date"] == plan["date"]
    assert restored_plans[0]["co2_kg"] == plan["co2_kg"]
    assert restored_settings == {
        "display_mode": "Light",
        "accent_palette": "Spring canopy",
        "currency_name": "US Dollar ($)",
        "goal_kg": 60,
        "goal_history": [
            {"from_month": (2025, 9), "goal_kg": 80},
            {"from_month": (2026, 9), "goal_kg": 60},
        ],
        "reduce_motion": True,
        "view_month": (2026, 9),
        "text_size": "L",
        "dyslexia_font": True,
        "sound_enabled": False,
        "uncertainty_band": 30,
        "month_review_last_visit": None,
        "xp_scoring_notice_dismissed": False,
    }


@pytest.mark.parametrize(
    ("value", "message", "error_type"),
    [
        (None, "unsupported format", TypeError),
        ("not-json", "could not be read", ValueError),
        (
            json.dumps({"version": 4, "purchases_csv": ""}),
            "unsupported version",
            ValueError,
        ),
        (json.dumps({"version": 1}), "missing", ValueError),
        (
            json.dumps(
                {
                    "version": 1,
                    "purchases_csv": "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n",
                    "guide_dismissed": "yes",
                }
            ),
            "preference must be a boolean",
            TypeError,
        ),
    ],
)
def test_browser_state_rejects_corrupt_or_unsupported_payloads(
    value, message, error_type
):
    with pytest.raises(error_type, match=message):
        decode_saved_state(value)


def test_browser_state_migrates_version_one_without_an_achievement_inbox():
    value = json.dumps(
        {
            "version": 1,
            "purchases_csv": (
                "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n"
            ),
            "guide_dismissed": True,
        }
    )

    purchases, guide_dismissed, skipped, achievements, plans, settings = decode_saved_state(value)

    assert purchases == []
    assert guide_dismissed is True
    assert skipped == []
    assert achievements == []
    assert plans == []
    assert settings == {
        "uncertainty_band": 30,
        "month_review_last_visit": None,
        "xp_scoring_notice_dismissed": False,
    }


def test_browser_state_migrates_legacy_goal_to_history():
    payload = json.loads(
        encode_saved_state([], False, settings={"goal_kg": 65})
    )
    payload["settings"].pop("goal_history")

    restored_settings = decode_saved_state(
        json.dumps(payload), today=dt.date(2026, 10, 15)
    )[-1]

    assert restored_settings["goal_kg"] == 65
    assert restored_settings["goal_history"] == [
        {"from_month": (2026, 10), "goal_kg": 65}
    ]


def test_browser_state_migrates_version_two_payload_without_plans():
    value = json.dumps(
        {
            "version": 2,
            "purchases_csv": (
                "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n"
            ),
            "guide_dismissed": False,
            "achievements": [],
        }
    )

    plans = decode_saved_state(value)[4]

    assert plans == []


def test_browser_state_rejects_malformed_achievement_items():
    value = json.dumps(
        {
            "version": 3,
            "purchases_csv": (
                "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n"
            ),
            "achievements": [{"name": "First Step"}],
        }
    )

    with pytest.raises(TypeError, match="achievement data"):
        decode_saved_state(value)


@pytest.mark.parametrize(
    ("key", "value", "error_type"),
    [
        ("display_mode", "Sepia", ValueError),
        ("accent_palette", "Neon", ValueError),
        ("currency_name", "Imaginary", ValueError),
        ("goal_kg", 21, ValueError),
        (
            "goal_history",
            [{"from_month": (2026, 10), "goal_kg": 67}],
            ValueError,
        ),
        (
            "goal_history",
            [
                {"from_month": (year, 1), "goal_kg": 80}
                for year in range(2000, 2061)
            ],
            ValueError,
        ),
        (
            "goal_history",
            [{"from_month": (2026, 13), "goal_kg": 80}],
            ValueError,
        ),
        ("reduce_motion", "yes", TypeError),
        ("text_size", "XXL", ValueError),
    ],
)
def test_browser_state_rejects_invalid_saved_preferences(key, value, error_type):
    payload = {
        "version": 3,
        "purchases_csv": (
            "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n"
        ),
        "settings": {key: value},
    }

    with pytest.raises(error_type, match="Saved"):
        decode_saved_state(json.dumps(payload))


def test_browser_state_ignores_unknown_preferences_without_saving_them():
    saved = encode_saved_state(
        [],
        guide_dismissed=False,
        settings={"internal_debug_flag": True, "reduce_motion": True},
    )

    assert decode_saved_state(saved)[-1] == {
        "reduce_motion": True,
        "uncertainty_band": 30,
        "month_review_last_visit": None,
        "xp_scoring_notice_dismissed": False,
    }


@pytest.mark.parametrize("band", [0, 15, 30, 50])
def test_browser_state_round_trips_uncertainty_band(band):
    restored_settings = decode_saved_state(
        encode_saved_state([], False, settings={"uncertainty_band": band})
    )[-1]

    assert restored_settings["uncertainty_band"] == band


def test_saved_state_includes_current_model_version():
    payload = json.loads(encode_saved_state([], False))

    assert payload["model_version"] == lg.MODEL_VERSION


@pytest.mark.parametrize("band", [True, -5, 55, 11, 12])
def test_browser_state_rejects_invalid_uncertainty_band(band):
    payload = {
        "version": 3,
        "purchases_csv": (
            "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n"
        ),
        "settings": {"uncertainty_band": band},
    }

    with pytest.raises(ValueError, match="uncertainty band"):
        decode_saved_state(json.dumps(payload))


def test_browser_state_migrates_missing_uncertainty_band_to_default():
    payload = json.loads(encode_saved_state([], False))
    payload["settings"].pop("uncertainty_band")

    assert decode_saved_state(json.dumps(payload))[-1]["uncertainty_band"] == 30


def test_browser_state_round_trips_month_review_visit_and_xp_notice():
    settings = decode_saved_state(
        encode_saved_state(
            [],
            False,
            settings={
                "month_review_last_visit": "2026-10-31",
                "xp_scoring_notice_dismissed": True,
            },
        )
    )[-1]

    assert settings["month_review_last_visit"] == "2026-10-31"
    assert settings["xp_scoring_notice_dismissed"] is True


def test_browser_state_round_trips_goal_history():
    history = [
        {"from_month": (2025, 11), "goal_kg": 80},
        {"from_month": (2026, 9), "goal_kg": 65},
    ]

    settings = decode_saved_state(
        encode_saved_state(
            [],
            False,
            settings={"goal_kg": 65, "goal_history": history},
        )
    )[-1]

    assert settings["goal_history"] == history


def test_browser_state_round_trips_swap_metadata_through_purchase_csv():
    plan = plan_tools.create_plan(
        "backup-swap",
        "Clothing",
        "Local shop",
        100,
        "New",
        False,
        dt.date(2026, 10, 8),
    )
    swap = plan_tools.swapped_purchase(plan, "Buy it second-hand", 1)

    restored = decode_saved_state(
        encode_saved_state([swap], False, settings={"goal_kg": 80})
    )[0][0]

    assert restored["source"] == "swap"
    assert restored["swap_from_label"] == "Buy it second-hand"
    assert restored["swap_saved_kg"] == swap["swap_saved_kg"]
    assert restored["swap_original_co2_kg"] == swap["swap_original_co2_kg"]
    assert restored["swap_original_price_usd"] == swap["swap_original_price_usd"]


def test_browser_state_keeps_valid_rows_and_reports_partially_invalid_csv():
    purchase = lg.make_purchase(
        1, dt.date(2026, 9, 30), "Clothing", "Local shop", 24, "Second-hand"
    )
    payload = json.loads(encode_saved_state([purchase], False))
    payload["purchases_csv"] = (
        export_purchases([purchase])
        + "not-a-date,Clothing,Local shop,New,false,24,12.000,false,,user\n"
    )

    purchases, _, skipped, *_ = decode_saved_state(json.dumps(payload))

    assert len(purchases) == 1
    assert skipped == [(3, "Date or USD price is not valid.")]


def test_browser_state_recalculates_saved_plan_estimate_with_current_model():
    plan = plan_tools.create_plan(
        "plan-model-change",
        "Clothing",
        "Local shop",
        24,
        "New",
        False,
        dt.date(2026, 10, 8),
    )
    payload = json.loads(encode_saved_state([], False, plans=[plan]))
    payload["plans"][0]["co2_kg"] = plan["co2_kg"] + 100

    restored_plan = decode_saved_state(json.dumps(payload))[4][0]

    assert restored_plan["plan_id"] == plan["plan_id"]
    assert restored_plan["co2_kg"] == plan_tools.create_plan(
        "plan-model-change",
        "Clothing",
        "Local shop",
        24,
        "New",
        False,
        dt.date(2026, 10, 8),
    )["co2_kg"]


@pytest.mark.parametrize(("old_mode", "new_mode"), [("Ivory", "Light"), ("Obsidian", "Dark"), ("High contrast", "Dark")])
def test_legacy_display_modes_migrate_without_losing_purchase_data(old_mode, new_mode):
    purchase = lg.make_purchase(1, dt.date(2026, 9, 30), "Clothing", "Local shop", 24)
    payload = json.loads(encode_saved_state([purchase], False, settings={"display_mode": "Light"}))
    payload["settings"]["display_mode"] = old_mode
    restored, _, skipped, _, _, settings = decode_saved_state(json.dumps(payload))
    assert skipped == []
    assert len(restored) == 1
    assert restored[0]["price_usd"] == purchase["price_usd"]
    assert settings["display_mode"] == new_mode
