"""Monthly recurrence date generation is capped and does not make future entries."""

import datetime as dt

from purchase_series import MAX_RECURRING_ENTRIES, monthly_occurrences


def test_monthly_occurrences_clamp_short_months_and_current_date():
    dates = monthly_occurrences(
        dt.date(2026, 1, 31),
        dt.date(2026, 3, 15),
    )

    assert dates == [
        dt.date(2026, 1, 31),
        dt.date(2026, 2, 28),
        dt.date(2026, 3, 15),
    ]


def test_monthly_occurrences_cap_to_latest_twelve_months():
    dates = monthly_occurrences(
        dt.date(2020, 1, 5),
        dt.date(2026, 10, 7),
    )

    assert len(dates) == MAX_RECURRING_ENTRIES
    assert dates[0] == dt.date(2025, 11, 5)
    assert dates[-1] == dt.date(2026, 10, 5)


def test_monthly_occurrences_reject_future_start_and_invalid_limit():
    assert monthly_occurrences(dt.date(2026, 10, 8), dt.date(2026, 10, 7)) == []
    try:
        monthly_occurrences(dt.date(2026, 1, 1), dt.date(2026, 2, 1), limit=0)
    except ValueError as error:
        assert "at least one" in str(error)
    else:
        raise AssertionError("Expected a zero occurrence limit to be rejected.")
