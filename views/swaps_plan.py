"""Optional greener swaps, scenario comparison, and planned purchases."""

import streamlit as st

import logic as lg
import plan_tools as pt
from ui.common import page_header, refresh_purchase_month_index, whats_next
from ui.undo import capture_state, record_change

NEXT = ("views/garden_badges.py", "Garden and badges", "See your garden and progress.")


def render() -> None:
    page_header(
        "Swaps and plan",
        "Compare a possibility, test a scenario and keep the choices that work for you.",
        action_label="View garden",
        action_page=NEXT[0],
    )
    state = st.session_state
    month = state.view_month
    symbol, rate = lg.CURRENCIES[state.currency_name]
    uncertainty_band = state.uncertainty_band / 100

    st.markdown(
        '<div class="studio-section"><span class="section-label">THINK BEFORE YOU BUY</span>'
        '<p>Start with an idea, compare the assumptions, then make a flexible plan. '
        'Experiments here leave your purchase journal unchanged.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown("## Three optional swaps")
    month_items = state.purchase_month_index.get(month, [])
    if month_items:
        ranked = sorted(month_items, key=lambda item: item["co2_kg"], reverse=True)[:3]
        swap_cols = st.columns(min(3, len(ranked)))
        for index, (col, purchase) in enumerate(zip(swap_cols, ranked), 1):
            alternatives = lg.suggest_alternatives(
                purchase["product_type"],
                purchase["brand"],
                purchase["price_usd"],
                purchase["condition"],
                purchase["low_packaging"],
            )
            best = max(
                alternatives["what_if"],
                key=lambda item: item["saved_kg"],
                default=None,
            )
            with col, st.container(border=True):
                st.markdown(f"#### {index}. {purchase['product_type']}")
                st.write(f"{purchase['brand']} · {purchase['co2_kg']:.1f} kg CO₂e")
                if best:
                    st.write(f"Try **{best['label']}**")
                    st.caption(
                        f"About {best['saved_kg']:.1f} kg lower in the "
                        "illustrative estimate."
                    )
                elif alternatives["static"]:
                    st.write(alternatives["static"][0])
                else:
                    st.caption("No lower estimate is listed for this choice.")
        st.caption(
            "Suggestions are optional ideas ranked by the illustrative estimate, "
            "not product claims or endorsements."
        )
    else:
        st.caption("Personalized swap ideas will appear after you add a purchase.")

    st.markdown(
        '<aside class="studio-note"><strong>Want to change just a few choices?</strong>'
        '<p>Impact Lab ranks alternatives across your month with a limit on how '
        'many purchases you want to change.</p></aside>',
        unsafe_allow_html=True,
    )
    st.page_link("views/impact_lab.py", label="Build an action plan in Impact Lab →")
    st.markdown("## Compare two options")
    st.caption("Use the same price or category to isolate a factor. This comparison applies the learning model, not verified product data.")
    compare_cols = st.columns(2)
    estimates = []
    for col, label, suffix in zip(compare_cols, ("Option A", "Option B"), ("a", "b")):
        with col, st.container(border=True):
            st.markdown(f"### {label}")
            product = st.selectbox(
                "Product type", list(lg.PRODUCTS), key=f"compare_type_{suffix}"
            )
            price = st.number_input(
                f"Price ({symbol})",
                min_value=0.0,
                max_value=float(lg.MAX_PRICE_USD * rate),
                value=25.0 * rate,
                key=f"compare_price_{suffix}",
            )
            condition = st.selectbox(
                "Condition",
                list(lg.CONDITION_FACTORS),
                key=f"compare_condition_{suffix}",
            )
            packaging = st.checkbox(
                "Minimal packaging", key=f"compare_packaging_{suffix}"
            )
            estimate = lg.calculate_impact(
                product, price / rate, condition, "", packaging
            )
            estimates.append(estimate)
            st.metric(
                f"{label} estimate",
                f"{estimate['co2_kg']:.2f} kg CO₂e",
            )
            with st.expander("Show model factors"):
                st.write(
                    f"{price / rate:.2f} USD × {estimate['multiplier']} product × "
                    f"{estimate['condition_factor']} condition × "
                    f"{estimate['brand_factor']} brand × "
                    f"{estimate['packaging_factor']} packaging"
                )
    if len(estimates) == 2:
        difference = estimates[0]["co2_kg"] - estimates[1]["co2_kg"]
        st.caption(
            f"Difference: {abs(difference):.2f} kg CO₂e in this illustrative comparison."
        )
    st.caption("Prices are converted to USD for the estimate; brand matching is not applied.")

    st.markdown("## What-if simulator")
    st.caption("Explore a hypothetical without changing your journal.")
    clothing_share = st.slider(
        "Swap this share of new clothing to second-hand",
        0,
        100,
        step=10,
        key="what_if_clothing_share",
    )
    minimal = st.checkbox(
        "Choose minimal packaging where available",
        key="what_if_minimal_packaging",
    )
    scenario = pt.what_if_savings(month_items, clothing_share, minimal)
    before_col, after_col = st.columns(2)
    before_col.metric("Current illustrative estimate", f"{scenario['baseline_kg']:.1f} kg")
    after_col.metric(
        "What-if estimate",
        f"{scenario['projected_kg']:.1f} kg",
        f"{scenario['saved_kg']:.1f} kg difference",
    )
    st.progress(
        0
        if not scenario["baseline_kg"]
        else min(1.0, scenario["projected_kg"] / scenario["baseline_kg"]),
        text="Projected share of this month's illustrative estimate",
    )
    st.caption("This scenario is not a measured saving or a promise about a real product.")

    st.markdown("## Your plans")
    if state.get("plan_feedback"):
        st.success(state.plan_feedback)
        state.plan_feedback = None
    month_plans = [
        plan for plan in state.plans if lg.month_of(plan["date"]) == month
    ]
    if not month_plans:
        st.markdown(
            '<div class="studio-empty"><h3>Leave room for a better choice.</h3>'
            '<p>No plans for this month yet. Choose “Plan a purchase” on Home, '
            'then return here to mark it bought, swapped or skipped.</p></div>',
            unsafe_allow_html=True,
        )
        st.page_link("views/home.py", label="Plan a purchase →")
    for plan in month_plans:
        alternatives = lg.suggest_alternatives(
            plan["product_type"],
            plan["brand"],
            plan["price_usd"],
            plan["condition"],
            plan["low_packaging"],
        )["what_if"]
        with st.container(border=True):
            st.markdown(f"### {plan['product_type']} · {plan['brand']}")
            plan_low, plan_high = lg.estimate_range(
                plan["co2_kg"], uncertainty_band
            )
            st.write(
                f"Planned for {plan['date']:%d %b %Y} · "
                f"{plan['co2_kg']:.1f} kg CO₂e (illustrative estimate)"
            )
            st.caption(
                f"Model range: between {plan_low:.1f} and "
                f"{plan_high:.1f} kilograms CO₂e."
            )
            alternative = st.selectbox(
                "Greener alternative to try",
                [item["label"] for item in alternatives] or ["No suggested alternative"],
                key=f"plan_alternative_{plan['plan_id']}",
                disabled=not alternatives,
            )
            bought_col, swapped_col, skipped_col = st.columns(3)
            if bought_col.button("Mark bought", key=f"plan_bought_{plan['plan_id']}"):
                before = capture_state(state)
                state.purchases.append(pt.bought_purchase(plan, state.next_id))
                state.next_id += 1
                state.plans.remove(plan)
                refresh_purchase_month_index(state)
                state.plan_feedback = "Added to your purchase journal."
                record_change(
                    before,
                    f"Marked {plan['product_type']} plan bought.",
                    state,
                )
                st.rerun()
            if swapped_col.button(
                "Mark swapped",
                key=f"plan_swapped_{plan['plan_id']}",
                disabled=not alternatives,
            ):
                before = capture_state(state)
                replacement = pt.swapped_purchase(plan, alternative, state.next_id)
                state.purchases.append(replacement)
                state.next_id += 1
                state.plans.remove(plan)
                refresh_purchase_month_index(state)
                state.plan_feedback = (
                    f"Logged the alternative at an illustrative estimate of "
                    f"{replacement['co2_kg']:.1f} kg CO₂e."
                )
                record_change(
                    before,
                    f"Marked {plan['product_type']} plan swapped.",
                    state,
                )
                st.rerun()
            if skipped_col.button("Skip plan", key=f"plan_skipped_{plan['plan_id']}"):
                before = capture_state(state)
                state.plans.remove(plan)
                state.plan_feedback = (
                    f"Plan skipped; its avoided estimate of {plan['co2_kg']:.1f} kg "
                    "CO₂e is illustrative, not a measured saving."
                )
                record_change(
                    before,
                    f"Skipped {plan['product_type']} plan.",
                    state,
                )
                st.rerun()
    whats_next(*NEXT)


render()
