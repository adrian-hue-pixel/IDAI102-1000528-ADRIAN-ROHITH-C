"""Helpers for planned purchases that reuse the existing illustrative model."""

import datetime as dt
from typing import Any

import logic as lg

Plan = dict[str, Any]


def create_plan(
    plan_id: str,
    product_type: str,
    brand: str,
    price_usd: float,
    condition: str,
    low_packaging: bool,
    planned_date: dt.date,
    today: dt.date | None = None,
) -> Plan:
    """Validate and estimate a planned purchase without adding it to purchases."""
    errors = lg.validate_purchase(
        product_type,
        brand,
        price_usd,
        condition,
        planned_date,
        low_packaging,
        is_plan=True,
        today=today,
    )
    if errors:
        raise ValueError(" ".join(errors))
    estimate = lg.calculate_impact(
        product_type, price_usd, condition, brand, low_packaging
    )
    return {
        "plan_id": plan_id,
        "date": planned_date,
        "product_type": product_type,
        "brand": brand.strip(),
        "price_usd": float(price_usd),
        "condition": condition,
        "low_packaging": bool(low_packaging),
        "co2_kg": estimate["co2_kg"],
    }


def bought_purchase(plan: Plan, purchase_id: int) -> lg.PurchaseRecord:
    """Convert a plan to a logged purchase using its current planned choices."""
    purchase = lg.make_purchase(
        purchase_id,
        plan["date"],
        plan["product_type"],
        plan["brand"],
        plan["price_usd"],
        plan["condition"],
        plan["low_packaging"],
    )
    purchase.update({"recurring": False, "recurring_group": None, "source": "user"})
    return purchase


def swapped_purchase(
    plan: Plan, alternative_label: str, purchase_id: int
) -> lg.PurchaseRecord:
    """Convert a plan into a supported greener alternative purchase."""
    product_type = plan["product_type"]
    brand = plan["brand"]
    condition = plan["condition"]
    low_packaging = plan["low_packaging"]
    product = lg.PRODUCTS[product_type]

    if alternative_label == "Buy it second-hand" and product["second_hand"]:
        condition = "Second-hand"
    elif alternative_label == "Buy it refurbished" and product["refurbished"]:
        condition = "Refurbished"
    elif alternative_label == "Pick plastic-free / minimal packaging":
        low_packaging = True
    elif alternative_label.startswith("Compare an illustrative listed example"):
        brand = product["brands"][0]
    elif alternative_label == "Swap this shop for plant-based groceries":
        product_type = "Groceries - Plant-based"
        brand = lg.PRODUCTS[product_type]["brands"][0]
    else:
        raise ValueError("Choose a greener alternative available for this plan.")

    purchase = lg.make_purchase(
        purchase_id,
        plan["date"],
        product_type,
        brand,
        plan["price_usd"],
        condition,
        low_packaging,
    )
    original_co2_kg = float(plan["co2_kg"])
    saved_kg = max(0.0, original_co2_kg - purchase["co2_kg"])
    purchase.update(
        {
            "recurring": False,
            "recurring_group": None,
            "source": "swap",
            "swap_from_label": alternative_label,
            "swap_original_co2_kg": original_co2_kg,
            "swap_saved_kg": round(saved_kg, 2),
            "swap_original_price_usd": float(plan["price_usd"]),
        }
    )
    return purchase


def what_if_savings(
    purchases: list[lg.PurchaseRecord],
    clothing_share: int,
    minimal_packaging: bool,
) -> dict[str, float]:
    """Project a scenario from existing records without mutating their estimates."""
    if not 0 <= clothing_share <= 100:
        raise ValueError("Clothing share must be between 0 and 100.")

    baseline = sum(purchase["co2_kg"] for purchase in purchases)

    def project(share: float, use_minimal_packaging: bool) -> float:
        total = 0.0
        for purchase in purchases:
            category = purchase["product_type"]
            can_swap = category == "Clothing" and purchase["condition"] == "New"
            chosen_packaging = use_minimal_packaging or purchase["low_packaging"]
            current = lg.calculate_impact(
                category,
                purchase["price_usd"],
                purchase["condition"],
                purchase["brand"],
                chosen_packaging,
            )["co2_kg"]
            if can_swap:
                second_hand = lg.calculate_impact(
                    category,
                    purchase["price_usd"],
                    "Second-hand",
                    purchase["brand"],
                    chosen_packaging,
                )["co2_kg"]
                weight = share / 100
                current = current * (1 - weight) + second_hand * weight
            total += current
        return total

    projected = project(clothing_share, minimal_packaging)
    without_packaging = project(clothing_share, False)
    with_packaging = project(clothing_share, True)
    clothing_saved = project(0, minimal_packaging) - projected
    packaging_saved = without_packaging - with_packaging

    return {
        "baseline_kg": round(baseline, 2),
        "projected_kg": round(projected, 2),
        "saved_kg": round(max(0.0, baseline - projected), 2),
        "clothing_saved_kg": round(max(0.0, clothing_saved), 2),
        "packaging_saved_kg": round(max(0.0, packaging_saved), 2),
    }


def forecast_month_end(total_kg: float, day_of_month: int, days_in_month: int) -> float:
    """Extrapolate a simple current-month pace; this is not a factual prediction."""
    if total_kg < 0 or not 1 <= day_of_month <= days_in_month:
        raise ValueError("Month total and day must be valid.")
    return round(total_kg * days_in_month / day_of_month, 2)
