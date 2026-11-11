"""Independent arithmetic, source integrity, exact replay and optimality checks."""

import hashlib
import itertools
import json
import random
from importlib.resources import files

import pytest
from shopimpact_core import (
    comparison,
    counterexample,
    estimate,
    factors,
    monthly,
    optimize,
    references,
)
from shopimpact_core.classifier import DATA, evaluate, predict
from shopimpact_core.lifecycle import break_even, lifespan
from shopimpact_core.model import manifest, replay, replay_export
from shopimpact_core.planner import cents


def test_factor_matches_pinned_raw_epa_dataset():
    import csv

    raw = files("shopimpact_core").joinpath("data", "epa_v1.3_usd2022.csv").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest()["epa_sha256"]
    rows = {r["2017 NAICS Code"]: r for r in csv.DictReader(raw.decode().splitlines())}
    for group in factors().values():
        for r in group:
            assert r["value"] == float(
                rows[r["code"]]["Supply Chain Emission Factors with Margins"]
            )
            assert (
                r["region"] == "US"
                and r["price_year"] == 2022
                and r["source"].startswith("https://doi.org/")
            )


def test_price_year_normalization_and_no_fake_discounts():
    expected = 799 * 292.655 / 304.702 * 0.111
    assert estimate("Smartphone", 799, price_year=2023)["point"] == pytest.approx(
        expected
    )
    assert estimate("Clothing", 100)["point"] == 12


@pytest.mark.parametrize(
    "region,currency", [("IN", "INR"), ("EU", "EUR"), ("US", "INR")]
)
def test_unsupported_region_fails_closed(region, currency):
    with pytest.raises(ValueError, match="No validated"):
        estimate("Smartphone", 100, region, currency)


@pytest.mark.parametrize("amount", [-1, float("nan"), float("inf"), True])
def test_nonfinite_or_negative_spend_is_rejected(amount):
    with pytest.raises(ValueError):
        estimate("Clothing", amount)


def test_point_source_has_no_invented_uncertainty():
    r = estimate("Smartphone", 100)
    assert r["p05"] == r["p95"] == 11.1
    assert (
        not r["mapping_spread_available"] and not r["parameter_uncertainty_available"]
    )


def test_mc_samples_come_only_from_unique_source_factors():
    r = estimate("Furniture", 100, seed=7)
    valid = {100 * x["value"] for x in r["source_rows"]}
    assert set(r["samples"]) <= valid
    assert r["p05"] < r["p95"]
    assert r == estimate("Furniture", 100, seed=7)


def record(amount, category="Furniture"):
    return {
        "category": category,
        "amount": amount,
        "region": "US",
        "currency": "USD",
        "price_year": 2022,
    }


def test_monthly_resampling_preserves_within_category_correlation():
    one = monthly([record(100)], seed=3)
    split = monthly([record(40), record(60)], seed=3)
    assert one["samples"] == split["samples"]


def test_replay_exact_and_tamper_or_version_fail():
    text = replay_export({"category": "Furniture", "amount": 100, "seed": 17})
    assert replay(text) == json.loads(text)
    data = json.loads(text)
    data["results"]["mean"] += 1
    with pytest.raises(ValueError, match="differ"):
        replay(json.dumps(data))
    data = json.loads(text)
    data["dataset_sha256"] = "wrong"
    with pytest.raises(ValueError, match="Incompatible"):
        replay(json.dumps(data))


def test_dp_beats_greedy_in_proven_counterexample():
    r = counterexample()
    assert r["greedy"]["kg"] == 12 and r["dp"]["kg"] == 18
    assert r["dp"]["ids"] == ["B", "C"]


def test_grouped_dp_matches_bruteforce_on_random_small_instances():
    rng = random.Random(5)
    for _ in range(30):
        actions = [
            {
                "id": str(i),
                "group": str(i // 2),
                "cost": rng.randint(0, 9),
                "kg": rng.randint(0, 20),
                "feasibility": rng.choice([0, 0.5, 1]),
            }
            for i in range(8)
        ]
        eligible = [a for a in actions if a["feasibility"] >= 0.5]
        candidates = []
        for count in range(4):
            for subset in itertools.combinations(eligible, count):
                if (
                    sum(a["cost"] for a in subset) <= 12
                    and len({a["group"] for a in subset}) == count
                ):
                    candidates.append(sum(a["kg"] for a in subset))
        r = optimize(actions, 12, 3, 0.5)
        assert r["kg"] == max(candidates)
        assert r["cost"] <= 12
        frontier = r["frontier"]
        assert all(
            a["cost"] < b["cost"] and a["kg"] < b["kg"]
            for a, b in itertools.pairwise(frontier)
        )


@pytest.mark.parametrize("value", [-1, 0.001, float("nan"), None])
def test_costs_cannot_be_silently_rounded(value):
    with pytest.raises((ValueError, TypeError)):
        cents(value)


def test_classifier_holdout_is_disjoint_and_oov_abstains():
    for train, test in DATA.values():
        assert not set(train) & set(test)
    assert predict("zzzzzz 123 total gst")["abstained"]
    r = evaluate()
    assert r["test_n"] == 28 and all(
        0 <= m["precision"] <= 1 and 0 <= m["recall"] <= 1 for m in r["metrics"]
    )
    assert not predict("cotton shirt")["calibrated"]


def test_local_corrections_change_model_hash_without_changing_benchmark():
    before = evaluate()
    correction = [{"text": "specialwidget", "category": "Smartphone"}]
    assert predict("specialwidget", correction)["category"] == "Smartphone"
    assert (
        predict("specialwidget", correction)["model_hash"]
        != predict("specialwidget")["model_hash"]
    )
    assert evaluate() == before


def test_lifespan_and_keep_replace_are_explicit_assumptions():
    assert lifespan(100, 1000, 5, 100) == {"kg_per_year": 20, "cost_per_use": 2}
    assert break_even(100, 100, 50, 0.5)["years"] == 4
    assert break_even(100, 50, 100, 0.5)["years"] is None
    with pytest.raises(ValueError):
        lifespan(1, 1, 0, 1)


def test_pilot_signs_are_reproduced_not_hardcoded():
    rows = list(map(comparison, references()))
    assert len(rows) == 3
    assert rows[0]["relative_difference_pct"] > 50
    assert rows[2]["relative_difference_pct"] < -50
    assert all("boundaries differ" in r["boundary_warning"] for r in rows)


def test_monthly_cpi_matches_pinned_bls_response_and_affects_dataset_hash():
    from shopimpact_core.model import CPI, load

    snapshot = load("cpi.json")
    raw = files("shopimpact_core").joinpath("data", "bls_response.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == snapshot["raw_sha256"]
    for row in json.loads(raw)["Results"]["series"][0]["data"]:
        if (
            row["period"].startswith("M")
            and row["period"] != "M13"
            and row["value"] != "-"
        ):
            period = row["year"] + "-" + row["period"][1:]
            assert CPI[period] == float(row["value"])
    period = max(snapshot["periods"])
    result = estimate("Clothing", 100, price_year=period)
    assert result["point"] == pytest.approx(100 * CPI[2022] / CPI[period] * 0.12)
    content = b"".join(
        files("shopimpact_core").joinpath("data", name).read_bytes()
        for name in [
            "factors.json",
            "products.json",
            "epa_v1.3_usd2022.csv",
            "cpi.json",
        ]
    )
    assert manifest()["dataset_sha256"] == hashlib.sha256(content).hexdigest()
