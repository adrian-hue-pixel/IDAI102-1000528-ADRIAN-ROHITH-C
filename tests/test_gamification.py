"""Tests for gentle progress summaries derived from saved purchase results."""

from datetime import date

import gamification


def purchase(
    day: date,
    rating: str = "Medium",
    condition: str = "New",
    **fields,
) -> dict[str, object]:
    return {
        "date": day,
        "rating": rating,
        "condition": condition,
        "co2_kg": 10.0,
        **fields,
    }


def test_experience_breakdown_uses_daily_cap_and_choice_reasons():
    progress = gamification.experience_summary(
        [purchase(date(2026, 10, 1), "Low") for _ in range(7)],
        today=date(2026, 10, 31),
    )

    assert progress["breakdown"] == {
        "Logging purchases": 15,
        "Second-hand or refurbished": 0,
        "Low-rated choices": 35,
        "Illustrative swap differences": 0,
        "Monthly goal reflection": 0,
    }
    assert progress["experience"] == sum(progress["breakdown"].values())
    assert progress["level"] == 1
    assert progress["progress"] == 50


def test_experience_rewards_second_hand_low_rating_and_positive_swap():
    purchases = [
        purchase(date(2026, 10, 1), "Low", condition="Second-hand"),
        purchase(
            date(2026, 10, 2),
            "Medium",
            condition="Refurbished",
            source="swap",
            swap_saved_kg=2,
        ),
        purchase(
            date(2026, 10, 3),
            "Medium",
            source="swap",
            swap_saved_kg=0,
        ),
    ]

    result = gamification.experience_summary(
        purchases, today=date(2026, 10, 31)
    )
    assert result["breakdown"] == {
        "Logging purchases": 9,
        "Second-hand or refurbished": 20,
        "Low-rated choices": 5,
        "Illustrative swap differences": 15,
        "Monthly goal reflection": 0,
    }


def test_experience_daily_log_cap_applies_to_twenty_purchases():
    purchases = [purchase(date(2026, 10, 1)) for _ in range(20)]

    result = gamification.experience_summary(
        purchases, today=date(2026, 10, 31)
    )

    assert result["breakdown"]["Logging purchases"] == 15


def test_demo_and_recurring_records_earn_no_experience():
    purchases = [
        purchase(date(2026, 10, 1), "Low", source="demo"),
        purchase(date(2026, 10, 2), "Low", recurring=True),
        purchase(date(2026, 10, 3), "Low", is_demo=True),
    ]

    assert gamification.experience_summary(
        purchases, goal_history=[{"from_month": (2026, 10), "goal_kg": 100}],
        today=date(2026, 10, 31),
    )["experience"] == 0


def test_monthly_goal_bonus_is_awarded_once_per_month_with_history():
    purchases = [
        purchase(date(2026, 10, day), "Medium", co2_kg=10)
        for day in (1, 2, 3, 4)
    ]
    history = [{"from_month": (2026, 10), "goal_kg": 40}]

    result = gamification.experience_summary(
        purchases, goal_history=history, today=date(2026, 10, 31)
    )

    assert result["breakdown"]["Monthly goal reflection"] == gamification.MONTHLY_GOAL_XP


def test_monthly_goal_bonus_uses_month_history_and_skips_without_history():
    purchases = [
        purchase(date(2026, 9, day), "Medium", co2_kg=10)
        for day in (1, 2, 3)
    ] + [
        purchase(date(2026, 10, day), "Medium", co2_kg=10)
        for day in (1, 2, 3)
    ]
    history = [
        {"from_month": (2026, 9), "goal_kg": 40},
        {"from_month": (2026, 10), "goal_kg": 50},
    ]

    with_history = gamification.experience_summary(
        purchases, goal_history=history, today=date(2026, 10, 31)
    )
    without_history = gamification.experience_summary(
        purchases, today=date(2026, 10, 31)
    )

    assert with_history["breakdown"]["Monthly goal reflection"] == 50
    assert without_history["breakdown"]["Monthly goal reflection"] == 0


def test_experience_summary_empty_input_has_zero_breakdown():
    result = gamification.experience_summary([])

    assert result["experience"] == 0
    assert result["level"] == 1
    assert result["progress"] == 0
    assert result["breakdown"] and sum(result["breakdown"].values()) == 0
    assert result["reasons"]


def test_weekly_challenges_count_purchase_dates_in_current_week():
    challenges = gamification.weekly_challenges(
        [
            purchase(date(2026, 10, 5), "Low"),
            purchase(date(2026, 10, 6)),
            purchase(date(2026, 10, 7)),
            purchase(date(2026, 10, 4), "Low"),
            purchase(date(2026, 10, 8), "Low"),
        ],
        date(2026, 10, 7),
        date(2026, 10, 6).isoformat(),
    )

    assert challenges == [
        {
            "title": "Review your month's impact this week",
            "progress": 1,
            "target": 1,
            "complete": True,
        },
        {
            "title": "Try one low-impact option this week",
            "progress": 1,
            "target": 1,
            "complete": True,
        },
    ]


def test_activity_streak_allows_one_rest_day_and_uses_unique_dates():
    records = [
        purchase(date(2026, 10, 1)),
        purchase(date(2026, 10, 3)),
        purchase(date(2026, 10, 3), "Low"),
        purchase(date(2026, 10, 5)),
        purchase(date(2026, 10, 10)),
    ]

    assert gamification.best_activity_streak(records) == 3
    assert gamification.best_activity_streak([]) == 0


def test_current_activity_streak_includes_run_ending_today():
    today = date(2026, 10, 10)
    records = [
        purchase(date(2026, 10, 6)),
        purchase(date(2026, 10, 8)),
        purchase(date(2026, 10, 10)),
    ]

    assert gamification.current_activity_streak(records, today) == 3


def test_current_activity_streak_includes_run_ending_yesterday():
    today = date(2026, 10, 10)
    records = [
        purchase(date(2026, 10, 7)),
        purchase(date(2026, 10, 9)),
    ]

    assert gamification.current_activity_streak(records, today) == 2


def test_current_activity_streak_allows_one_rest_day_between_activities():
    today = date(2026, 10, 10)
    records = [
        purchase(date(2026, 10, 8)),
        purchase(today),
    ]

    assert gamification.current_activity_streak(records, today) == 2


def test_current_activity_streak_ignores_old_activity_runs():
    today = date(2026, 10, 10)
    records = [
        purchase(date(2026, 10, 1)),
        purchase(date(2026, 10, 3)),
        purchase(date(2026, 10, 5)),
    ]

    assert gamification.current_activity_streak(records, today) == 0
