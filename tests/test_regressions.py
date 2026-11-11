"""Retained legacy-journal regressions for data and date handling."""

import csv
import datetime as dt
import io
import os
from itertools import permutations
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

import browser_storage
import gamification
import logic as lg
from data_io import export_purchases, import_purchases
from ui import common

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")


def _purchase(
    purchase_id: int = 1,
    purchase_date: dt.date = dt.date(2026, 10, 1),
    *,
    product_type: str = "Clothing",
    brand: str = "Local shop",
    condition: str = "New",
    price: float = 24,
) -> dict:
    return lg.make_purchase(
        purchase_id,
        purchase_date,
        product_type,
        brand,
        price,
        condition,
        today=dt.date(2026, 10, 28),
    )


def _purchases_app(purchases: list[dict]) -> AppTest:
    app = AppTest.from_file(APP_PATH)
    app.session_state["browser_storage_loaded"] = True
    app.session_state["storage_available"] = False
    app.session_state["storage_error"] = "Browser storage is unavailable in AppTest."
    app.session_state["purchases"] = purchases
    app.session_state["next_id"] = max(
        (purchase["id"] for purchase in purchases), default=0
    ) + 1
    app.run()
    app.switch_page("views/purchases.py").run()
    return app


def test_corrupt_saved_state_stays_locked_without_writing(monkeypatch):
    writes = []
    raw = "not-json"
    monkeypatch.setattr(browser_storage, "read_saved_value", lambda: (True, raw, None))
    monkeypatch.setattr(
        browser_storage,
        "write_saved_value",
        lambda value: (writes.append(value) or True, None),
    )
    app = AppTest.from_file(APP_PATH).run()

    assert app.session_state["raw_saved_state"] == raw
    assert app.session_state["persistence_locked"] is True
    assert writes == []
    assert any(
        button.label == "Download my saved data (raw JSON)"
        for button in app.download_button
    )
    assert not app.exception


def test_csv_restore_requires_confirmation_and_undoes_the_full_journal():
    previous = [
        _purchase(1),
        _purchase(2, dt.date(2026, 10, 2), brand="Bookshop"),
    ]
    replacement = _purchase(1, dt.date(2026, 10, 3), brand="New shop")
    app = _purchases_app(previous)
    app.file_uploader[0].set_value(
        ("restore.csv", export_purchases([replacement]).encode(), "text/csv")
    ).run()
    next(button for button in app.button if button.label == "Preview restore").click().run()

    replace = next(button for button in app.button if button.label == "Confirm Replace")
    assert replace.disabled
    assert app.session_state["purchases"] == previous
    assert any("remove 2 current purchase(s)" in item.value for item in app.warning)

    next(
        widget
        for widget in app.checkbox
        if widget.label.startswith("I understand Replace")
    ).set_value(True).run()
    next(button for button in app.button if button.label == "Confirm Replace").click().run()
    assert app.session_state["purchases"][0]["brand"] == "New shop"
    next(
        button for button in app.button
        if button.label == "Undo: Replaced the journal from CSV."
    ).click().run()
    assert app.session_state["purchases"] == previous
    assert not app.exception


def test_csv_export_escapes_formula_text_and_import_restores_it():
    trigger = "="
    purchase = _purchase(brand=f"{trigger}shop")
    purchase["recurring"] = True
    purchase["recurring_group"] = f"{trigger}series"

    csv_text = export_purchases([purchase])
    row = next(csv.DictReader(io.StringIO(csv_text)))
    restored, skipped = import_purchases(csv_text, today=dt.date(2026, 10, 28))

    assert row["brand"] == "'=shop"
    assert row["recurring_group"] == "'=series"
    assert skipped == []
    assert restored[0]["brand"] == "=shop"
    assert restored[0]["recurring_group"] == "=series"


def test_purchase_date_bounds_match_csv_and_plan_validation():
    today = dt.date(2026, 10, 28)
    rows = (
        "date,product_type,brand,condition,packaging,price_usd,co2e_kg\n"
        "0001-01-01,Clothing,Shop,New,false,12,1\n"
        "9999-12-31,Clothing,Shop,New,false,12,1\n"
    )
    imported, skipped = import_purchases(rows, today=today)

    assert imported == []
    assert len(skipped) == 2
    assert "on or after" in skipped[0][1]
    assert "future" in skipped[1][1]
    assert lg.validate_purchase(
        "Clothing", "Shop", 12, "New", today + dt.timedelta(days=1), is_plan=True,
        today=today,
    ) == []


def test_viewer_timezone_rollover_updates_default_month_and_date_picker(monkeypatch):
    instant = dt.datetime(2026, 12, 31, 19, 0, tzinfo=dt.timezone.utc)
    real_datetime = dt.datetime

    class FixedDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)

    monkeypatch.setattr(common.dt, "datetime", FixedDateTime)
    monkeypatch.setattr(
        common.st, "context", SimpleNamespace(timezone="Asia/Kolkata")
    )
    assert common.app_today() == dt.date(2027, 1, 1)

    monkeypatch.setattr(common, "app_today", lambda: dt.date(2027, 1, 1))
    app = AppTest.from_file(APP_PATH).run()
    date_picker = next(
        widget for widget in app.date_input if widget.label == "Purchase date"
    )
    assert app.session_state["view_month"] == (2027, 1)
    assert date_picker.proto.max == "2027-01-01"
    assert not app.exception


def test_monthly_insights_are_order_independent_and_neutral_for_zero_change():
    september = dt.date(2026, 9, 10)
    october = dt.date(2026, 10, 10)
    balanced = [
        _purchase(1, september, price=5),
        _purchase(2, september, product_type="Books & Stationery", price=13.75),
        _purchase(3, october, price=10),
        _purchase(4, october, product_type="Books & Stationery", price=27.5),
    ]
    outputs = [
        lg.monthly_insights(ordering, (2026, 10))
        for ordering in permutations(balanced)
    ]
    zero_change = lg.monthly_insights(
        [_purchase(1, september), _purchase(2, october)], (2026, 10)
    )

    assert all(result == outputs[0] for result in outputs)
    assert outputs[0][0].startswith("Estimated books & stationery impact")
    assert zero_change[0] == "Your estimated impact was about the same as last month."


def test_current_streak_expires_after_yesterday_but_keeps_rest_day_allowance():
    today = dt.date(2026, 10, 10)
    assert gamification.current_activity_streak(
        [_purchase(purchase_date=today - dt.timedelta(days=1))], today
    ) == 1
    assert gamification.current_activity_streak(
        [
            _purchase(purchase_date=today - dt.timedelta(days=2)),
            _purchase(2, today),
        ],
        today,
    ) == 2
    assert gamification.current_activity_streak(
        [_purchase(purchase_date=today - dt.timedelta(days=5))], today
    ) == 0
