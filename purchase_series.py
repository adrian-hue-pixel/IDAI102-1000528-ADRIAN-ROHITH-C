"""Date helpers for optional monthly recurring-purchase entries."""

import calendar
import datetime as dt

MAX_RECURRING_ENTRIES = 12


def monthly_occurrences(
    start: dt.date,
    through: dt.date,
    limit: int = MAX_RECURRING_ENTRIES,
) -> list[dt.date]:
    """Return the latest bounded monthly dates, preserving the start day when possible."""
    if limit < 1:
        raise ValueError("The occurrence limit must be at least one.")
    if start > through:
        return []

    start_index = start.year * 12 + start.month - 1
    end_index = through.year * 12 + through.month - 1
    total_months = end_index - start_index + 1
    first_offset = max(0, total_months - limit)
    dates: list[dt.date] = []
    for offset in range(first_offset, total_months):
        month_index = start_index + offset
        year, month_zero = divmod(month_index, 12)
        month = month_zero + 1
        day = min(start.day, calendar.monthrange(year, month)[1])
        if year == through.year and month == through.month:
            day = min(day, through.day)
        dates.append(dt.date(year, month, day))
    return dates
