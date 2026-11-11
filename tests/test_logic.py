"""Unit tests for ShopImpact's logic engine.  Run with:  python -m pytest -v"""

import datetime as dt
import os
import sys
from itertools import permutations

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logic as lg

TODAY = dt.date(2026, 10, 15)


def buy(pid, ptype, price, brand="Generic", cond="New", pack=False, date=TODAY):
    return lg.make_purchase(pid, date, ptype, brand, price, cond, pack)


# ---------------------------------------------------------------- impact maths
def test_basic_impact_is_price_times_multiplier():
    r = lg.calculate_impact("Leather Shoes", 100)
    assert r["co2_kg"] == pytest.approx(95.0)  # 100 x 0.95
    assert r == {
        "co2_kg": 95.0,
        "multiplier": lg.PRODUCTS["Leather Shoes"]["multiplier"],
        "condition_factor": 1.0,
        "brand_factor": 1.0,
        "packaging_factor": 1.0,
        "curated_brand_match": False,
    }


@pytest.mark.parametrize(
    ("co2_kg", "band", "expected"),
    [
        (100, 0, (100.0, 100.0)),
        (100, 0.3, (70.0, 130.0)),
        (1, 0.5, (0.5, 1.5)),
        (0.05, 0.5, (0.0, 0.1)),
    ],
)
def test_estimate_range_returns_rounded_nonnegative_bounds(co2_kg, band, expected):
    assert lg.estimate_range(co2_kg, band) == expected


@pytest.mark.parametrize("band", [-0.01, 0.51, float("nan"), True])
def test_estimate_range_rejects_uncertainty_outside_bounds(band):
    with pytest.raises(ValueError, match="uncertainty band"):
        lg.estimate_range(10, band)


def test_second_hand_is_much_lower_than_new():
    new = lg.calculate_impact("Clothing", 50, "New")["co2_kg"]
    used = lg.calculate_impact("Clothing", 50, "Second-hand")["co2_kg"]
    assert used == pytest.approx(new * 0.20)


def test_curated_brand_match_and_packaging_reduce_estimate():
    base = lg.calculate_impact("Cosmetics & Personal Care", 40)["co2_kg"]
    both = lg.calculate_impact("Cosmetics & Personal Care", 40, "New", "Lush", True)[
        "co2_kg"
    ]
    assert both == pytest.approx(base * 0.75 * 0.90)


def test_unknown_inputs_are_rejected():
    with pytest.raises(ValueError):
        lg.calculate_impact("Spaceship", 10)
    with pytest.raises(ValueError):
        lg.calculate_impact("Clothing", -5)
    with pytest.raises(ValueError):
        lg.calculate_impact("Clothing", 5, "Stolen")


@pytest.mark.parametrize(
    "price", [float("nan"), float("inf"), float("-inf"), "10", True, 10**1000]
)
def test_impact_rejects_non_finite_or_non_numeric_prices(price):
    with pytest.raises(ValueError):
        lg.calculate_impact("Clothing", price)


def test_purchase_validation_catches_missing_and_malformed_inputs():
    errors = lg.validate_purchase("Unknown", "  ", 0, "Stolen", "not a date")
    assert len(errors) == 5
    assert any("category" in error for error in errors)
    assert any("brand" in error for error in errors)
    assert any("price" in error for error in errors)
    assert any("condition" in error for error in errors)
    assert any("date" in error for error in errors)


def test_purchase_validation_accepts_a_valid_purchase():
    assert (
        lg.validate_purchase("Clothing", "Local shop", 25.0, "New", TODAY, False) == []
    )
    assert any(
        "no greater" in error
        for error in lg.validate_purchase(
            "Clothing", "Local shop", lg.MAX_PRICE_USD + 1, "New", TODAY, False
        )
    )
    assert any(
        "packaging" in error
        for error in lg.validate_purchase(
            "Clothing", "Local shop", 25.0, "New", TODAY, "yes"
        )
    )


def test_purchase_note_and_intent_validation_and_normalization():
    purchase = lg.make_purchase(
        1,
        TODAY,
        "Clothing",
        "Local shop",
        25,
        note="  A thoughtful note  ",
        intent="Want",
    )

    assert purchase["note"] == "A thoughtful note"
    assert purchase["intent"] == "Want"
    assert any(
        "140 characters" in error
        for error in lg.validate_purchase(
            "Clothing",
            "Local shop",
            25,
            "New",
            TODAY,
            note="x" * (lg.MAX_NOTE_LENGTH + 1),
        )
    )
    assert any(
        "intent" in error.lower()
        for error in lg.validate_purchase(
            "Clothing", "Local shop", 25, "New", TODAY, intent="Maybe"
        )
    )
    with pytest.raises(ValueError, match="140 characters"):
        lg.make_purchase(
            2,
            TODAY,
            "Clothing",
            "Local shop",
            25,
            note="x" * (lg.MAX_NOTE_LENGTH + 1),
        )


def test_purchase_date_bounds_and_plan_horizon():
    today = dt.datetime.now().astimezone().date()
    before_minimum = dt.date(1, 1, 1)
    far_future = dt.date(9999, 12, 31)

    assert lg.MIN_PURCHASE_DATE == dt.date(2000, 1, 1)
    assert lg.max_purchase_date(today) == today
    assert lg.max_purchase_date(today, is_plan=True) == today.replace(
        year=today.year + 2
    )
    assert any(
        "on or after" in error
        for error in lg.validate_purchase(
            "Clothing", "Local shop", 25, "New", before_minimum
        )
    )
    assert any(
        "future" in error
        for error in lg.validate_purchase("Clothing", "Local shop", 25, "New", far_future)
    )
    allowed_plan_date = lg.max_purchase_date(today, is_plan=True)
    assert lg.validate_purchase(
        "Clothing", "Local shop", 25, "New", allowed_plan_date, is_plan=True
    ) == []
    assert any(
        "two years" in error
        for error in lg.validate_purchase(
            "Clothing",
            "Local shop",
            25,
            "New",
            allowed_plan_date + dt.timedelta(days=1),
            is_plan=True,
        )
    )


def test_add_purchase_validates_and_appends_exactly_once():
    purchases = []
    item = lg.add_purchase(
        purchases, 1, TODAY, "Books & Stationery", "Local library", 12.0, "New", False
    )
    assert purchases == [item]
    assert item["co2_kg"] == pytest.approx(1.8)
    with pytest.raises(ValueError, match="brand"):
        lg.add_purchase(purchases, 2, TODAY, "Clothing", "", 20.0)
    assert len(purchases) == 1


def test_zero_price_is_zero_impact():
    assert lg.calculate_impact("Smartphone", 0)["co2_kg"] == 0
    assert lg.rate_impact(0, 0) == "Low"


@pytest.mark.parametrize(
    "brand,expected",
    [
        ("Patagonia", True),
        ("patagonia ", True),
        ("Thrift store", True),
        ("Local farmers market stall", True),
        ("Fast Fashion Co", False),
        ("", False),
        (None, False),
    ],
)
def test_curated_brand_name_matching(brand, expected):
    assert lg.matches_curated_brand(brand) is expected


def test_rating_thresholds():
    assert lg.rate_impact(25, 100) == "Low"  # 0.25 -> boundary is Low
    assert lg.rate_impact(40, 100) == "Medium"
    assert lg.rate_impact(95, 100) == "High"


def test_every_product_has_complete_data():
    for name, info in lg.PRODUCTS.items():
        assert info["multiplier"] > 0, name
        assert info["brands"] and info["alternatives"], name


# ------------------------------------------------------------ monthly summaries
def test_monthly_summary_only_counts_that_month():
    last_month = dt.date(2026, 9, 10)
    data = [buy(1, "Clothing", 100), buy(2, "Clothing", 100, date=last_month)]
    s = lg.monthly_summary(data, (2026, 10))
    assert s["n"] == 1 and s["spend_usd"] == 100 and s["co2_kg"] == pytest.approx(55)


def test_month_index_matches_monthly_helpers_and_keeps_purchase_order():
    purchases = [
        buy(1, "Clothing", 10, date=dt.date(2026, 9, 15)),
        buy(2, "Books & Stationery", 20, date=dt.date(2026, 10, 2)),
        buy(3, "Clothing", 30, date=dt.date(2026, 9, 20)),
    ]
    index = lg.build_month_index(purchases)

    assert [item["id"] for item in index[(2026, 9)]] == [1, 3]
    assert lg.monthly_summary(purchases, (2026, 9), index) == lg.monthly_summary(
        purchases, (2026, 9)
    )
    assert lg.monthly_totals(purchases, index) == lg.monthly_totals(purchases)
    assert lg.goal_streak(purchases, 1000, (2026, 10), index) == lg.goal_streak(
        purchases, 1000, (2026, 10)
    )


def test_previous_month_wraps_over_new_year():
    assert lg.previous_month((2026, 1)) == (2025, 12)
    assert lg.previous_month((2026, 10)) == (2026, 9)


def test_empty_month_does_not_crash():
    s = lg.monthly_summary([], (2026, 10))
    assert s["n"] == 0 and s["co2_kg"] == 0 and s["intensity"] == 0
    assert s["average_co2_kg"] == 0 and s["by_category"] == {}


def test_monthly_summary_includes_average_and_spending_by_category():
    data = [
        buy(1, "Books & Stationery", 10),
        buy(2, "Books & Stationery", 30),
        buy(3, "Clothing", 20),
    ]
    s = lg.monthly_summary(data, (2026, 10))
    assert s["average_co2_kg"] == pytest.approx(6.33, abs=0.01)
    assert s["by_category"]["Books & Stationery"] == {
        "spend_usd": 40.0,
        "co2_kg": 8.0,
        "count": 2,
    }
    assert s["by_category"]["Clothing"]["spend_usd"] == 20.0


def test_monthly_insights_are_deterministic_and_silent_without_enough_data():
    assert lg.monthly_insights([], (2026, 10)) == []
    september = dt.date(2026, 9, 10)
    october = dt.date(2026, 10, 10)
    data = [
        buy(1, "Clothing", 10, date=september),
        buy(2, "Clothing", 10, cond="Second-hand", date=october),
    ]

    first = lg.monthly_insights(data, (2026, 10))

    assert first == lg.monthly_insights(data, (2026, 10))
    assert any("lower than last month" in insight for insight in first)
    assert any(
        "Second-hand" in insight and "illustrative model" in insight
        for insight in first
    )
    assert any("October 2026" in insight for insight in first)


def test_monthly_insights_are_identical_across_purchase_orderings():
    september = dt.date(2026, 9, 10)
    october = dt.date(2026, 10, 10)
    data = [
        buy(1, "Clothing", 5, date=september),
        buy(2, "Books & Stationery", 13.75, date=september),
        buy(3, "Clothing", 10, date=october),
        buy(4, "Books & Stationery", 27.5, date=october),
    ]

    outputs = [
        lg.monthly_insights(ordering, (2026, 10))
        for ordering in permutations(data)
    ]

    assert all(output == outputs[0] for output in outputs)
    assert outputs[0][0].startswith("Estimated books & stationery impact")


def test_monthly_insights_describe_zero_change_as_about_the_same():
    september = dt.date(2026, 9, 10)
    october = dt.date(2026, 10, 10)
    data = [
        buy(1, "Clothing", 10, date=september),
        buy(2, "Clothing", 10, date=october),
    ]

    insights = lg.monthly_insights(data, (2026, 10))

    assert insights[0] == "Your estimated impact was about the same as last month."


def test_monthly_insights_add_neutral_want_share_only_after_three_tagged_purchases():
    purchases = [
        buy(index, "Books & Stationery", 10, date=TODAY)
        for index in range(1, 4)
    ]
    purchases[0]["intent"] = "Need"
    purchases[1]["intent"] = "Want"

    assert not any(
        "tagged as wants" in insight
        for insight in lg.monthly_insights(purchases, (2026, 10))
    )

    purchases[2]["intent"] = "Gift"
    insights = lg.monthly_insights(purchases, (2026, 10))
    want_insights = [
        insight for insight in insights if "tagged as wants" in insight
    ]
    assert want_insights == [
        (
            "About 33% of this month's estimated footprint came from "
            "purchases you tagged as wants."
        )
    ]
    assert not any(word in want_insights[0].lower() for word in ("failure", "failed"))


def test_goal_streak_counts_consecutive_logged_months_under_goal():
    august = dt.date(2026, 8, 10)
    september = dt.date(2026, 9, 10)
    october = dt.date(2026, 10, 10)
    data = [
        buy(1, "Leather Shoes", 100, date=august),
        buy(2, "Books & Stationery", 10, date=september),
        buy(3, "Books & Stationery", 10, date=october),
    ]

    assert lg.goal_streak(data, 10, (2026, 10)) == 2
    assert lg.goal_streak(data, 10, (2026, 8)) == 0


def test_goal_for_month_uses_latest_applicable_history_entry():
    history = [
        {"from_month": (2026, 10), "goal_kg": 40},
        {"from_month": (2026, 8), "goal_kg": 80},
    ]

    assert lg.goal_for_month(history, (2026, 7), 100) == 100
    assert lg.goal_for_month(history, (2026, 8), 100) == 80
    assert lg.goal_for_month(history, (2026, 9), 100) == 80
    assert lg.goal_for_month(history, (2026, 10), 100) == 40
    assert lg.goal_for_month([], (2026, 10), 60) == 60


def test_goal_streak_uses_the_goal_active_in_each_month():
    data = [
        buy(1, "Leather Shoes", 100, date=dt.date(2026, 8, 10)),
        buy(2, "Leather Shoes", 100, date=dt.date(2026, 9, 10)),
        buy(3, "Leather Shoes", 100, date=dt.date(2026, 10, 10)),
    ]
    history = [
        {"from_month": (2026, 8), "goal_kg": 100},
        {"from_month": (2026, 9), "goal_kg": 90},
        {"from_month": (2026, 10), "goal_kg": 100},
    ]

    assert lg.goal_streak(data, 100, (2026, 10), goal_history=history) == 1


@pytest.mark.parametrize(
    ("monthly_values", "expected"),
    [
        ([50, 55], {"Same as my average": 55, "10% lower": 45, "20% lower": 40}),
        ([10, 15], {"Same as my average": 20, "10% lower": 20, "20% lower": 20}),
        ([450, 455], {"Same as my average": 300, "10% lower": 300, "20% lower": 300}),
    ],
)
def test_suggested_goal_presets_round_and_clamp(monthly_values, expected):
    purchases = [
        {
            "date": dt.date(2026, month, 1),
            "product_type": "Clothing",
            "price_usd": 100.0,
            "co2_kg": value,
        }
        for month, value in zip((8, 9, 10), monthly_values)
    ]

    result = lg.suggested_goal_presets(purchases)

    assert result is not None
    assert result[1] == expected


def test_suggested_goal_presets_require_two_logged_months():
    assert lg.suggested_goal_presets([]) is None
    assert lg.suggested_goal_presets(
        [{"date": dt.date(2026, 10, 1), "product_type": "Clothing",
          "price_usd": 10, "co2_kg": 5}]
    ) is None


def test_swap_savings_summarizes_positive_swap_rows_in_selected_month():
    purchases = [
        {
            **buy(1, "Clothing", 10, date=dt.date(2026, 10, 1)),
            "source": "swap",
            "swap_saved_kg": 3.2,
        },
        {
            **buy(2, "Clothing", 10, date=dt.date(2026, 10, 2)),
            "source": "swap",
            "swap_saved_kg": 0,
        },
        {
            **buy(3, "Clothing", 10, date=dt.date(2026, 9, 2)),
            "source": "swap",
            "swap_saved_kg": 5.0,
        },
        {
            **buy(4, "Clothing", 10, date=dt.date(2026, 10, 3)),
            "source": "user",
            "swap_saved_kg": 8.0,
        },
    ]

    savings = lg.swap_savings(purchases, (2026, 10))

    assert savings == {
        "count": 1,
        "saved_kg": 3.2,
        "saved_equivalents": lg.equivalents(3.2),
    }


def test_peak_highlights_surface_the_best_and_biggest_items_for_the_month():
    data = [
        buy(1, "Clothing", 100),
        buy(2, "Books & Stationery", 10),
        buy(3, "Clothing", 20),
    ]
    highlights = lg.peak_highlights(data, (2026, 10), 80)

    assert highlights["best_choice"]["label"].startswith("Books & Stationery")
    assert highlights["best_choice"]["co2_kg"] == pytest.approx(2.0)
    assert highlights["top_category"]["category"] == "Clothing"
    assert highlights["goal_status"]["met"] is True


def test_month_momentum_labels_improvement_relative_to_last_month():
    august = dt.date(2026, 8, 10)
    september = dt.date(2026, 9, 10)
    october = dt.date(2026, 10, 10)
    data = [
        buy(1, "Leather Shoes", 100, date=august),
        buy(2, "Leather Shoes", 100, date=september),
        buy(3, "Books & Stationery", 10, date=october),
    ]
    trend = lg.month_momentum(data, (2026, 10))

    assert trend["direction"] == "improving"
    assert trend["delta_kg"] < 0
    assert "lower" in trend["status"]


def test_daily_tip_is_stable_category_aware_and_rotates():
    day = dt.date(2026, 10, 15)
    first = lg.tip_of_day("Clothing", day)
    assert first == lg.tip_of_day("Clothing", day)
    assert first != lg.tip_of_day("Clothing", day, offset=1, previous_tip=first)
    assert lg.tip_of_day("Clothing", day) in lg.CATEGORY_TIPS["Clothing"]
    assert lg.tip_of_day("Smartphone", day) in lg.CATEGORY_TIPS["Smartphone"]


# ----------------------------------------------------------------------- badges
def earned(data, goal=80):
    return lg.earned_badge_ids(data, (2026, 10), goal)


def test_first_step_badge():
    assert "first_step" not in earned([])
    assert "first_step" in earned([buy(1, "Books & Stationery", 10)])
    badge = next(
        b
        for b in lg.evaluate_badges([buy(1, "Books & Stationery", 10)], (2026, 10), 80)
        if b["id"] == "first_step"
    )
    assert "at least one purchase" in badge["reason"]


def test_low_impact_needs_three_purchases_and_under_goal():
    two = [buy(1, "Books & Stationery", 10), buy(2, "Books & Stationery", 10)]
    three = two + [buy(3, "Books & Stationery", 10)]
    assert "low_impact" not in earned(two)
    assert "low_impact" in earned(three)
    assert "low_impact" not in earned(three, goal=3)  # 6 kg > 3 kg goal


def test_swaps_chosen_badge_requires_three_positive_swap_rows():
    swaps = []
    for index in range(3):
        purchase = buy(
            index + 1,
            "Clothing",
            10,
            date=dt.date(2026, 10, index + 1),
        )
        purchase.update({"source": "swap", "swap_saved_kg": 1.0})
        swaps.append(purchase)

    badge = next(
        badge
        for badge in lg.evaluate_badges(swaps, (2026, 10), 80)
        if badge["id"] == "swaps_chosen"
    )

    assert badge["earned"] is True


def test_eco_saver_requires_low_average_intensity():
    green = [buy(i, "Clothing", 30, "Thrift store", "Second-hand") for i in range(1, 4)]
    heavy = [buy(i, "Leather Shoes", 30) for i in range(1, 4)]
    assert "eco_saver" in earned(green)
    assert "eco_saver" not in earned(heavy)


def test_second_life_and_curated_list_badges_need_two():
    one = [buy(1, "Smartphone", 100, "Fairphone", "Refurbished")]
    two = one + [buy(2, "Clothing", 20, "Patagonia", "Second-hand")]
    assert "second_life" not in earned(one) and "curated_list" not in earned(one)
    assert "second_life" in earned(two) and "curated_list" in earned(two)


def test_plant_powered_is_blocked_by_meat():
    plant = [
        buy(1, "Groceries - Plant-based", 20),
        buy(2, "Groceries - Plant-based", 20),
    ]
    assert "plant" in earned(plant)
    assert "plant" not in earned(plant + [buy(3, "Groceries - Meat & Dairy", 10)])


def test_footprint_shrinker_compares_with_last_month():
    sept = dt.date(2026, 9, 12)
    lower = [buy(1, "Leather Shoes", 100, date=sept), buy(2, "Books & Stationery", 10)]
    higher = [buy(1, "Books & Stationery", 10, date=sept), buy(2, "Leather Shoes", 100)]
    assert "shrinker" in earned(lower)
    assert "shrinker" not in earned(higher)
    assert "shrinker" not in earned([buy(1, "Books & Stationery", 10)])  # no last month


# ----------------------------------------------------------------- suggestions
def test_what_if_savings_are_positive_and_sorted():
    alts = lg.suggest_alternatives("Clothing", "Fast Fashion Co", 100)
    savings = [w["saved_kg"] for w in alts["what_if"]]
    assert savings and all(s > 0 for s in savings)
    assert savings == sorted(savings, reverse=True)
    assert alts["what_if"][0]["label"] == "Buy it second-hand"


def test_phone_suggests_refurbished_not_second_hand():
    labels = [
        w["label"]
        for w in lg.suggest_alternatives("Smartphone", "Brandx", 400)["what_if"]
    ]
    assert "Buy it refurbished" in labels and "Buy it second-hand" not in labels


def test_meat_suggests_plant_swap():
    labels = [
        w["label"]
        for w in lg.suggest_alternatives("Groceries - Meat & Dairy", "Tesco", 60)[
            "what_if"
        ]
    ]
    assert any("plant-based" in label for label in labels)


def test_greenest_choice_has_no_what_if():
    best = lg.suggest_alternatives(
        "Books & Stationery", "Local library", 10, "Second-hand", True
    )
    assert best["what_if"] == []


def test_category_tip_is_relevant_and_avoids_immediate_repeat():
    import random

    rng = random.Random(4)
    first = lg.generate_eco_tip("Smartphone", rng=rng)
    second = lg.generate_eco_tip("Smartphone", previous_tip=first, rng=rng)
    assert first in lg.CATEGORY_TIPS["Smartphone"]
    assert second in lg.CATEGORY_TIPS["Smartphone"]
    assert second != first


# ------------------------------------------------------------------- demo data
def test_demo_data_has_15_purchases_over_three_months_and_no_future_dates():
    demo = lg.demo_purchases(TODAY)
    assert len(demo) == 15
    assert len({lg.month_of(p["date"]) for p in demo}) == 3
    assert all(p["date"] <= TODAY for p in demo)
