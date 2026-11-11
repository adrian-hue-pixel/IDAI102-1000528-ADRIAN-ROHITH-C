"""Local experiments with the illustrative purchase model."""

import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

import impact_lab as lab
import logic as lg
from styles import CHART_COLORS, style_chart
from ui.common import page_header, whats_next


def render() -> None:
    page_header("Impact Lab", "Test a hypothesis, inspect the assumptions, and take a reproducible experiment with you.", action_label="Explore swaps", action_page="views/swaps_plan.py")
    with st.container(key="research-entry", border=True):
        intro, action = st.columns([3, 1], vertical_alignment="center")
        with intro:
            st.markdown("**Go deeper with research tools**")
            st.caption("Cited EPA estimates, manufacturer comparisons, validation, constrained planning and product-text analysis — all inside ShopImpact.")
        with action:
            st.page_link("views/research.py", label="Open research tools →")
        st.page_link("views/research_feedback.py", label="Share study feedback", icon=":material/chat_bubble_outline:")
    state = st.session_state
    month = state.view_month
    purchases = state.purchase_month_index.get(month, [])
    st.caption("Experiments run in this app session. Your journal is unchanged. All estimates use an illustrative spend-based model.")
    planner, model, coverage = st.tabs(["Action planner", "Model explorer", "Journal coverage"])
    with planner:
        demo_count = sum(item.get("source") == "demo" for item in purchases)
        if demo_count:
            st.caption(f"Example scenario · {demo_count} synthetic demo entries in the selected month.")
        st.markdown("### Find a few changes worth exploring")
        st.write("Choose how many purchases to reconsider. The planner picks the largest model differences, with at most one alternative for each purchase.")
        max_changes = st.slider("Maximum purchases to reconsider", 1, 10, value=3, key="lab_max_changes")
        plan = lab.action_plan(purchases, max_changes)
        cols = st.columns(3)
        cols[0].metric("Current model estimate", f"{plan['baseline_kg']:.1f} kg")
        cols[1].metric("Scenario estimate", f"{plan['projected_kg']:.1f} kg")
        cols[2].metric("Hypothetical difference", f"{plan['difference_kg']:.1f} kg")
        if not purchases:
            st.info("This month has no entries. Add a purchase, or use demo data on Home, to build a scenario.")
            st.page_link("views/home.py", label="Open your journal")
        elif not plan["changes"]:
            st.info("No lower alternatives are listed for these purchases in the current model. You can still inspect the model or explore general swap ideas.")
        else:
            for index, change in enumerate(plan["changes"], 1):
                with st.container(border=True):
                    st.markdown(f"**{index}. {change['product_type']} · purchase #{change['purchase_id']}**")
                    st.write(change["action"])
                    st.caption(f"{change['baseline_kg']:.2f} → {change['projected_kg']:.2f} kg CO₂e · {change['difference_kg']:.2f} kg model difference")
        with st.expander("How the planner works"):
            st.write("Each purchase contributes at most one alternative. Because choices are independent and each uses one change, sorting the best option for each purchase produces the largest model difference for the selected limit. Alternatives are not combined, and prices stay constant. Brand-name discounts are excluded because a name is not evidence of real impact.")
            st.caption("Results use current model factors, which may differ from older saved estimates. Actual cost, suitability, availability and life-cycle impact are not evaluated.")
        st.download_button("Download experiment JSON", lab.export_experiment(state.purchases, month, max_changes, state.uncertainty_band / 100, dt.datetime.now(dt.timezone.utc)), file_name=f"shopimpact-experiment-{month[0]}-{month[1]:02d}.json", mime="application/json", key="lab_download_experiment")
        st.caption("The download includes this month's brands, dates and prices plus model factors. Personal notes are excluded. No external emissions service is called; hosted deployments process inputs on the app server.")
    with model:
        st.markdown("### See what drives a number")
        left, right = st.columns(2)
        product = left.selectbox("Product category", list(lg.PRODUCTS), key="lab_product")
        price = left.number_input("Price in USD", min_value=0.0, max_value=float(lg.MAX_PRICE_USD), value=50.0, step=5.0, key="lab_price")
        conditions = ["New"]
        if lg.PRODUCTS[product]["second_hand"]:
            conditions.append("Second-hand")
        if lg.PRODUCTS[product]["refurbished"]:
            conditions.append("Refurbished")
        if state.get("lab_condition") not in conditions:
            state.lab_condition = "New"
        condition = left.selectbox("Item condition", conditions, key="lab_condition")
        brand = right.text_input("Brand or shop for model matching", value="Local shop", key="lab_brand", max_chars=120)
        packaging = right.checkbox("Minimal packaging assumption", key="lab_packaging")
        band = right.slider("Assumed uncertainty band (%)", 0, 50, value=30, step=5, key="lab_band") / 100
        experiment = lab.model_experiment(product, price, condition, brand, packaging, band)
        factors = experiment["factors"]
        st.metric("Illustrative estimate", f"{factors['co2_kg']:.2f} kg CO₂e")
        st.code(f"{price:.2f} USD × {factors['multiplier']} category × {factors['condition_factor']} condition × {factors['brand_factor']} brand × {factors['packaging_factor']} packaging = {factors['co2_kg']:.3f} kg CO₂e", language=None)
        st.caption(f"Assumed range: {experiment['range_kg'][0]:.1f}–{experiment['range_kg'][1]:.1f} kg. The band is a user-selected sensitivity assumption, not a statistical confidence interval.")
        if factors["curated_brand_match"]:
            st.info("This name triggers a fixed example-brand factor. It is not a certification or verified environmental comparison.")
        st.markdown("#### Change one input at a time")
        frame = pd.DataFrame(experiment["scenarios"]).rename(columns={"scenario": "Scenario", "estimate_kg": "Estimate (kg CO₂e)", "difference_kg": "Change from baseline (kg)"})
        sensitivity_chart = alt.Chart(frame).mark_bar(
            color=CHART_COLORS[state.display_mode]["line"], cornerRadiusEnd=3,
        ).encode(
            x=alt.X("Estimate (kg CO₂e):Q", title="Illustrative estimate · kg CO₂e"),
            y=alt.Y("Scenario:N", sort=None, title=None),
            tooltip=["Scenario:N", "Estimate (kg CO₂e):Q", "Change from baseline (kg):Q"],
        ).properties(height=220)
        st.altair_chart(style_chart(sensitivity_chart, state.display_mode), width="stretch")
        st.table(frame)
        st.caption("Lower price directly lowers this spend-based estimate. That does not establish that a cheaper real product has a smaller footprint. Scenarios are independent, not additive.")
    with coverage:
        st.markdown("### Know what your journal covers")
        scope = st.radio("Coverage scope", ["Selected month", "Entire journal"], horizontal=True, key="lab_coverage_scope")
        items = purchases if scope == "Selected month" else state.purchases
        result = lab.journal_coverage(items)
        cols = st.columns(3)
        cols[0].metric("Purchase records", result["purchases"])
        cols[1].metric("Distinct purchase dates", result["purchase_dates"])
        cols[2].metric("Intent tags present", f"{result['intent_coverage_pct']:.0f}%")
        st.write(f"{len(result['categories'])} categories · {result['months']} months represented · {result['untagged_intents']} entries without a need/want/gift tag.")
        if result["first_date"]:
            st.caption(f"Purchase dates run from {result['first_date']} to {result['last_date']}.")
        if result["sources"]:
            st.dataframe(pd.DataFrame([{"Source": source, "Records": count} for source, count in result["sources"].items()]), hide_index=True, width="stretch")
        if result["sources"].get("demo"):
            st.info(f"{result['sources']['demo']} records are synthetic demo entries. Keep them separate from real-use evidence in your portfolio.")
        if result["missing_months"]:
            st.warning("Months without entries between your first and last recorded month: " + ", ".join(result["missing_months"]))
        elif result["months"] < 2:
            st.caption("At least two months with entries are needed for a month-to-month comparison.")
        st.caption("Coverage describes the data entered here. It cannot establish that every purchase was recorded, that estimates are accurate, or that habits changed.")
    whats_next("views/swaps_plan.py", "Swaps and plan", "Explore an alternative or plan a future purchase.")


render()
