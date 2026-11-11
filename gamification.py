"""Gentle progress summaries derived from existing purchase results."""

from datetime import date, datetime, timedelta
from itertools import pairwise
from typing import Any

import logic as lg

XP_PER_PURCHASE = 3
DAILY_LOG_XP_CAP = 15
SECOND_HAND_XP = 10
LOW_RATING_XP = 5
SWAP_XP = 15
MONTHLY_GOAL_XP = 25
MONTHLY_GOAL_MIN_PURCHASES = 3


def _purchase_day(purchase: dict[str, Any]) -> date:
    value = purchase["date"]
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def experience_summary(
    purchases: list[dict[str, Any]],
    goal_history: list[dict[str, Any]] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Derive supportive XP from eligible saved purchase records."""
    today = today or datetime.now().astimezone().date()
    breakdown = {
        "Logging purchases": 0,
        "Second-hand or refurbished": 0,
        "Low-rated choices": 0,
        "Illustrative swap differences": 0,
        "Monthly goal reflection": 0,
    }
    eligible = [
        purchase
        for purchase in purchases
        if purchase.get("source") != "demo"
        and not purchase.get("is_demo", False)
        and not purchase.get("recurring", False)
        and _purchase_day(purchase) <= today
    ]

    daily_counts: dict[date, int] = {}
    for purchase in eligible:
        day = _purchase_day(purchase)
        daily_counts[day] = daily_counts.get(day, 0) + 1
    breakdown["Logging purchases"] = sum(
        min(count * XP_PER_PURCHASE, DAILY_LOG_XP_CAP)
        for count in daily_counts.values()
    )

    for purchase in eligible:
        if purchase.get("condition") in {"Second-hand", "Refurbished"}:
            breakdown["Second-hand or refurbished"] += SECOND_HAND_XP
        if purchase.get("rating") == "Low":
            breakdown["Low-rated choices"] += LOW_RATING_XP
        if purchase.get("source") == "swap" and purchase.get("swap_saved_kg", 0) > 0:
            breakdown["Illustrative swap differences"] += SWAP_XP

    if goal_history is not None:
        default_goal = (
            min(goal_history, key=lambda entry: tuple(entry["from_month"]))["goal_kg"]
            if goal_history
            else 0
        )
        purchases_by_month: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for purchase in eligible:
            month = lg.month_of(_purchase_day(purchase))
            purchases_by_month.setdefault(month, []).append(purchase)
        for month, month_purchases in purchases_by_month.items():
            if len(month_purchases) < MONTHLY_GOAL_MIN_PURCHASES:
                continue
            month_total = sum(purchase.get("co2_kg", 0) for purchase in month_purchases)
            month_goal = lg.goal_for_month(goal_history, month, default_goal)
            if month_total <= month_goal:
                breakdown["Monthly goal reflection"] += MONTHLY_GOAL_XP

    experience = sum(breakdown.values())
    level, progress = divmod(experience, 100)
    reasons = [
        (
            f"Logging gives {XP_PER_PURCHASE} XP per purchase, capped at "
            f"{DAILY_LOG_XP_CAP} XP per day."
        ),
        f"Second-hand or refurbished choices add {SECOND_HAND_XP} XP each.",
        f"Low-rated choices add {LOW_RATING_XP} XP each.",
        f"A swap with a positive illustrative difference adds {SWAP_XP} XP.",
        (
            f"A month with at least {MONTHLY_GOAL_MIN_PURCHASES} purchases at or "
            f"below its goal adds {MONTHLY_GOAL_XP} XP."
        ),
    ]
    return {
        "experience": experience,
        "level": level + 1,
        "progress": progress,
        "next_level": (level + 1) * 100,
        "breakdown": breakdown,
        "reasons": reasons,
    }


def weekly_challenges(
    purchases: list[dict[str, Any]],
    today: date,
    month_review_last_visit: str | None = None,
) -> list[dict[str, int | str | bool]]:
    """Return optional, date-based challenges for this calendar week."""
    week_start = today - timedelta(days=today.weekday())
    week_purchases = [
        purchase
        for purchase in purchases
        if week_start <= _purchase_day(purchase) <= today
    ]
    low_count = sum(purchase["rating"] == "Low" for purchase in week_purchases)
    reviewed_this_week = False
    if month_review_last_visit:
        try:
            last_visit = date.fromisoformat(month_review_last_visit)
        except ValueError:
            last_visit = None
        reviewed_this_week = (
            last_visit is not None and week_start <= last_visit <= today
        )
    return [
        {
            "title": "Review your month's impact this week",
            "progress": int(reviewed_this_week),
            "target": 1,
            "complete": reviewed_this_week,
        },
        {
            "title": "Try one low-impact option this week",
            "progress": min(low_count, 1),
            "target": 1,
            "complete": low_count >= 1,
        },
    ]


def best_activity_streak(purchases: list[dict[str, Any]]) -> int:
    """Count the longest purchase-date activity run, allowing one rest day."""
    days = sorted({_purchase_day(purchase) for purchase in purchases})
    if not days:
        return 0
    longest = current = 1
    for previous, current_day in pairwise(days):
        if (current_day - previous).days <= 2:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
    return longest


def current_activity_streak(purchases: list[dict[str, Any]], today: date) -> int:
    """Count the active run ending today or yesterday, allowing one rest day."""
    days = sorted({_purchase_day(purchase) for purchase in purchases})
    days = [day for day in days if day <= today]
    if not days or days[-1] < today - timedelta(days=1):
        return 0

    streak = 1
    for previous, current in pairwise(reversed(days)):
        if (previous - current).days > 2:
            break
        streak += 1
    return streak
