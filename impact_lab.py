"""Reproducible, non-mutating experiments over the illustrative model."""

import datetime as dt
import json
from collections import Counter
from collections.abc import Sequence
from typing import Any

import logic as lg


def action_plan(purchases: Sequence[dict[str, Any]], max_changes: int) -> dict[str, Any]:
    """Pick independent alternatives with at most one change per purchase.

    Brand-name reductions are excluded: a name is not evidence of real impact.
    Recompute baseline with the current model so old estimates are not mixed.
    """
    if isinstance(max_changes, bool) or not isinstance(max_changes, int) or max_changes < 0:
        raise ValueError("Maximum changes must be a non-negative integer.")
    ids = [purchase["id"] for purchase in purchases]
    if len(ids) != len(set(ids)):
        raise ValueError("Purchase IDs must be unique for a reproducible plan.")
    candidates = []
    baseline = 0.0
    for purchase in purchases:
        current = lg.calculate_impact(
            purchase["product_type"], purchase["price_usd"], purchase["condition"],
            purchase["brand"], purchase["low_packaging"],
        )["co2_kg"]
        baseline += current
        options = lg.suggest_alternatives(
            purchase["product_type"], purchase["brand"], purchase["price_usd"],
            purchase["condition"], purchase["low_packaging"],
        )["what_if"]
        options = [option for option in options if option["kind"] != "brand"]
        if not options:
            continue
        best = max(options, key=lambda option: (option["saved_kg"], option["label"]))
        # Alternative outputs are rounded; reconcile the displayed arithmetic.
        projected = min(current, float(best["co2_kg"]))
        difference = max(0.0, current - projected)
        if difference <= 0.005:
            continue
        candidates.append({
            "purchase_id": purchase["id"], "product_type": purchase["product_type"],
            "brand": purchase["brand"], "action": best["label"],
            "baseline_kg": round(current, 3), "projected_kg": round(projected, 3),
            "difference_kg": round(difference, 3),
        })
    candidates.sort(key=lambda candidate: (-candidate["difference_kg"], str(candidate["purchase_id"])))
    selected = candidates[:max_changes]
    difference = sum(candidate["difference_kg"] for candidate in selected)
    return {
        "baseline_kg": round(baseline, 3),
        "projected_kg": round(max(0.0, baseline - difference), 3),
        "difference_kg": round(difference, 3), "changes": selected,
        "eligible_purchases": len(candidates), "max_changes": max_changes,
    }


def model_experiment(
    product_type: str, price_usd: float, condition: str, brand: str,
    low_packaging: bool, band: float = lg.DEFAULT_UNCERTAINTY,
) -> dict[str, Any]:
    """Explain a baseline and vary one input at a time, without stacking effects."""
    factors = lg.calculate_impact(product_type, price_usd, condition, brand, low_packaging)
    low, high = lg.estimate_range(factors["co2_kg"], band)
    rows = []

    def add(label: str, *, price=price_usd, selected_condition=condition, packaging=low_packaging):
        value = lg.calculate_impact(product_type, price, selected_condition, brand, packaging)["co2_kg"]
        rows.append({"scenario": label, "estimate_kg": value, "difference_kg": round(value - factors["co2_kg"], 3)})

    add("Baseline")
    add("Price −25%", price=price_usd * .75)
    add("Price +25%" if price_usd * 1.25 <= lg.MAX_PRICE_USD else "Price +25% (capped at model limit)", price=min(lg.MAX_PRICE_USD, price_usd * 1.25))
    for choice in lg.CONDITION_FACTORS:
        allowed = choice == "New" or (choice == "Second-hand" and lg.PRODUCTS[product_type]["second_hand"]) or (choice == "Refurbished" and lg.PRODUCTS[product_type]["refurbished"])
        if allowed and choice != condition:
            add(f"Condition: {choice}", selected_condition=choice)
    add("Packaging: standard" if low_packaging else "Packaging: minimal", packaging=not low_packaging)
    return {"factors": factors, "range_kg": [low, high], "band": band, "scenarios": rows}


def journal_coverage(purchases: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Describe entered coverage, never completeness or estimation accuracy."""
    dates = [item["date"].date() if isinstance(item["date"], dt.datetime) else item["date"] for item in purchases]
    sources = Counter(item.get("source") or ("recurring" if item.get("recurring") else "user") for item in purchases)
    tagged = sum(item.get("intent") in lg.INTENTS for item in purchases)
    categories = sorted({item["product_type"] for item in purchases})
    months = sorted({lg.month_of(date) for date in dates})
    missing = []
    if months:
        year, month = months[0]
        end = months[-1]
        observed = set(months)
        while (year, month) <= end:
            if (year, month) not in observed:
                missing.append(f"{year:04d}-{month:02d}")
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return {
        "purchases": len(purchases), "purchase_dates": len(set(dates)),
        "months": len(months), "categories": categories,
        "tagged_intents": tagged, "untagged_intents": len(purchases) - tagged,
        "intent_coverage_pct": round(tagged / len(purchases) * 100, 1) if purchases else 0.0,
        "sources": dict(sorted(sources.items())), "missing_months": missing,
        "first_date": min(dates).isoformat() if dates else None,
        "last_date": max(dates).isoformat() if dates else None,
    }


def export_experiment(
    purchases: Sequence[dict[str, Any]], month: tuple[int, int], max_changes: int,
    band: float, created_at: dt.datetime,
) -> str:
    """Export reproducible inputs/results locally, excluding personal notes."""
    lg.estimate_range(0, band)
    if not isinstance(created_at, dt.datetime) or created_at.tzinfo is None:
        raise ValueError("Creation time must include a timezone.")
    if len(month) != 2 or not 1 <= month[1] <= 12:
        raise ValueError("Choose a valid year and month.")
    selected = [item for item in purchases if lg.month_of(item["date"]) == month]
    inputs = []
    for item in selected:
        factors = lg.calculate_impact(item["product_type"], item["price_usd"], item["condition"], item["brand"], item["low_packaging"])
        inputs.append({
            "purchase_id": item["id"], "date": item["date"].isoformat(),
            "product_type": item["product_type"], "brand": item["brand"],
            "price_usd": item["price_usd"], "condition": item["condition"],
            "low_packaging": item["low_packaging"],
            "source": item.get("source", "user"), "model_factors": factors,
        })
    plan = action_plan(selected, max_changes)
    document = {
        "schema_version": 1, "model_version": lg.MODEL_VERSION,
        "created_at": created_at.isoformat(), "month": f"{month[0]:04d}-{month[1]:02d}",
        "method": "Independent alternatives; maximum one change per purchase; ranked by model difference.",
        "limits": "Illustrative spend-based model. Differences are hypothetical, not measured savings. Brand name alternatives excluded. No price savings assumed.",
        "uncertainty_band": band,
        "baseline_range_kg": lg.estimate_range(plan["baseline_kg"], band),
        "projected_range_kg": lg.estimate_range(plan["projected_kg"], band),
        "inputs": inputs, "plan": plan,
    }
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
