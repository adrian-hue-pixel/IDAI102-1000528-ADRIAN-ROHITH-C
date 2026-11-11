"""Versioned serialization helpers for browser-local ShopImpact data."""

import datetime as dt
import json
from typing import Any

import data_io as dio
import logic as lg
import plan_tools
from styles import ACCENT_PALETTES, normalize_mode

STORAGE_KEY = "shopimpact_saved_state_v1"
TEXT_SIZES = {"S", "M", "L", "XL"}


def _validated_settings(
    value: object,
    today: dt.date | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("Saved preferences must be an object.")
    validated: dict[str, Any] = {}
    for key, item in value.items():
        if key == "text_size":
            if item not in TEXT_SIZES:
                raise ValueError("Saved text size is unsupported.")
        elif key == "dyslexia_font" or key == "sound_enabled" or key == "reduce_motion":
            if not isinstance(item, bool):
                raise TypeError(f"Saved {key} preference must be a boolean.")
        elif key == "display_mode":
            if not isinstance(item, str):
                raise ValueError("Saved display mode is unsupported.")
            item = normalize_mode(item)
        elif key == "accent_palette":
            if item not in ACCENT_PALETTES:
                raise ValueError("Saved accent palette is unsupported.")
        elif key == "currency_name":
            if item not in lg.CURRENCIES:
                raise ValueError("Saved currency is unsupported.")
        elif key == "goal_kg":
            if (
                isinstance(item, bool)
                or not isinstance(item, int)
                or not 20 <= item <= 300
                or item % 5
            ):
                raise ValueError("Saved monthly goal is unsupported.")
        elif key == "uncertainty_band":
            if (
                isinstance(item, bool)
                or not isinstance(item, int)
                or not 0 <= item <= 50
                or item % 5
            ):
                raise ValueError("Saved estimate uncertainty band is unsupported.")
            validated[key] = item
        elif key == "month_review_last_visit":
            if item is not None:
                if not isinstance(item, str):
                    raise TypeError("Saved Month in review visit date must be text.")
                try:
                    parsed_date = dt.date.fromisoformat(item)
                except ValueError as error:
                    raise ValueError(
                        "Saved Month in review visit date is unsupported."
                    ) from error
                if parsed_date.isoformat() != item:
                    raise ValueError(
                        "Saved Month in review visit date is unsupported."
                    )
        elif key == "xp_scoring_notice_dismissed":
            if not isinstance(item, bool):
                raise TypeError("Saved XP notice preference must be a boolean.")
        elif key == "goal_history":
            if not isinstance(item, list):
                raise TypeError("Saved goal history must be a list.")
            if len(item) > 60:
                raise ValueError("Saved goal history cannot exceed 60 entries.")
            history = []
            seen_months = set()
            for entry in item:
                if not isinstance(entry, dict) or set(entry) != {
                    "from_month",
                    "goal_kg",
                }:
                    raise TypeError("Saved goal history entry has an unsupported format.")
                month = entry["from_month"]
                goal = entry["goal_kg"]
                if (
                    not isinstance(month, (tuple, list))
                    or len(month) != 2
                    or any(
                        isinstance(part, bool) or not isinstance(part, int)
                        for part in month
                    )
                    or not 1 <= month[0] <= 9999
                    or not 1 <= month[1] <= 12
                ):
                    raise ValueError("Saved goal history month is unsupported.")
                if (
                    isinstance(goal, bool)
                    or not isinstance(goal, int)
                    or not 20 <= goal <= 300
                    or goal % 5
                ):
                    raise ValueError("Saved goal history goal is unsupported.")
                month_key = tuple(month)
                if month_key in seen_months:
                    raise ValueError("Saved goal history has duplicate months.")
                seen_months.add(month_key)
                history.append({"from_month": month_key, "goal_kg": goal})
            item = sorted(history, key=lambda entry: entry["from_month"])
        elif key == "view_month":
            if (
                not isinstance(item, (tuple, list))
                or len(item) != 2
                or any(isinstance(part, bool) or not isinstance(part, int) for part in item)
                or not 1 <= item[1] <= 12
                or not 1 <= item[0] <= 9999
            ):
                raise ValueError("Saved month selection is unsupported.")
            item = tuple(item)
        else:
            continue
        validated[key] = item
    if "goal_kg" in validated and "goal_history" not in validated:
        month = lg.month_of(today or dt.datetime.now().astimezone().date())
        validated["goal_history"] = [
            {"from_month": month, "goal_kg": validated["goal_kg"]}
        ]
    validated.setdefault("uncertainty_band", 30)
    validated.setdefault("month_review_last_visit", None)
    validated.setdefault("xp_scoring_notice_dismissed", False)
    return validated


def encode_saved_state(
    purchases: list[dict[str, Any]],
    guide_dismissed: bool,
    achievements: list[dict[str, str]] | None = None,
    plans: list[dict[str, Any]] | None = None,
    settings: dict[str, Any] | None = None,
) -> str:
    """Encode purchases, plans, onboarding preference, achievement inbox and UI settings."""
    safe_settings = _validated_settings(
        settings or {}, today=dt.datetime.now().astimezone().date()
    )
    return json.dumps(
        {
            "version": 3,
            "model_version": lg.MODEL_VERSION,
            "purchase_count": len(purchases),
            "purchases_csv": dio.export_purchases(purchases),
            "guide_dismissed": bool(guide_dismissed),
            "achievements": achievements or [],
            "plans": [
                {
                    **plan,
                    "date": plan["date"].isoformat(),
                }
                for plan in plans or []
            ],
            "settings": safe_settings,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def decode_saved_state(
    value: object,
    today: dt.date | None = None,
) -> tuple[
    list[dict[str, Any]],
    bool,
    list[tuple[int, str]],
    list[dict[str, str]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    """Validate saved data and rebuild purchase and planned records."""
    if not isinstance(value, str):
        raise TypeError("Saved browser data has an unsupported format.")
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("Saved browser data could not be read.") from error
    if not isinstance(payload, dict) or payload.get("version") not in {1, 2, 3}:
        raise ValueError("Saved browser data uses an unsupported version.")
    settings = _validated_settings(payload.get("settings", {}), today=today)
    if "purchases_csv" not in payload:
        raise ValueError("Saved browser purchase data is missing.")
    csv_text = payload["purchases_csv"]
    if not isinstance(csv_text, str):
        raise TypeError("Saved browser purchase data must be text.")
    dismissed = payload.get("guide_dismissed", False)
    if not isinstance(dismissed, bool):
        raise TypeError("Saved onboarding preference must be a boolean.")
    achievements = payload.get("achievements", [])
    if not isinstance(achievements, list) or any(
        not isinstance(item, dict)
        or set(item) != {"name", "month", "reason"}
        or any(not isinstance(item[key], str) for key in item)
        for item in achievements
    ):
        raise TypeError("Saved achievement data has an unsupported format.")
    saved_plans = payload.get("plans", [])
    if not isinstance(saved_plans, list):
        raise TypeError("Saved planned purchases must be a list.")
    plans: list[dict[str, Any]] = []
    expected_plan_fields = {
        "plan_id",
        "date",
        "product_type",
        "brand",
        "price_usd",
        "condition",
        "low_packaging",
        "co2_kg",
    }
    for item in saved_plans:
        if not isinstance(item, dict) or set(item) != expected_plan_fields:
            raise TypeError("Saved planned purchase has an unsupported format.")
        if not isinstance(item["plan_id"], str) or not item["plan_id"]:
            raise TypeError("Saved planned purchase ID must be text.")
        if not isinstance(item["low_packaging"], bool):
            raise TypeError("Saved packaging preference must be a boolean.")
        try:
            planned_date = dt.date.fromisoformat(item["date"])
            plan = plan_tools.create_plan(
                item["plan_id"],
                item["product_type"],
                item["brand"],
                float(item["price_usd"]),
                item["condition"],
                item["low_packaging"],
                planned_date,
                today=today,
            )
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise ValueError("Saved planned purchase could not be restored.") from error
        plans.append(plan)
    purchases, skipped = dio.import_purchases(csv_text, today=today)
    return purchases, dismissed, skipped, achievements, plans, settings
