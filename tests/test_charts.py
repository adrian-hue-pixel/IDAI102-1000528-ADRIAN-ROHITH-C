"""Chart builders handle empty, single-month, and multi-month data."""

import charts


def test_trend_charts_show_friendly_empty_and_single_month_states():
    assert charts.trend_charts([], 80, 1.0, "$") == (None, None)
    assert charts.trend_charts(
        [{"label": "Oct 2026", "co2_kg": 12.0, "spend_usd": 30.0}],
        80,
        1.0,
        "$",
    ) == (None, None)


def test_trend_charts_build_line_goal_and_spending_for_multiple_months():
    totals = [
        {"label": "Aug 2026", "co2_kg": 18.3, "spend_usd": 42.0},
        {"label": "Sep 2026", "co2_kg": 14.1, "spend_usd": 35.0},
        {"label": "Oct 2026", "co2_kg": 20.4, "spend_usd": 60.0},
    ]

    co2_chart, spend_chart = charts.trend_charts(totals, 80, 88.0, "₹")

    assert co2_chart is not None and spend_chart is not None
    assert len(co2_chart.to_dict()["layer"]) == 2
    assert spend_chart.to_dict()["encoding"]["y"]["title"] == "Spend (₹)"


def test_trend_chart_includes_optional_forecast_as_a_dashed_layer():
    totals = [{"label": "Oct 2026", "co2_kg": 15.0, "spend_usd": 42.0}]

    co2_chart, spend_chart = charts.trend_charts(totals, 80, 1.0, "$", forecast_kg=31.0)

    assert co2_chart is not None and spend_chart is not None
    forecast = co2_chart.to_dict()["layer"][2]
    assert forecast["mark"]["strokeDash"] == [5, 4]
    assert "Oct 2026 forecast" in str(forecast["encoding"]["x"]["sort"])


def test_category_chart_builds_for_both_measures():
    rows = [
        {
            "Category": "Clothing",
            "Estimated CO₂e (kg)": 4.2,
            "Spend ($)": 10.0,
        }
    ]
    for measure in ("Estimated CO₂e", "Spend"):
        chart = charts.category_chart(rows, "$", measure)
        assert chart is not None
        assert chart.to_dict()["mark"]["type"] == "bar"
    assert charts.category_chart([], "$", "Spend") is None


def test_sparkline_is_accessible_and_handles_a_single_month():
    svg = charts.sparkline_svg([12.0], "Estimated CO₂e")

    assert 'role="img"' in svg
    assert 'aria-label="Estimated CO₂e trend across recent months"' in svg
    assert 'd="M 4.0 12.0 L 76.0 12.0"' in svg


def test_sparkline_rejects_empty_data():
    import pytest

    with pytest.raises(ValueError, match="at least one value"):
        charts.sparkline_svg([], "Purchases")
