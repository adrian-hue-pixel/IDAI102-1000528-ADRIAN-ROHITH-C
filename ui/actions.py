"""Shared state-changing actions for purchase and planning workflows."""

import datetime as dt
import uuid

import streamlit as st

import logic as lg
import plan_tools as pt
import purchase_series as ps
from ui.common import app_today, refresh_purchase_month_index
from ui.undo import capture_state, record_change


def load_demo() -> None:
    state = st.session_state
    before = capture_state(state)
    today = app_today()
    state.purchases = lg.demo_purchases(today)
    for purchase in state.purchases:
        purchase.update({"source": "demo", "recurring": False, "recurring_group": None})
    state.next_id = max((purchase["id"] for purchase in state.purchases), default=0) + 1
    state.last_event = None
    state.achievement_inbox = []
    state.view_month = lg.month_of(today)
    refresh_purchase_month_index(state)
    record_change(before, "Loaded synthetic demo data.", state)


def log_purchase(
    product_type: str,
    brand: str,
    price_usd: float,
    condition: str,
    low_packaging: bool,
    purchase_date: dt.date,
    repeat_monthly: bool,
    goal_kg: float,
    note: str = "",
    intent: str = "",
) -> None:
    state = st.session_state
    today = app_today()
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
        st.error("Please fix: " + " ".join(errors))
        return
    before = capture_state(state)
    month = lg.month_of(purchase_date)
    month_index = state.get("purchase_month_index")
    earned_before = lg.earned_badge_ids(
        state.purchases,
        month,
        goal_kg,
        month_index,
        goal_history=state.goal_history,
    )
    dates = (
        ps.monthly_occurrences(purchase_date, today)
        if repeat_monthly
        else [purchase_date]
    )
    recurring_group = uuid.uuid4().hex if repeat_monthly else None
    added = []
    for occurrence in dates:
        purchase = lg.add_purchase(
            state.purchases,
            state.next_id,
            occurrence,
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
                "recurring": repeat_monthly,
                "recurring_group": recurring_group,
                "source": "user",
            }
        )
        state.next_id += 1
        added.append(purchase)
    refresh_purchase_month_index(state)
    earned_after = lg.earned_badge_ids(
        state.purchases,
        month,
        goal_kg,
        state.purchase_month_index,
        goal_history=state.goal_history,
    )
    new_badges = [
        badge["name"] for badge in lg.BADGES if badge["id"] in earned_after - earned_before
    ]
    if new_badges:
        badge_lookup = {
            badge["name"]: badge
            for badge in lg.evaluate_badges(
                state.purchases,
                month,
                goal_kg,
                goal_history=state.goal_history,
            )
            if badge["earned"]
        }
        state.achievement_inbox.extend(
            {
                "name": name,
                "month": lg.month_label(month),
                "reason": badge_lookup[name]["reason"],
            }
            for name in new_badges
        )
    latest = added[-1]
    state.last_event = {
        "rating": latest["rating"],
        "purchase_id": latest["id"],
        "co2": latest["co2_kg"],
        "eco": latest["rating"] == "Low",
        "new_badges": new_badges,
        "type": product_type,
        "animate_eco": latest["rating"] == "Low",
        "animate_badge": bool(new_badges),
    }
    state.tip_view_category = product_type
    state.quote = lg.random_quote()
    state.view_month = month
    noun = "purchase" if len(added) == 1 else "purchases"
    record_change(before, f"Logged {len(added)} {product_type} {noun}.", state)


def save_plan(
    product_type: str,
    brand: str,
    price_usd: float,
    condition: str,
    low_packaging: bool,
    planned_date: dt.date,
) -> None:
    today = app_today()
    try:
        plan = pt.create_plan(
            uuid.uuid4().hex,
            product_type,
            brand,
            price_usd,
            condition,
            low_packaging,
            planned_date,
            today=today,
        )
    except ValueError as error:
        st.error(f"Plan could not be saved: {error}")
    else:
        before = capture_state(st.session_state)
        st.session_state.plans.append(plan)
        record_change(before, f"Saved a {product_type} plan.", st.session_state)
        st.toast(f"Plan saved · illustrative estimate {plan['co2_kg']:.1f} kg CO₂e.")


def badge_progress(
    badge_id: str,
    purchases: list[dict],
    month: tuple[int, int],
    month_index: dict | None = None,
) -> tuple[int, int]:
    if month_index is None:
        month_index = lg.build_month_index(purchases)
    month_items = month_index.get(month, [])
    if badge_id == "first_step":
        return min(len(purchases), 1), 1
    if badge_id in {"low_impact", "eco_saver"}:
        target = lg.MIN_PURCHASES_FOR_MONTHLY_BADGES
        return min(len(month_items), target), target
    if badge_id == "second_life":
        count = sum(item["condition"] != "New" for item in month_items)
        return min(count, 2), 2
    if badge_id == "curated_list":
        count = sum(item["curated_brand_match"] for item in month_items)
        return min(count, 2), 2
    if badge_id == "plant":
        count = sum(item["product_type"] == "Groceries - Plant-based" for item in month_items)
        return min(count, 2), 2
    if badge_id == "footprint_shrinker":
        return int(
            lg.month_momentum(purchases, month, month_index)["direction"]
            == "improving"
        ), 1
    if badge_id == "swaps_chosen":
        count = sum(
            1
            for item in month_items
            if item.get("source") == "swap"
        )
        return min(count, 3), 3
    return 0, 1
