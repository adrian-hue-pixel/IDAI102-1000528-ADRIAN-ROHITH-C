"""Portable CSV import and export for ShopImpact purchase records."""

import csv
import datetime as dt
import io
import math
from typing import Any

import logic as lg

CSV_FIELDS = (
    "date",
    "product_type",
    "brand",
    "condition",
    "packaging",
    "price_usd",
    "co2e_kg",
    "recurring",
    "recurring_group",
    "source",
    "swap_label",
    "swap_saved_kg",
    "swap_original_co2_kg",
    "swap_original_price_usd",
    "note",
    "intent",
)

REQUIRED_FIELDS = CSV_FIELDS[:7]
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _escape_spreadsheet_text(value: str) -> str:
    if value.startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value


def _restore_spreadsheet_text(value: str) -> tuple[str, bool]:
    if len(value) > 1 and value[0] == "'" and value[1] in FORMULA_PREFIXES:
        return value[1:], True
    return value, False


def export_purchases(purchases: list[dict[str, Any]]) -> str:
    """Serialize purchases with stable, documented, portable CSV columns."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for purchase in purchases:
        writer.writerow(
            {
                "date": purchase["date"].isoformat(),
                "product_type": _escape_spreadsheet_text(purchase["product_type"]),
                "brand": _escape_spreadsheet_text(purchase["brand"]),
                "condition": purchase["condition"],
                "packaging": str(purchase["low_packaging"]).lower(),
                "price_usd": f"{purchase['price_usd']:.2f}",
                "co2e_kg": f"{purchase['co2_kg']:.3f}",
                "recurring": str(bool(purchase.get("recurring", False))).lower(),
                "recurring_group": _escape_spreadsheet_text(
                    purchase.get("recurring_group") or ""
                ),
                "source": purchase.get(
                    "source", "demo" if purchase.get("is_demo", False) else "user"
                ),
                "swap_label": _escape_spreadsheet_text(
                    purchase.get("swap_from_label") or ""
                ),
                "swap_saved_kg": (
                    f"{purchase['swap_saved_kg']:.2f}"
                    if "swap_saved_kg" in purchase
                    else ""
                ),
                "swap_original_co2_kg": (
                    f"{purchase['swap_original_co2_kg']:.2f}"
                    if "swap_original_co2_kg" in purchase
                    else ""
                ),
                "swap_original_price_usd": (
                    f"{purchase['swap_original_price_usd']:.2f}"
                    if "swap_original_price_usd" in purchase
                    else ""
                ),
                "note": _escape_spreadsheet_text(purchase.get("note") or ""),
                "intent": purchase.get("intent") or "",
            }
        )
    return output.getvalue()


def import_purchases(
    csv_text: str, first_id: int = 1, today: dt.date | None = None
) -> tuple[list[dict[str, Any]], list[tuple[int, str]]]:
    """Validate CSV rows and rebuild records, returning skipped row reasons.

    The supplied CO₂e value is informational only; the estimate is recalculated
    using the app's current illustrative model.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        return [], [(1, "CSV is empty or has no header row.")]
    missing_fields = [
        field for field in REQUIRED_FIELDS if field not in reader.fieldnames
    ]
    if missing_fields:
        return [], [(1, f"Missing required columns: {', '.join(missing_fields)}.")]

    imported: list[dict[str, Any]] = []
    skipped: list[tuple[int, str]] = []
    next_id = first_id
    for row_number, row in enumerate(reader, start=2):
        if None in row:
            skipped.append((row_number, "Row has more values than the header."))
            continue
        try:
            purchase_date = dt.date.fromisoformat(row["date"].strip())
            price_usd = float(row["price_usd"])
        except (AttributeError, TypeError, ValueError):
            skipped.append((row_number, "Date or USD price is not valid."))
            continue

        packaging_value = (row.get("packaging") or "").strip().lower()
        if packaging_value not in {"true", "false"}:
            skipped.append((row_number, "Packaging must be true or false."))
            continue
        low_packaging = packaging_value == "true"
        recurring_value = (row.get("recurring") or "false").strip().lower()
        if recurring_value not in {"true", "false"}:
            skipped.append((row_number, "Recurring must be true or false."))
            continue
        recurring = recurring_value == "true"
        recurring_group, escaped_recurring_group = _restore_spreadsheet_text(
            row.get("recurring_group") or ""
        )
        if not escaped_recurring_group:
            recurring_group = recurring_group.strip()
        if recurring and not recurring_group:
            skipped.append((row_number, "Recurring entries need a series identifier."))
            continue
        source = (row.get("source") or "user").strip().lower()
        if source not in {"user", "demo", "swap"}:
            skipped.append((row_number, "Source must be user, demo, or swap."))
            continue
        product_type, _ = _restore_spreadsheet_text(row.get("product_type") or "")
        product_type = product_type.strip()
        brand, escaped_brand = _restore_spreadsheet_text(row.get("brand") or "")
        if not escaped_brand:
            brand = brand.strip()
        condition = (row.get("condition") or "").strip()
        note, _ = _restore_spreadsheet_text(row.get("note") or "")
        intent = (row.get("intent") or "").strip()
        errors = lg.validate_purchase(
            product_type,
            brand,
            price_usd,
            condition,
            purchase_date,
            low_packaging,
            today=today,
            note=note,
            intent=intent,
        )
        if errors:
            skipped.append((row_number, " ".join(errors)))
            continue
        purchase = lg.make_purchase(
            next_id,
            purchase_date,
            product_type,
            brand,
            price_usd,
            condition,
            low_packaging,
            today=today,
            note=note,
            intent=intent,
        )
        purchase.update(
            {
                "recurring": recurring,
                "recurring_group": recurring_group if recurring else None,
                "source": source,
            }
        )
        try:
            swap_saved_kg = float(row.get("swap_saved_kg") or "")
        except (TypeError, ValueError):
            swap_saved_kg = float("nan")
        swap_label, _ = _restore_spreadsheet_text(row.get("swap_label") or "")
        if (
            source == "swap"
            and swap_label.strip()
            and math.isfinite(swap_saved_kg)
            and swap_saved_kg >= 0
        ):
            purchase["swap_from_label"] = swap_label
            purchase["swap_saved_kg"] = swap_saved_kg
            for column, field in (
                ("swap_original_co2_kg", "swap_original_co2_kg"),
                ("swap_original_price_usd", "swap_original_price_usd"),
            ):
                try:
                    value = float(row.get(column) or "")
                except (TypeError, ValueError):
                    continue
                if math.isfinite(value) and value >= 0:
                    purchase[field] = value
        if escaped_brand:
            purchase["brand"] = brand
        imported.append(purchase)
        next_id += 1
    return imported, skipped
