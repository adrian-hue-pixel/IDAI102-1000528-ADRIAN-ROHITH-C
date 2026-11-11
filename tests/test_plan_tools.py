"""Tests for plans and what-if projections based on the illustrative estimator."""

import datetime as dt

import pytest

import logic as lg
import plan_tools as pt


def make_plan(
    product_type="Clothing",
    brand="Local shop",
    price=100.0,
    condition="New",
    minimal_packaging=False,
):
    return pt.create_plan(
        "plan-1",
        product_type,
        brand,
        price,
        condition,
        minimal_packaging,
        dt.date(2026, 10, 8),
    )


def test_plan_estimate_matches_existing_model_without_creating_a_purchase():
    plan = make_plan()

    assert (
        plan["co2_kg"]
        == lg.calculate_impact("Clothing", 100, "New", "Local shop", False)["co2_kg"]
    )
    assert plan["plan_id"] == "plan-1"
    assert "id" not in plan


def test_plan_requires_valid_existing_purchase_inputs():
    with pytest.raises(ValueError, match="brand"):
        make_plan(brand="")


def test_bought_plan_becomes_a_purchase_with_its_existing_estimate():
    plan = make_plan()

    purchase = pt.bought_purchase(plan, purchase_id=7)

    assert purchase["id"] == 7
    assert purchase["co2_kg"] == plan["co2_kg"]
    assert purchase["source"] == "user"
    assert purchase["recurring"] is False


@pytest.mark.parametrize(
    ("category", "condition", "alternative", "expected_category", "expected_choice"),
    [
        ("Clothing", "New", "Buy it second-hand", "Clothing", "Second-hand"),
        (
            "Smartphone",
            "New",
            "Buy it refurbished",
            "Smartphone",
            "Refurbished",
        ),
        (
            "Clothing",
            "New",
            "Pick plastic-free / minimal packaging",
            "Clothing",
            "minimal",
        ),
        (
            "Groceries - Meat & Dairy",
            "New",
            "Swap this shop for plant-based groceries",
            "Groceries - Plant-based",
            "New",
        ),
    ],
)
def test_swapped_plan_logs_the_selected_supported_alternative(
    category, condition, alternative, expected_category, expected_choice
):
    plan = make_plan(product_type=category, condition=condition)

    purchase = pt.swapped_purchase(plan, alternative, purchase_id=3)

    assert purchase["product_type"] == expected_category
    if expected_choice == "minimal":
        assert purchase["low_packaging"] is True
    else:
        assert purchase["condition"] == expected_choice
    assert purchase["id"] == 3
    assert purchase["source"] == "swap"
    assert purchase["swap_from_label"] == alternative
    assert purchase["swap_original_co2_kg"] == plan["co2_kg"]
    assert purchase["swap_original_price_usd"] == plan["price_usd"]
    assert purchase["swap_saved_kg"] == pytest.approx(
        max(0, plan["co2_kg"] - purchase["co2_kg"])
    )


def test_swapped_plan_rejects_an_unknown_alternative():
    with pytest.raises(ValueError, match="available for this plan"):
        pt.swapped_purchase(make_plan(), "Not a model option", 1)


def test_swap_saved_estimate_never_goes_below_zero():
    plan = make_plan(product_type="Books & Stationery", condition="Second-hand")
    plan["co2_kg"] = 0

    purchase = pt.swapped_purchase(
        plan,
        "Pick plastic-free / minimal packaging",
        purchase_id=8,
    )

    assert purchase["swap_saved_kg"] == 0


def test_what_if_is_deterministic_and_does_not_mutate_purchase_results():
    purchases = [
        lg.make_purchase(
            1, dt.date(2026, 10, 1), "Clothing", "Local shop", 100, "New", False
        ),
        lg.make_purchase(
            2,
            dt.date(2026, 10, 2),
            "Books & Stationery",
            "Library",
            20,
            "New",
            False,
        ),
    ]
    original_estimates = [purchase["co2_kg"] for purchase in purchases]

    baseline = pt.what_if_savings(purchases, 0, False)
    scenario = pt.what_if_savings(purchases, 50, True)

    assert baseline["saved_kg"] == 0
    assert scenario["projected_kg"] < scenario["baseline_kg"]
    assert scenario["saved_kg"] > 0
    assert scenario["clothing_saved_kg"] > 0
    assert scenario["packaging_saved_kg"] > 0
    assert [purchase["co2_kg"] for purchase in purchases] == original_estimates


def test_what_if_rejects_percentages_outside_slider_range():
    with pytest.raises(ValueError, match="between 0 and 100"):
        pt.what_if_savings([], 101, False)


def test_forecast_scales_with_remaining_days_and_validates_day():
    assert pt.forecast_month_end(31, 10, 31) == 96.1
    with pytest.raises(ValueError, match="day must be valid"):
        pt.forecast_month_end(31, 32, 31)
