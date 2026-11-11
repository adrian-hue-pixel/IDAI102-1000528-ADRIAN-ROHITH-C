"""Constraint, reproducibility and model interpretation checks for Impact Lab."""

import copy
import datetime as dt
import itertools
import json

import pytest

import impact_lab as lab
import logic as lg


def purchase(index, product="Clothing", price=100, condition="New", packaging=False, date=dt.date(2026, 1, 5), **extras):
    item = lg.make_purchase(index, date, product, "Local shop", price, condition, packaging, today=dt.date(2026, 11, 11))
    item.update(extras)
    return item


def test_plan_obeys_limit_and_never_combines_actions_for_one_purchase():
    items = [purchase(1), purchase(2, "Smartphone", 250), purchase(3, "Groceries - Meat & Dairy", 80)]
    original = copy.deepcopy(items)
    plan = lab.action_plan(items, 2)
    assert len(plan["changes"]) == 2
    assert len({row["purchase_id"] for row in plan["changes"]}) == 2
    assert plan["projected_kg"] >= 0
    assert plan["baseline_kg"] - plan["projected_kg"] == pytest.approx(plan["difference_kg"])
    assert items == original


def test_plan_is_optimal_against_exhaustive_independent_options():
    items = [purchase(1), purchase(2, "Smartphone", 250), purchase(3, "Groceries - Meat & Dairy", 80)]
    possibilities = []
    for item in items:
        options = lg.suggest_alternatives(item["product_type"], item["brand"], item["price_usd"], item["condition"], item["low_packaging"])["what_if"]
        options = [option for option in options if option["kind"] != "brand"]
        baseline = lg.calculate_impact(item["product_type"], item["price_usd"], item["condition"], item["brand"], item["low_packaging"])["co2_kg"]
        possibilities.append([0, *(baseline - option["co2_kg"] for option in options)])
    best = max(sum(combination) for combination in itertools.product(*possibilities) if sum(value > 0 for value in combination) <= 2)
    assert lab.action_plan(items, 2)["difference_kg"] == pytest.approx(best, abs=.001)


def test_zero_changes_keeps_baseline_and_larger_limit_is_monotonic():
    items = [purchase(1), purchase(2)]
    plans = [lab.action_plan(items, count) for count in (0, 1, 2, 10)]
    assert plans[0]["changes"] == []
    assert plans[0]["baseline_kg"] == plans[0]["projected_kg"]
    assert [plan["difference_kg"] for plan in plans] == sorted(plan["difference_kg"] for plan in plans)
    assert plans[-1]["difference_kg"] == plans[-2]["difference_kg"]


def test_plan_recomputes_old_saved_estimates_and_excludes_brand_name_only_changes():
    item = purchase(1, "Clothing", condition="Second-hand", packaging=True)
    item["co2_kg"] = 999
    plan = lab.action_plan([item], 10)
    assert plan["baseline_kg"] == lg.calculate_impact("Clothing", 100, "Second-hand", "Local shop", True)["co2_kg"]
    assert plan["changes"] == []


@pytest.mark.parametrize("limit", [-1, 1.5, True, "2"])
def test_plan_rejects_invalid_limits(limit):
    with pytest.raises(ValueError, match="non-negative integer"):
        lab.action_plan([], limit)


def test_plan_rejects_duplicate_ids_instead_of_double_counting():
    with pytest.raises(ValueError, match="unique"):
        lab.action_plan([purchase(1), purchase(1)], 2)


def test_empty_plan_and_coverage_are_meaningful():
    assert lab.action_plan([], 2)["projected_kg"] == 0
    result = lab.journal_coverage([])
    assert result["purchases"] == result["intent_coverage_pct"] == 0
    assert result["first_date"] is None
    assert result["missing_months"] == []


def test_model_scenarios_vary_only_one_assumption_and_explain_factors():
    result = lab.model_experiment("Clothing", 100, "New", "Local shop", False, .3)
    rows = {row["scenario"]: row for row in result["scenarios"]}
    assert result["factors"]["co2_kg"] == 55
    assert rows["Condition: Second-hand"]["estimate_kg"] == 11
    assert rows["Packaging: minimal"]["estimate_kg"] == 49.5
    assert rows["Price −25%"]["estimate_kg"] == 41.25
    assert result["range_kg"] == [38.5, 71.5]
    assert "Condition: Refurbished" not in rows


def test_price_sensitivity_stays_inside_model_price_bound():
    result = lab.model_experiment("Smartphone", lg.MAX_PRICE_USD, "New", "Local shop", False)
    plus = next(row for row in result["scenarios"] if row["scenario"].startswith("Price +25%"))
    assert plus["estimate_kg"] == result["factors"]["co2_kg"]


def test_coverage_separates_demo_sources_and_reports_missing_months_across_year():
    items = [
        purchase(1, date=dt.date(2025, 12, 5), intent="Need", source="demo"),
        purchase(2, date=dt.date(2026, 2, 5), intent="Want"),
        purchase(3, date=dt.date(2026, 2, 5), recurring=True),
    ]
    result = lab.journal_coverage(items)
    assert result["purchase_dates"] == 2
    assert result["months"] == 2
    assert result["missing_months"] == ["2026-01"]
    assert result["intent_coverage_pct"] == 66.7
    assert result["sources"] == {"demo": 1, "recurring": 1, "user": 1}


def test_export_is_reproducible_month_scoped_and_excludes_notes():
    items = [purchase(1, note="Private note", source="demo"), purchase(2, date=dt.date(2026, 2, 5))]
    original = copy.deepcopy(items)
    created = dt.datetime(2026, 11, 11, 12, tzinfo=dt.timezone.utc)
    text = lab.export_experiment(items, (2026, 1), 2, .3, created)
    document = json.loads(text)
    assert text == lab.export_experiment(items, (2026, 1), 2, .3, created)
    assert document["model_version"] == lg.MODEL_VERSION
    assert len(document["inputs"]) == 1
    assert document["inputs"][0]["source"] == "demo"
    assert "Private note" not in text
    assert document["inputs"][0]["model_factors"]["co2_kg"] == document["plan"]["baseline_kg"]
    assert "not measured savings" in document["limits"]
    assert items == original


def test_export_requires_a_timezone_and_valid_model_range():
    with pytest.raises(ValueError, match="timezone"):
        lab.export_experiment([], (2026, 1), 2, .3, dt.datetime(2026, 11, 11, tzinfo=None))  # noqa: DTZ001 — deliberately invalid input
    with pytest.raises(ValueError, match="band"):
        lab.export_experiment([], (2026, 1), 2, .9, dt.datetime.now(dt.timezone.utc))


def test_brand_exclusion_does_not_depend_on_display_wording(monkeypatch):
    original = lg.suggest_alternatives
    def renamed(*args, **kwargs):
        result = original(*args, **kwargs)
        for option in result["what_if"]:
            option["label"] = "Research an alternative"
        return result
    monkeypatch.setattr(lg, "suggest_alternatives", renamed)
    item = purchase(1, condition="Second-hand", packaging=True)
    assert lab.action_plan([item], 3)["changes"] == []
