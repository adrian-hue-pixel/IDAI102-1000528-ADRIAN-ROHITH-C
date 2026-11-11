"""
ShopImpact - the "engine" of the app.

Everything here is plain Python (lists, dictionaries, functions, datetime) with
NO Streamlit code, so each small function can be tested on its own.

Core idea
---------
    CO2 (kg) = price (USD) x product multiplier x condition factor
                           x brand factor x packaging factor

The multipliers are CURATED, ILLUSTRATIVE values (kg CO2e per US dollar spent),
inspired by spend-based carbon estimates. They are not exact measurements; the
goal is to build awareness and compare choices, not to judge anyone.
"""

import datetime as dt
import math
import random
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

# ----------------------------------------------------------------------------
# 1. CONSTANTS (easy to tweak in one place)
# ----------------------------------------------------------------------------
PurchaseRecord = dict[str, Any]
MonthKey = tuple[int, int]
GoalHistory = Sequence[dict[str, Any]]
INTENTS = ("Need", "Want", "Gift", "Unsure")
MAX_NOTE_LENGTH = 140
MODEL_VERSION = "2026.1"
DEFAULT_UNCERTAINTY = 0.30

CONDITION_FACTORS = {  # illustrative assumptions; not measured product data
    "New": 1.00,
    "Refurbished": 0.45,
    "Second-hand": 0.20,
}
CURATED_BRAND_FACTOR = 0.75  # illustrative model factor for matching names
LOW_PACKAGING_FACTOR = 0.90  # illustrative model factor for marked packaging

LOW_INTENSITY = 0.25  # kg CO2 per $ -> at or below = "Low"
MEDIUM_INTENSITY = 0.55  # at or below = "Medium", above = "High"
ECO_SAVER_INTENSITY = 0.30  # monthly average needed for the Eco Saver badge
MIN_PURCHASES_FOR_MONTHLY_BADGES = 3
MAX_PRICE_USD = 1_000_000
UNUSUALLY_LARGE_PURCHASE_USD = 10_000
MIN_PURCHASE_DATE = dt.date(2000, 1, 1)

KG_PER_CAR_KM = 0.17  # rough average petrol car
KG_PER_TREE_MONTH = 1.75  # a mature tree absorbs roughly 21 kg CO2 a year


def max_purchase_date(today: dt.date, is_plan: bool = False) -> dt.date:
    """Return the latest date allowed for a logged purchase or planned purchase."""
    if not is_plan:
        return today
    try:
        return today.replace(year=today.year + 2)
    except ValueError:
        return today.replace(year=today.year + 2, day=28)

# Approximate, fixed demo exchange rates (units of currency per 1 USD).
CURRENCIES = {
    "US Dollar ($)": ("$", 1.0),
    "Indian Rupee (₹)": ("₹", 88.0),
    "Euro (€)": ("€", 0.92),
    "British Pound (£)": ("£", 0.78),
}

# ----------------------------------------------------------------------------
# 2. PRODUCT DATA - one dictionary per product type
#    multiplier  : kg CO2e per USD (illustrative)
#    brands      : examples to research (NOT certifications or endorsements)
#    alternatives: greener options to nudge the user toward
#    second_hand / refurbished : is this a sensible "what-if" for the product?
# ----------------------------------------------------------------------------
PRODUCTS = {
    "Clothing": {
        "emoji": "👕",
        "multiplier": 0.55,
        "second_hand": True,
        "refurbished": False,
        "brands": ["Patagonia", "Pact", "Thought", "People Tree"],
        "alternatives": [
            "Browse second-hand or vintage shops before buying new",
            "Choose organic cotton, linen or recycled fibres",
            "Swap or rent clothes for one-off events",
        ],
    },
    "Leather Shoes": {
        "emoji": "👞",
        "multiplier": 0.95,
        "second_hand": True,
        "refurbished": False,
        "brands": ["Veja", "Nisolo", "Thesus"],
        "alternatives": [
            "Get your current pair resoled or repaired",
            "Look for pre-owned leather shoes (they last for decades)",
            "Try plant-based or recycled-material footwear",
        ],
    },
    "Sneakers": {
        "emoji": "👟",
        "multiplier": 0.65,
        "second_hand": True,
        "refurbished": False,
        "brands": ["Veja", "Allbirds", "Native Shoes"],
        "alternatives": [
            "Pick sneakers made with recycled or natural materials",
            "Buy a durable pair and wash/repair instead of replacing",
            "Check resale platforms for barely-worn pairs",
        ],
    },
    "Smartphone": {
        "emoji": "📱",
        "multiplier": 0.45,
        "second_hand": False,
        "refurbished": True,
        "brands": ["Fairphone", "Refurbished (any brand)"],
        "alternatives": [
            "Buy a certified refurbished phone",
            "Choose a repairable model with replaceable battery",
            "Keep your phone one more year - the biggest saving of all",
        ],
    },
    "Laptop / Computer": {
        "emoji": "💻",
        "multiplier": 0.55,
        "second_hand": False,
        "refurbished": True,
        "brands": ["Framework", "Refurbished (any brand)"],
        "alternatives": [
            "Choose a refurbished business-class laptop",
            "Pick a repairable/upgradeable model (RAM and storage you can swap)",
            "Upgrade RAM or SSD in your current laptop instead of replacing it",
        ],
    },
    "Home Appliance": {
        "emoji": "🔌",
        "multiplier": 0.50,
        "second_hand": True,
        "refurbished": True,
        "brands": ["Miele", "Bosch (energy-label A)", "Refurbished (any brand)"],
        "alternatives": [
            "Choose the highest energy-rating you can afford",
            "Repair before you replace - many faults are cheap to fix",
            "Look for refurbished or ex-display appliances",
        ],
    },
    "Furniture": {
        "emoji": "🛋️",
        "multiplier": 0.45,
        "second_hand": True,
        "refurbished": False,
        "brands": ["Second-hand / local maker", "FSC-certified wood", "Vitra"],
        "alternatives": [
            "Buy second-hand or upcycle - solid wood furniture lasts generations",
            "Look for FSC-certified or reclaimed wood",
            "Choose local makers to cut transport emissions",
        ],
    },
    "Groceries - Meat & Dairy": {
        "emoji": "🥩",
        "multiplier": 1.60,
        "second_hand": False,
        "refurbished": False,
        "brands": ["Local farm / farmers market", "Organic local producer"],
        "alternatives": [
            "Try a plant-based meal 1-2 days a week (lentils, beans, tofu)",
            "Buy smaller amounts of higher-quality local meat/dairy",
            "Choose oat or soy milk for everyday use",
        ],
    },
    "Groceries - Plant-based": {
        "emoji": "🥦",
        "multiplier": 0.40,
        "second_hand": False,
        "refurbished": False,
        "brands": ["Local farm / farmers market", "Organic local producer", "Oddbox"],
        "alternatives": [
            "Buy seasonal and local produce",
            "Choose loose items over plastic-wrapped ones",
            "Rescue 'wonky' veg boxes to cut food waste",
        ],
    },
    "Books & Stationery": {
        "emoji": "📚",
        "multiplier": 0.20,
        "second_hand": True,
        "refurbished": False,
        "brands": ["Second-hand bookshop", "Local library", "Bookshop.org"],
        "alternatives": [
            "Borrow from a library or swap with friends",
            "Buy second-hand books",
            "Choose recycled paper stationery",
        ],
    },
    "Cosmetics & Personal Care": {
        "emoji": "🧴",
        "multiplier": 0.35,
        "second_hand": False,
        "refurbished": False,
        "brands": ["Lush", "Dr. Bronner's", "Ethique"],
        "alternatives": [
            "Try solid bars (shampoo, soap) with no plastic bottle",
            "Use refill stations and refillable containers",
            "Pick products with short, natural ingredient lists",
        ],
    },
    "Cleaning Products": {
        "emoji": "🧽",
        "multiplier": 0.30,
        "second_hand": False,
        "refurbished": False,
        "brands": ["Seventh Generation", "Ecover", "Method"],
        "alternatives": [
            "Use concentrated refills instead of new bottles",
            "Make a simple vinegar and bicarbonate cleaner at home",
            "Switch to plant-based, biodegradable formulas",
        ],
    },
    "Toys & Games": {
        "emoji": "🧸",
        "multiplier": 0.40,
        "second_hand": True,
        "refurbished": False,
        "brands": ["Plan Toys", "Hape", "Toy library / second-hand"],
        "alternatives": [
            "Buy second-hand or join a toy library",
            "Choose wooden or recycled-plastic toys",
            "Pick open-ended toys that last for years",
        ],
    },
    "Coffee & Tea": {
        "emoji": "☕",
        "multiplier": 0.55,
        "second_hand": False,
        "refurbished": False,
        "brands": ["Fairtrade / organic", "Local roaster", "Pukka"],
        "alternatives": [
            "Choose Fairtrade or Rainforest Alliance certified",
            "Buy loose-leaf tea or beans in compostable/refill packaging",
            "Brew only what you will drink - less wasted water and energy",
        ],
    },
}

# These examples are not verified sustainability claims or certifications.
CURATED_BRAND_NAMES = sorted(
    {b.lower() for p in PRODUCTS.values() for b in p["brands"]}
)
CURATED_NAME_KEYWORDS = (
    "second-hand",
    "secondhand",
    "thrift",
    "charity shop",
    "library",
    "farmers market",
    "fairtrade",
    "fair trade",
    "organic",
    "refurbished",
    "refill",
)

# ----------------------------------------------------------------------------
# 3. TIPS & QUOTES (shown after each purchase)
# ----------------------------------------------------------------------------
ECO_TIPS = [
    "If you do not need a replacement yet, keeping what you own is a simple option.",
    "Repair, borrowing and swapping can be useful alternatives to buying new.",
    "Choose an option that fits your needs and budget; a greener choice does not have to be perfect.",
]
CATEGORY_TIPS = {
    "Clothing": [
        "Consider repairing, swapping or looking for second-hand clothing before buying new.",
        "Check the care instructions; looking after clothes can help you keep them longer.",
    ],
    "Leather Shoes": [
        "Repairing or resoling a pair may help you keep it in use for longer.",
        "Consider second-hand shoes if they suit your needs and fit comfortably.",
    ],
    "Sneakers": [
        "Keeping, cleaning or repairing your current pair can be an alternative to replacement.",
        "When replacing sneakers, look for a pair that suits your needs and is designed to be durable.",
    ],
    "Smartphone": [
        "Keeping your current phone longer or repairing it can be an alternative to replacement.",
        "Refurbished phones are one option to compare when you need a replacement.",
    ],
    "Laptop / Computer": [
        "A repair or upgrade may meet your needs without replacing the whole computer.",
        "If you need a replacement, compare refurbished options as well as new ones.",
    ],
    "Home Appliance": [
        "Check whether an appliance can be repaired before replacing it.",
        "Compare energy labels and repair options when choosing an appliance.",
    ],
    "Furniture": [
        "Repairing, reusing or buying second-hand furniture can be worth considering.",
        "Look for furniture that can be maintained or repaired over time.",
    ],
    "Groceries - Meat & Dairy": [
        "You could try a plant-based meal when it suits your preferences and diet.",
        "Planning meals can help you buy amounts that work for your household.",
    ],
    "Groceries - Plant-based": [
        "Planning meals and storing food well can help make the most of what you buy.",
        "Seasonal produce is one option to explore when it is available and affordable.",
    ],
    "Books & Stationery": [
        "Libraries, book swaps and second-hand shops can be alternatives to buying new books.",
        "Reuse notebooks and stationery when there are still usable pages or supplies.",
    ],
    "Cosmetics & Personal Care": [
        "Refillable products may be an option if they are available and suit your routine.",
        "Use what you already have before replacing personal-care products.",
    ],
    "Cleaning Products": [
        "Refill packs and concentrated products are options to compare where available.",
        "Use cleaning products as directed and finish what you already have before replacing them.",
    ],
    "Toys & Games": [
        "Toy libraries, swaps and second-hand options can extend the use of toys and games.",
        "Choose toys that are easy to share, repair or pass on when possible.",
    ],
    "Coffee & Tea": [
        "Reusable cups or loose-leaf options may suit your routine and local availability.",
        "Making only what you plan to drink can help avoid unnecessary food waste.",
    ],
}
QUOTES = [
    "Small, thoughtful choices can add up to meaningful habits.",
    "Progress matters more than perfection.",
    "A better choice is one that works for you and your circumstances.",
]


def random_tip(rng: Any = random) -> str:
    """Return a random eco tip."""
    return rng.choice(ECO_TIPS)


def random_quote(rng: Any = random) -> str:
    """Return a random motivational quote."""
    return rng.choice(QUOTES)


def generate_eco_tip(
    product_type: str | None, previous_tip: str = "", rng: Any = random
) -> str:
    """Choose a practical tip for a category without immediately repeating it."""
    choices = CATEGORY_TIPS.get(product_type, ECO_TIPS)
    alternatives = [tip for tip in choices if tip != previous_tip]
    return rng.choice(alternatives or choices)


def tip_of_day(
    product_type: str | None,
    day: dt.date,
    offset: int = 0,
    previous_tip: str = "",
) -> str:
    """Choose a category tip deterministically for a date and rotation offset."""
    choices = CATEGORY_TIPS.get(product_type, ECO_TIPS)
    category_seed = sum(ord(character) for character in (product_type or ""))
    index = (day.toordinal() + category_seed + offset) % len(choices)
    tip = choices[index]
    if tip == previous_tip and len(choices) > 1:
        tip = choices[(index + 1) % len(choices)]
    return tip


# ----------------------------------------------------------------------------
# 4. IMPACT CALCULATION
# ----------------------------------------------------------------------------
def matches_curated_brand(brand: object) -> bool:
    """Match a name against examples; this is not a judgement or certification."""
    name = brand.strip().lower() if isinstance(brand, str) else ""
    if not name:
        return False
    if name in CURATED_BRAND_NAMES:
        return True
    return any(word in name for word in CURATED_NAME_KEYWORDS)


def calculate_impact(
    product_type: object,
    price_usd: object,
    condition: object = "New",
    brand: object = "",
    low_packaging: object = False,
) -> dict[str, Any]:
    """
    Estimate the footprint of ONE purchase.

    Returns a dictionary containing the final CO2 (kg) and every factor used,
    so the interface can explain the number ("show your working").
    """
    if not isinstance(product_type, str) or product_type not in PRODUCTS:
        raise ValueError(f"Unknown product type: {product_type}")
    if not isinstance(condition, str) or condition not in CONDITION_FACTORS:
        raise ValueError(f"Unknown condition: {condition}")
    if not _valid_price(price_usd):
        raise ValueError(
            f"Price must be a finite number from zero to ${MAX_PRICE_USD:,.0f} USD"
        )
    price_float = float(price_usd)
    if price_float < 0 or price_float > MAX_PRICE_USD:
        raise ValueError(
            f"Price must be a finite number from zero to ${MAX_PRICE_USD:,.0f} USD"
        )

    multiplier = PRODUCTS[product_type]["multiplier"]
    condition_factor = CONDITION_FACTORS[condition]
    curated_match = matches_curated_brand(brand)
    brand_factor = CURATED_BRAND_FACTOR if curated_match else 1.0
    packaging_factor = LOW_PACKAGING_FACTOR if low_packaging else 1.0

    co2 = price_float * multiplier * condition_factor * brand_factor * packaging_factor
    return {
        "co2_kg": round(co2, 3),
        "multiplier": multiplier,
        "condition_factor": condition_factor,
        "brand_factor": brand_factor,
        "packaging_factor": packaging_factor,
        "curated_brand_match": curated_match,
    }


def validate_purchase(
    product_type: object,
    brand: object,
    price_usd: object,
    condition: object,
    purchase_date: object,
    low_packaging: object = False,
    is_plan: bool = False,
    today: dt.date | None = None,
    *,
    note: object = "",
    intent: object = "",
) -> list[str]:
    """Return friendly validation messages for a purchase before it is stored."""
    errors = []
    if not isinstance(product_type, str) or product_type not in PRODUCTS:
        errors.append("Choose a product category from the list.")
    if not isinstance(brand, str) or not brand.strip():
        errors.append("Enter a brand or shop name.")
    if not _valid_price(price_usd) or price_usd <= 0:
        errors.append("Enter a price greater than zero using a valid number.")
    elif price_usd > MAX_PRICE_USD:
        errors.append(
            f"Enter a price no greater than ${MAX_PRICE_USD:,.0f} USD equivalent."
        )
    if not isinstance(condition, str) or condition not in CONDITION_FACTORS:
        errors.append("Choose a valid item condition.")
    if not isinstance(purchase_date, dt.date) or isinstance(purchase_date, dt.datetime):
        errors.append("Choose a valid purchase date.")
    else:
        today = today or dt.datetime.now().astimezone().date()
        if purchase_date < MIN_PURCHASE_DATE:
            errors.append(
                f"Choose a date on or after {MIN_PURCHASE_DATE:%d %b %Y}."
            )
        max_date = max_purchase_date(today, is_plan=is_plan)
        if purchase_date > max_date:
            if is_plan:
                errors.append(
                    "Planned purchases can be dated no more than two years ahead."
                )
            else:
                errors.append("A logged purchase date cannot be in the future.")
    if not isinstance(low_packaging, bool):
        errors.append("Choose whether the packaging is minimal.")
    if not isinstance(note, str):
        errors.append("Enter a note using text.")
    elif len(note.strip()) > MAX_NOTE_LENGTH:
        errors.append(f"Keep notes to {MAX_NOTE_LENGTH} characters or fewer.")
    if not isinstance(intent, str) or intent.strip() not in ("", *INTENTS):
        errors.append("Choose Need, Want, Gift, or Unsure for the purchase intent.")
    return errors


def estimate_range(
    co2_kg: float, band: float = DEFAULT_UNCERTAINTY
) -> tuple[float, float]:
    """Return a plain illustrative uncertainty range around one estimate."""
    if not isinstance(band, (int, float)) or isinstance(band, bool) or not 0 <= band <= 0.5:
        raise ValueError("Estimate uncertainty band must be between 0 and 0.5.")
    if not isinstance(co2_kg, (int, float)) or isinstance(co2_kg, bool):
        raise TypeError("Estimated CO₂e must be a non-negative number.")
    if not math.isfinite(co2_kg) or co2_kg < 0:
        raise ValueError("Estimated CO₂e must be a non-negative number.")
    low = max(0.0, co2_kg * (1 - band))
    high = co2_kg * (1 + band)
    return round(low, 1), round(high, 1)


def _valid_price(value: object) -> bool:
    """Accept finite numeric values while rejecting booleans and malformed inputs."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        try:
            return math.isfinite(float(value))
        except OverflowError:
            return False
    if isinstance(value, Decimal):
        return value.is_finite()
    return False


def rate_impact(co2_kg: float, price_usd: float) -> str:
    """Label a purchase Low / Medium / High using kg CO2 per dollar."""
    if price_usd <= 0:
        return "Low"
    intensity = co2_kg / price_usd
    if intensity <= LOW_INTENSITY:
        return "Low"
    if intensity <= MEDIUM_INTENSITY:
        return "Medium"
    return "High"


RATING_EMOJI = {"Low": "🌿", "Medium": "🟡", "High": "🔥"}


def equivalents(co2_kg: float) -> dict[str, float]:
    """Turn kilograms of CO2 into things people can picture."""
    return {
        "car_km": round(co2_kg / KG_PER_CAR_KM, 1),
        "tree_months": round(co2_kg / KG_PER_TREE_MONTH, 1),
    }


def make_purchase(
    purchase_id: int,
    date: dt.date,
    product_type: str,
    brand: str,
    price_usd: float,
    condition: str = "New",
    low_packaging: bool = False,
    today: dt.date | None = None,
    *,
    note: str = "",
    intent: str = "",
) -> PurchaseRecord:
    """Build one purchase record (a dictionary) ready to store in the list."""
    errors = validate_purchase(
        product_type,
        brand,
        price_usd,
        condition,
        date,
        low_packaging,
        today=today,
        note=note,
        intent=intent,
    )
    if errors:
        raise ValueError(" ".join(errors))
    price_float = float(price_usd)
    result = calculate_impact(
        product_type, price_float, condition, brand, low_packaging
    )
    return {
        "id": purchase_id,
        "date": date,
        "product_type": product_type,
        "brand": (brand or "").strip() or "Unspecified",
        "price_usd": round(price_float, 2),
        "condition": condition,
        "low_packaging": low_packaging,
        "co2_kg": result["co2_kg"],
        "curated_brand_match": result["curated_brand_match"],
        "rating": rate_impact(result["co2_kg"], price_float),
        "note": note.strip(),
        "intent": intent.strip(),
    }


def add_purchase(
    purchases: list[PurchaseRecord],
    purchase_id: int,
    date: dt.date,
    product_type: str,
    brand: str,
    price_usd: float,
    condition: str = "New",
    low_packaging: bool = False,
    today: dt.date | None = None,
    *,
    note: str = "",
    intent: str = "",
) -> PurchaseRecord:
    """Validate, create and append one purchase; return the new record."""
    purchase = make_purchase(
        purchase_id,
        date,
        product_type,
        brand,
        price_usd,
        condition,
        low_packaging,
        today=today,
        note=note,
        intent=intent,
    )
    purchases.append(purchase)
    return purchase


# ----------------------------------------------------------------------------
# 5. MONTHLY SUMMARIES (the dashboard numbers)
# ----------------------------------------------------------------------------
def month_of(date: dt.date) -> MonthKey:
    """(year, month) tuple used as the key for a month."""
    return (date.year, date.month)


def month_label(ym: MonthKey) -> str:
    """(2026, 10) -> 'October 2026'"""
    return dt.date(ym[0], ym[1], 1).strftime("%B %Y")


def previous_month(ym: MonthKey) -> MonthKey:
    """Return the calendar month immediately before ``ym``."""
    year, month = ym
    return (year - 1, 12) if month == 1 else (year, month - 1)


def goal_for_month(
    history: GoalHistory | None,
    ym: MonthKey,
    default: float,
) -> float:
    """Return the most recently active goal for ``ym``, or ``default``."""
    applicable = [
        entry
        for entry in history or ()
        if tuple(entry["from_month"]) <= ym
    ]
    if not applicable:
        return default
    active = max(applicable, key=lambda entry: tuple(entry["from_month"]))
    return float(active["goal_kg"])


def suggested_goal_presets(
    purchases: Sequence[PurchaseRecord],
    month_index: dict[MonthKey, list[PurchaseRecord]] | None = None,
) -> tuple[float, dict[str, int]] | None:
    """Suggest rounded goals from the average of up to three logged months."""
    totals = monthly_totals(purchases, month_index)
    if len(totals) < 2:
        return None
    recent = totals[-3:]
    average = sum(row["co2_kg"] for row in recent) / len(recent)

    def rounded_goal(factor: float) -> int:
        target = average * factor
        return min(300, max(20, math.floor(target / 5 + 0.5) * 5))

    return average, {
        "Same as my average": rounded_goal(1.0),
        "10% lower": rounded_goal(0.9),
        "20% lower": rounded_goal(0.8),
    }


def purchases_in_month(
    purchases: Sequence[PurchaseRecord], ym: MonthKey
) -> list[PurchaseRecord]:
    """Select purchases whose date falls within ``ym``."""
    return [p for p in purchases if month_of(p["date"]) == ym]


def build_month_index(
    purchases: Sequence[PurchaseRecord],
) -> dict[MonthKey, list[PurchaseRecord]]:
    """Group a journal by month in one pass for repeated monthly calculations."""
    index: dict[MonthKey, list[PurchaseRecord]] = {}
    for purchase in purchases:
        index.setdefault(month_of(purchase["date"]), []).append(purchase)
    return index


def monthly_summary(
    purchases: Sequence[PurchaseRecord],
    ym: MonthKey,
    month_index: dict[MonthKey, list[PurchaseRecord]] | None = None,
) -> dict[str, Any]:
    """Totals for one month: count, spend, CO2, intensity, rating, by category."""
    items = (
        month_index.get(ym, [])
        if month_index is not None
        else purchases_in_month(purchases, ym)
    )
    spend = sum(p["price_usd"] for p in items)
    co2 = sum(p["co2_kg"] for p in items)
    by_type = {}
    by_category = {}
    for p in items:
        by_type[p["product_type"]] = by_type.get(p["product_type"], 0) + p["co2_kg"]
        category = by_category.setdefault(
            p["product_type"], {"spend_usd": 0.0, "co2_kg": 0.0, "count": 0}
        )
        category["spend_usd"] += p["price_usd"]
        category["co2_kg"] += p["co2_kg"]
        category["count"] += 1
    for category in by_category.values():
        category["spend_usd"] = round(category["spend_usd"], 2)
        category["co2_kg"] = round(category["co2_kg"], 2)
    return {
        "n": len(items),
        "spend_usd": round(spend, 2),
        "co2_kg": round(co2, 2),
        "average_co2_kg": round(co2 / len(items), 2) if items else 0.0,
        "intensity": round(co2 / spend, 3) if spend > 0 else 0.0,
        "rating": rate_impact(co2, spend),
        "by_type": by_type,
        "by_category": by_category,
    }


def monthly_totals(
    purchases: Sequence[PurchaseRecord],
    month_index: dict[MonthKey, list[PurchaseRecord]] | None = None,
) -> list[dict[str, Any]]:
    """One row per month (oldest first) - used for the trend charts."""
    index = month_index if month_index is not None else build_month_index(purchases)
    months = sorted(index)
    rows = []
    for ym in months:
        s = monthly_summary(purchases, ym, index)
        rows.append(
            {
                "ym": ym,
                "label": dt.date(ym[0], ym[1], 1).strftime("%b %Y"),
                "spend_usd": s["spend_usd"],
                "co2_kg": s["co2_kg"],
            }
        )
    return rows


def swap_savings(
    purchases: Sequence[PurchaseRecord],
    ym: MonthKey,
) -> dict[str, Any]:
    """Summarize positive illustrative swap comparisons for one month."""
    swaps = [
        purchase
        for purchase in purchases
        if month_of(purchase["date"]) == ym
        and purchase.get("source") == "swap"
        and purchase.get("swap_saved_kg", 0) > 0
    ]
    saved_kg = round(sum(purchase["swap_saved_kg"] for purchase in swaps), 2)
    return {
        "count": len(swaps),
        "saved_kg": saved_kg,
        "saved_equivalents": equivalents(saved_kg),
    }


def monthly_insights(
    purchases: Sequence[PurchaseRecord],
    ym: MonthKey,
    month_index: dict[MonthKey, list[PurchaseRecord]] | None = None,
) -> list[str]:
    """Return a few deterministic, model-based observations for one month."""
    index = month_index if month_index is not None else build_month_index(purchases)
    current_items = index.get(ym, [])
    if not current_items:
        return []

    insights: list[str] = []
    previous_ym = previous_month(ym)
    previous_items = index.get(previous_ym, [])
    if previous_items:
        current = monthly_summary(purchases, ym, index)
        previous = monthly_summary(purchases, previous_ym, index)
        categories = sorted(set(current["by_category"]) | set(previous["by_category"]))
        change = max(
            categories,
            key=lambda category: abs(
                current["by_category"].get(category, {}).get("co2_kg", 0.0)
                - previous["by_category"].get(category, {}).get("co2_kg", 0.0)
            ),
        )
        delta = current["by_category"].get(change, {}).get("co2_kg", 0.0) - previous[
            "by_category"
        ].get(change, {}).get("co2_kg", 0.0)
        if abs(delta) < 0.05:
            insights.append("Your estimated impact was about the same as last month.")
        else:
            direction = "higher" if delta > 0 else "lower"
            insights.append(
                f"Estimated {change.lower()} impact was {abs(delta):.1f} kg CO₂e "
                f"{direction} than last month."
            )

    second_life_saving = 0.0
    for purchase in current_items:
        if purchase["condition"] != "New":
            new_estimate = calculate_impact(
                purchase["product_type"],
                purchase["price_usd"],
                "New",
                purchase["brand"],
                purchase["low_packaging"],
            )["co2_kg"]
            second_life_saving += new_estimate - purchase["co2_kg"]
    if second_life_saving > 0:
        insights.append(
            f"Second-hand or refurbished choices were about {second_life_saving:.1f} "
            "kg CO₂e lower than new-item estimates in this illustrative model."
        )

    intent_items = [purchase for purchase in current_items if purchase.get("intent")]
    total_co2_kg = sum(purchase["co2_kg"] for purchase in current_items)
    if len(intent_items) >= 3 and total_co2_kg > 0:
        want_co2_kg = sum(
            purchase["co2_kg"]
            for purchase in intent_items
            if purchase["intent"] == "Want"
        )
        share = round(want_co2_kg / total_co2_kg * 100)
        insights.append(
            f"About {share}% of this month's estimated footprint came from "
            "purchases you tagged as wants."
        )

    totals = monthly_totals(purchases, index)
    if len(totals) > 1:
        best = min(totals, key=lambda row: (row["co2_kg"], row["ym"]))
        insights.append(
            f"Your lowest-estimated month so far was {month_label(best['ym'])} "
            f"at {best['co2_kg']:.1f} kg CO₂e."
        )
    return insights[:4]


def goal_streak(
    purchases: Sequence[PurchaseRecord],
    goal_kg: float,
    through: MonthKey,
    month_index: dict[MonthKey, list[PurchaseRecord]] | None = None,
    goal_history: GoalHistory | None = None,
) -> int:
    """Count consecutive logged months ending at ``through`` within their goals."""
    streak = 0
    ym = through
    index = month_index if month_index is not None else build_month_index(purchases)
    while True:
        summary = monthly_summary(purchases, ym, index)
        month_goal = goal_for_month(goal_history, ym, goal_kg)
        if not summary["n"] or summary["co2_kg"] > month_goal:
            return streak
        streak += 1
        ym = previous_month(ym)


def peak_highlights(
    purchases: Sequence[PurchaseRecord],
    ym: MonthKey,
    goal_kg: float,
    month_index: dict[MonthKey, list[PurchaseRecord]] | None = None,
    goal_history: GoalHistory | None = None,
) -> dict[str, Any]:
    """Return quick, user-friendly peak moments for the selected month."""
    index = month_index if month_index is not None else build_month_index(purchases)
    items = index.get(ym, [])
    summary = monthly_summary(purchases, ym, index)
    month_goal = goal_for_month(goal_history, ym, goal_kg)
    best_choice = None
    if items:
        best = min(
            items,
            key=lambda purchase: (purchase["co2_kg"], purchase["price_usd"]),
        )
        best_choice = {
            "label": f"{best['product_type']} · {best['brand']}",
            "co2_kg": round(best["co2_kg"], 1),
            "note": "Lowest estimated impact this month",
        }

    top_category = None
    if summary["by_category"]:
        category_name, category_values = max(
            summary["by_category"].items(),
            key=lambda item: (item[1]["co2_kg"], item[1]["count"]),
        )
        top_category = {
            "category": category_name,
            "co2_kg": round(category_values["co2_kg"], 1),
            "note": "Biggest category footprint",
        }

    return {
        "best_choice": best_choice,
        "top_category": top_category,
        "goal_status": {
            "met": summary["co2_kg"] <= month_goal,
            "message": (
                f"{summary['co2_kg']:.1f} / {month_goal:.0f} kg month total"
                if summary["n"]
                else "No purchases logged yet"
            ),
        },
    }


def month_momentum(
    purchases: Sequence[PurchaseRecord],
    ym: MonthKey,
    month_index: dict[MonthKey, list[PurchaseRecord]] | None = None,
) -> dict[str, float | str]:
    """Compare this month to the previous month and label the direction of change."""
    index = month_index if month_index is not None else build_month_index(purchases)
    current = monthly_summary(purchases, ym, index)
    previous_ym = previous_month(ym)
    previous = monthly_summary(purchases, previous_ym, index)
    if not current["n"] or not previous["n"]:
        return {
            "delta_kg": 0.0,
            "percent_change": 0.0,
            "status": "No trend yet",
            "direction": "steady",
        }
    delta = current["co2_kg"] - previous["co2_kg"]
    percent_change = (delta / previous["co2_kg"]) * 100 if previous["co2_kg"] else 0.0
    if abs(delta) < 0.05:
        direction = "steady"
        status = "About the same as last month"
    elif delta < 0:
        direction = "improving"
        status = f"{abs(percent_change):.0f}% lower than last month"
    else:
        direction = "worse"
        status = f"{abs(percent_change):.0f}% higher than last month"
    return {
        "delta_kg": round(delta, 1),
        "percent_change": round(percent_change, 1),
        "status": status,
        "direction": direction,
    }


# ----------------------------------------------------------------------------
# 6. BADGES - rule based, evaluated for the month being viewed
# ----------------------------------------------------------------------------
BADGES = [
    {
        "id": "first_step",
        "name": "First Step",
        "symbol": "sprout",
        "ring": "#8d6e3f",
        "fill": "#f1d9a0",
        "desc": "Log your very first purchase.",
    },
    {
        "id": "low_impact",
        "name": "Low Impact Shopper",
        "symbol": "leaf",
        "ring": "#2e7d32",
        "fill": "#c8e6c9",
        "desc": "Stay under your monthly CO₂ goal (3+ purchases).",
    },
    {
        "id": "eco_saver",
        "name": "Eco Saver",
        "symbol": "star",
        "ring": "#b8860b",
        "fill": "#ffe082",
        "desc": "Average impact of 0.30 kg CO₂ per $ or less (3+ purchases).",
    },
    {
        "id": "second_life",
        "name": "Second-Life Hero",
        "symbol": "cycle",
        "ring": "#1565c0",
        "fill": "#bbdefb",
        "desc": "Buy 2+ second-hand or refurbished items in a month.",
    },
    {
        "id": "curated_list",
        "name": "Curated-List Explorer",
        "symbol": "link",
        "ring": "#6a4c93",
        "fill": "#e1d5f0",
        "desc": "Log 2+ purchases using names on the illustrative list (not a certification).",
    },
    {
        "id": "plant",
        "name": "Plant Powered",
        "symbol": "heart",
        "ring": "#c2185b",
        "fill": "#f8bbd0",
        "desc": "Buy 2+ plant-based grocery items and no meat/dairy in a month.",
    },
    {
        "id": "shrinker",
        "name": "Footprint Shrinker",
        "symbol": "arrow",
        "ring": "#00695c",
        "fill": "#b2dfdb",
        "desc": "Beat last month's total CO₂ (and log something this month).",
    },
    {
        "id": "swaps_chosen",
        "name": "Swaps chosen",
        "symbol": "cycle",
        "ring": "#008577",
        "fill": "#b2dfdb",
        "desc": "Choose 3 alternatives in a month.",
    },
]


def evaluate_badges(
    purchases: Sequence[PurchaseRecord],
    ym: MonthKey,
    goal_kg: float,
    month_index: dict[MonthKey, list[PurchaseRecord]] | None = None,
    goal_history: GoalHistory | None = None,
) -> list[dict[str, Any]]:
    """
    Check every badge rule. Returns a list of dictionaries:
    the badge definition + 'earned' (bool) + 'progress' (hint text).
    """
    index = month_index if month_index is not None else build_month_index(purchases)
    month_items = index.get(ym, [])
    s = monthly_summary(purchases, ym, index)
    month_goal = goal_for_month(goal_history, ym, goal_kg)
    n = s["n"]
    enough = n >= MIN_PURCHASES_FOR_MONTHLY_BADGES

    used = sum(1 for p in month_items if p["condition"] != "New")
    curated_matches = sum(1 for p in month_items if p["curated_brand_match"])
    plant = sum(
        1 for p in month_items if p["product_type"] == "Groceries - Plant-based"
    )
    meat = sum(
        1 for p in month_items if p["product_type"] == "Groceries - Meat & Dairy"
    )

    prev = monthly_summary(purchases, previous_month(ym), index)
    swap_count = sum(
        1
        for purchase in month_items
        if purchase.get("source") == "swap"
    )

    def tier_for(current: int, target: int) -> tuple[str | None, int | None, str]:
        if target <= 0:
            return (None, None, "")
        if current >= target * 3:
            return ("Gold", target * 3, "Ready for gold tier")
        if current >= target * 2:
            return ("Silver", target * 2, "Next tier: Gold")
        if current >= target:
            return ("Bronze", target, "Next tier: Silver")
        if current <= 0:
            return (None, target, f"Next tier: Bronze at {target}")
        return (None, target, f"Next tier: Bronze at {target}")

    # earned? and a short progress message for locked badges
    rules = {
        "first_step": (
            len(purchases) >= 1,
            "Log a purchase to unlock",
            "You logged at least one purchase.",
        ),
        "low_impact": (
            enough and s["co2_kg"] <= month_goal,
            (
                f"{n}/{MIN_PURCHASES_FOR_MONTHLY_BADGES} purchases, "
                f"{s['co2_kg']:.0f}/{month_goal:.0f} kg"
            ),
            f"{n} purchases total {s['co2_kg']:.1f} kg, within your {month_goal:.0f} kg goal.",
        ),
        "eco_saver": (
            enough and s["intensity"] <= ECO_SAVER_INTENSITY,
            (
                f"{n}/{MIN_PURCHASES_FOR_MONTHLY_BADGES} purchases, "
                f"avg {s['intensity']:.2f} (need ≤ {ECO_SAVER_INTENSITY})"
            ),
            f"Your estimated intensity is {s['intensity']:.2f} kg per USD across {n} purchases.",
        ),
        "second_life": (
            used >= 2,
            f"{used}/2 second-hand or refurbished",
            f"You logged {used} second-hand or refurbished purchases.",
        ),
        "curated_list": (
            curated_matches >= 2,
            f"{curated_matches}/2 curated-list purchases",
            f"{curated_matches} names matched the illustrative list; this is not a certification.",
        ),
        "plant": (
            plant >= 2 and meat == 0,
            f"{plant}/2 plant-based" + (", remove meat/dairy" if meat else ""),
            f"You logged {plant} plant-based grocery purchases and no meat/dairy purchase this month.",
        ),
        "shrinker": (
            n >= 1 and prev["n"] >= 1 and s["co2_kg"] < prev["co2_kg"],
            "Needs purchases in both this and last month, with a lower total",
            f"This month is {s['co2_kg']:.1f} kg, below last month's {prev['co2_kg']:.1f} kg estimate.",
        ),
        "swaps_chosen": (
            swap_count >= 3,
            f"{min(swap_count, 3)}/3 alternatives chosen",
            f"You chose {swap_count} alternatives; their impact differences are illustrative estimates.",
        ),
    }
    results = []
    for badge in BADGES:
        earned, hint, reason = rules[badge["id"]]
        count = {
            "first_step": len(purchases),
            "low_impact": n,
            "eco_saver": n,
            "second_life": used,
            "curated_list": curated_matches,
            "plant": plant,
            "shrinker": n,
            "swaps_chosen": swap_count,
        }[badge["id"]]
        target = {"first_step": 1, "low_impact": 3, "eco_saver": 3, "second_life": 2, "curated_list": 2, "plant": 2, "shrinker": 1, "swaps_chosen": 3}[badge["id"]]
        tier, next_target, tier_text = tier_for(count, target)
        tier_display = "Bronze" if tier is None and count >= target else (tier or "Bronze")
        results.append(
            {
                **badge,
                "earned": earned,
                "reason": reason if earned else "",
                "progress": "Earned! 🎉" if earned else hint,
                "tier": tier_display,
                "tier_target": next_target,
                "tier_text": tier_text,
            }
        )
    return results


def earned_badge_ids(
    purchases: Sequence[PurchaseRecord],
    ym: MonthKey,
    goal_kg: float,
    month_index: dict[MonthKey, list[PurchaseRecord]] | None = None,
    goal_history: GoalHistory | None = None,
) -> set[str]:
    """Return the identifiers of badges earned for the selected month."""
    return {
        b["id"]
        for b in evaluate_badges(
            purchases, ym, goal_kg, month_index, goal_history
        )
        if b["earned"]
    }


# ----------------------------------------------------------------------------
# 7. GREENER ALTERNATIVES
# ----------------------------------------------------------------------------
def suggest_alternatives(
    product_type: str,
    brand: str = "",
    price_usd: float = 0.0,
    condition: str = "New",
    low_packaging: bool = False,
) -> dict[str, Any]:
    """
    Returns:
      'static'  - list of greener ideas for this product type
      'brands'  - illustrative brand examples to research
      'what_if' - list of {label, co2_kg, saved_kg, kind}: the same purchase with one
                  greener choice, sorted by biggest saving first
    """
    if not isinstance(product_type, str) or product_type not in PRODUCTS:
        raise ValueError(f"Unknown product type: {product_type}")
    info = PRODUCTS[product_type]
    now = calculate_impact(product_type, price_usd, condition, brand, low_packaging)[
        "co2_kg"
    ]
    what_if = []

    def add(label, alt_co2, kind="condition"):
        saved = round(now - alt_co2, 2)
        if saved > 0.005:
            what_if.append(
                {"label": label, "co2_kg": round(alt_co2, 2), "saved_kg": saved, "kind": kind}
            )

    if condition == "New" and info["second_hand"]:
        add(
            "Buy it second-hand",
            calculate_impact(
                product_type, price_usd, "Second-hand", brand, low_packaging
            )["co2_kg"],
        )
    if condition == "New" and info["refurbished"]:
        add(
            "Buy it refurbished",
            calculate_impact(
                product_type, price_usd, "Refurbished", brand, low_packaging
            )["co2_kg"],
        )
    if not matches_curated_brand(brand):
        add(
            f"Compare an illustrative listed example (e.g. {info['brands'][0]})",
            calculate_impact(
                product_type, price_usd, condition, info["brands"][0], low_packaging
            )["co2_kg"],
            kind="brand",
        )
    if not low_packaging:
        add(
            "Pick plastic-free / minimal packaging",
            calculate_impact(product_type, price_usd, condition, brand, True)["co2_kg"],
            kind="packaging",
        )
    if product_type == "Groceries - Meat & Dairy":
        add(
            "Swap this shop for plant-based groceries",
            calculate_impact(
                "Groceries - Plant-based", price_usd, condition, brand, low_packaging
            )["co2_kg"],
            kind="category",
        )

    what_if.sort(key=lambda w: w["saved_kg"], reverse=True)
    return {
        "static": info["alternatives"],
        "brands": info["brands"],
        "what_if": what_if,
    }


# ----------------------------------------------------------------------------
# 8. DEMO DATA (15 purchases across 3 months: cheap, expensive, eco, non-eco)
# ----------------------------------------------------------------------------
def _shift_month(date: dt.date, months_back: int) -> tuple[int, int]:
    year, month = date.year, date.month - months_back
    while month < 1:
        month += 12
        year -= 1
    return year, month


def demo_purchases(today: dt.date | None = None) -> list[PurchaseRecord]:
    """15 sample purchases for the current month and the two before it."""
    today = today or dt.datetime.now().astimezone().date()
    # (months back, day, type, brand, price USD, condition, low packaging)
    rows = [
        (2, 3, "Leather Shoes", "Generic brand", 120, "New", False),
        (2, 7, "Groceries - Meat & Dairy", "Supermarket", 60, "New", False),
        (2, 12, "Clothing", "Fast Fashion Co", 45, "New", False),
        (2, 18, "Laptop / Computer", "Dell", 900, "New", False),
        (2, 24, "Books & Stationery", "Second-hand bookshop", 25, "Second-hand", True),
        (1, 4, "Sneakers", "Veja", 110, "New", False),
        (
            1,
            9,
            "Groceries - Plant-based",
            "Local farm / farmers market",
            55,
            "New",
            True,
        ),
        (1, 15, "Clothing", "Thrift store", 35, "Second-hand", False),
        (1, 20, "Cleaning Products", "Seventh Generation", 18, "New", True),
        (1, 26, "Coffee & Tea", "Starbucks", 22, "New", False),
        (0, 1, "Smartphone", "Fairphone", 150, "Refurbished", False),
        (0, 2, "Groceries - Plant-based", "Oddbox", 40, "New", True),
        (
            0,
            3,
            "Groceries - Plant-based",
            "Local farm / farmers market",
            35,
            "New",
            True,
        ),
        (0, 4, "Clothing", "Patagonia", 50, "Second-hand", False),
        (0, 5, "Cosmetics & Personal Care", "Lush", 25, "New", True),
    ]
    purchases = []
    for i, (back, day, ptype, brand, price, cond, pack) in enumerate(rows, start=1):
        year, month = _shift_month(today, back)
        if back == 0:
            day = min(day, today.day)  # never create future dates
        purchases.append(
            make_purchase(
                i,
                dt.date(year, month, day),
                ptype,
                brand,
                price,
                cond,
                pack,
                today=today,
            )
        )
    return purchases
