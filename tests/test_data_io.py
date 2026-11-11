"""CSV portability and per-row import validation tests."""

import csv
import datetime as dt
import io

import pytest

import logic as lg
import plan_tools as pt
from data_io import export_purchases, import_purchases


def test_purchase_csv_export_import_round_trip_recalculates_model():
    purchases = [
        {
            **lg.make_purchase(
                4,
                dt.date(2026, 9, 12),
                "Clothing",
                "Local shop",
                25.5,
                "Second-hand",
                True,
            ),
            "recurring": True,
            "recurring_group": "monthly-series-1",
            "source": "user",
        },
        lg.make_purchase(
            5, dt.date(2026, 10, 2), "Books & Stationery", "Library", 12.0, "New", False
        ),
    ]

    csv_text = export_purchases(purchases)
    restored, skipped = import_purchases(csv_text)

    assert skipped == []
    assert [p["date"] for p in restored] == [p["date"] for p in purchases]
    assert [p["product_type"] for p in restored] == [
        p["product_type"] for p in purchases
    ]
    assert [p["brand"] for p in restored] == [p["brand"] for p in purchases]
    assert [p["condition"] for p in restored] == [p["condition"] for p in purchases]
    assert [p["low_packaging"] for p in restored] == [
        p["low_packaging"] for p in purchases
    ]
    assert [p["price_usd"] for p in restored] == [p["price_usd"] for p in purchases]
    assert [p["co2_kg"] for p in restored] == [p["co2_kg"] for p in purchases]
    assert restored[0]["recurring"] is True
    assert restored[0]["recurring_group"] == "monthly-series-1"
    assert restored[0]["source"] == "user"
    assert restored[1]["recurring"] is False
    assert restored[1]["source"] == "user"
    assert [p["id"] for p in restored] == [1, 2]


def test_csv_round_trip_labels_synthetic_demo_records():
    purchase = lg.make_purchase(
        1,
        dt.date(2026, 10, 2),
        "Books & Stationery",
        "Local library",
        12,
    )
    purchase.update({"source": "demo", "recurring": False, "recurring_group": None})

    restored, skipped = import_purchases(export_purchases([purchase]))

    assert skipped == []
    assert restored[0]["source"] == "demo"
    assert ",demo" in export_purchases([purchase])


def test_swap_csv_round_trip_preserves_swap_metadata():
    plan = pt.create_plan(
        "swap-csv",
        "Clothing",
        "Local shop",
        100,
        "New",
        False,
        dt.date(2026, 10, 2),
    )
    swap = pt.swapped_purchase(plan, "Buy it second-hand", 1)

    restored, skipped = import_purchases(export_purchases([swap]))

    assert skipped == []
    assert restored[0]["source"] == "swap"
    assert restored[0]["swap_from_label"] == "Buy it second-hand"
    assert restored[0]["swap_saved_kg"] == swap["swap_saved_kg"]
    assert restored[0]["swap_original_co2_kg"] == swap["swap_original_co2_kg"]
    assert restored[0]["swap_original_price_usd"] == swap["swap_original_price_usd"]


@pytest.mark.parametrize("saved_value", ["", "not-a-number", "nan", "-1"])
def test_swap_csv_with_blank_or_invalid_saving_imports_without_swap_data(saved_value):
    csv_text = (
        "date,product_type,brand,condition,packaging,price_usd,co2e_kg,"
        "source,swap_label,swap_saved_kg\n"
        f"2026-10-02,Clothing,Local shop,Second-hand,false,100,11,swap,"
        f"Buy it second-hand,{saved_value}\n"
    )

    restored, skipped = import_purchases(csv_text)

    assert skipped == []
    assert restored[0]["source"] == "swap"
    assert not any(key.startswith("swap_") for key in restored[0])


def test_csv_import_accepts_old_files_without_optional_swap_columns():
    csv_text = (
        "date,product_type,brand,condition,packaging,price_usd,co2e_kg,source\n"
        "2026-10-02,Clothing,Local shop,New,false,12,6,user\n"
    )

    restored, skipped = import_purchases(csv_text)

    assert skipped == []
    assert restored[0]["source"] == "user"
    assert not any(key.startswith("swap_") for key in restored[0])
    assert restored[0]["note"] == ""
    assert restored[0]["intent"] == ""


def test_csv_round_trip_preserves_note_intent_and_formula_safe_text():
    note = '="A note, with quotes"'
    purchase = lg.make_purchase(
        1,
        dt.date(2026, 10, 2),
        "Clothing",
        "Local shop",
        12,
        note=note,
        intent="Gift",
    )

    csv_text = export_purchases([purchase])
    row = next(csv.DictReader(io.StringIO(csv_text)))
    restored, skipped = import_purchases(csv_text)

    assert row["note"] == "'" + note
    assert skipped == []
    assert restored[0]["note"] == note.strip()
    assert restored[0]["intent"] == "Gift"


@pytest.mark.parametrize(
    ("note", "intent", "reason"),
    [
        ("x" * (lg.MAX_NOTE_LENGTH + 1), "Need", "140 characters"),
        ("Valid", "Maybe", "intent"),
    ],
)
def test_csv_import_skips_invalid_note_or_intent(note, intent, reason):
    purchase = lg.make_purchase(1, dt.date(2026, 10, 2), "Clothing", "Shop", 12)
    row = next(csv.DictReader(io.StringIO(export_purchases([purchase]))))
    row.update({"note": note, "intent": intent})
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=row)
    writer.writeheader()
    writer.writerow(row)

    imported, skipped = import_purchases(output.getvalue())

    assert imported == []
    assert len(skipped) == 1
    assert reason in skipped[0][1]


def test_csv_import_reports_bad_rows_and_keeps_valid_rows():
    csv_text = (
        "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n"
        "2026-10-02,Books & Stationery,Library,New,false,12,2.4\n"
        "2026-10-03,Unknown,Shop,New,false,12,0\n"
        "not-a-date,Clothing,Shop,New,false,12,0\n"
    )

    restored, skipped = import_purchases(csv_text, first_id=8)

    assert len(restored) == 1
    assert restored[0]["id"] == 8
    assert [row for row, _ in skipped] == [3, 4]
    assert "category" in skipped[0][1].lower()
    assert "date" in skipped[1][1].lower()


@pytest.mark.parametrize(
    ("purchase_date", "expected"),
    [
        ("0001-01-01", "on or after"),
        ("9999-12-31", "future"),
    ],
)
def test_csv_import_rejects_dates_outside_purchase_bounds(purchase_date, expected):
    csv_text = (
        "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n"
        f"{purchase_date},Clothing,Local shop,New,false,12,2.4\n"
    )

    imported, skipped = import_purchases(csv_text)

    assert imported == []
    assert len(skipped) == 1
    assert expected in skipped[0][1].lower()


def test_csv_import_reports_missing_columns():
    restored, skipped = import_purchases("date,brand\n2026-10-02,Shop\n")

    assert restored == []
    assert skipped[0][0] == 1
    assert "missing required columns" in skipped[0][1].lower()


def test_csv_import_reports_invalid_recurring_flag_and_series_id():
    csv_text = (
        "date,product_type,brand,condition,packaging,price_usd,co2e_kg,"
        "recurring,recurring_group,source\n"
        "2026-10-02,Books & Stationery,Library,New,false,12,2.4,maybe,,user\n"
        "2026-10-03,Clothing,Shop,New,false,12,3.3,true,,user\n"
    )

    imported, skipped = import_purchases(csv_text)

    assert imported == []
    assert [line for line, _ in skipped] == [2, 3]
    assert "recurring" in skipped[0][1].lower()
    assert "series identifier" in skipped[1][1].lower()


@pytest.mark.parametrize("trigger", ["=", "+", "-", "@", "\t", "\r"])
def test_csv_export_prefixes_formula_trigger_text_fields(trigger):
    purchase = {
        **lg.make_purchase(
            1, dt.date(2026, 10, 2), "Clothing", "Local shop", 12
        ),
        "product_type": f"{trigger}Clothing",
        "brand": f"{trigger}Shop",
        "recurring": True,
        "recurring_group": f"{trigger}series",
    }

    row = next(csv.DictReader(io.StringIO(export_purchases([purchase]))))

    assert row["product_type"] == f"'{trigger}Clothing"
    assert row["brand"] == f"'{trigger}Shop"
    assert row["recurring_group"] == f"'{trigger}series"
    assert row["price_usd"] == "12.00"
    assert row["co2e_kg"] == f"{purchase['co2_kg']:.3f}"


@pytest.mark.parametrize("trigger", ["=", "+", "-", "@", "\t", "\r"])
def test_csv_export_import_round_trip_restores_escaped_text(trigger):
    brand = f"{trigger}Shop"
    recurring_group = f"{trigger}series"
    purchase = {
        **lg.make_purchase(
            1, dt.date(2026, 10, 2), "Clothing", brand, 12
        ),
        "brand": brand,
        "recurring": True,
        "recurring_group": recurring_group,
    }

    restored, skipped = import_purchases(export_purchases([purchase]))

    assert skipped == []
    assert restored[0]["brand"] == brand
    assert restored[0]["recurring_group"] == recurring_group
