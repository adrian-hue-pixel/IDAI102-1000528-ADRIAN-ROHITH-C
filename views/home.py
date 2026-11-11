"""Purchase workspace, balanced monthly snapshot, and Tilly companion."""

import math

import streamlit as st

import logic as lg
from ui import actions
from ui.common import (
    app_today,
    money,
    monthly_summary,
    page_header,
    render_stat_chip,
    render_state_guidance,
    render_svg,
    render_tilly,
    whats_next,
)
from ui.illustrations import cached_footprint_svg, cached_plant_svg
from ui.studio import home_hero, render_tools

PAGE_NEXT = ("views/dashboard.py", "Dashboard", "Explore monthly trends and insights.")


def _show_another_tip() -> None:
    state = st.session_state
    state.tip_offset += 1
    state.tip = lg.tip_of_day(
        state.tip_view_category, app_today(), state.tip_offset, state.tip
    )


@st.fragment
def _render_tip() -> None:
    state = st.session_state
    today = app_today()
    if state.get("tip_key") != (today.isoformat(), state.tip_view_category):
        state.tip = lg.tip_of_day(
            state.tip_view_category, today, state.tip_offset, state.get("tip", "")
        )
        state.tip_key = (today.isoformat(), state.tip_view_category)
    with st.container(key="home-tip", border=True):
        st.markdown("#### One idea to try")
        st.write(state.tip)
        st.button(
            "Show another tip",
            key="show_another_tip",
            on_click=_show_another_tip,
        )


def render() -> None:
    page_header(
        "Home",
        "Your purchases, patterns and possibilities.",
        action_label="View dashboard",
        action_page=PAGE_NEXT[0],
    )
    state = st.session_state
    today = app_today()
    mode = state.display_mode
    symbol, rate = lg.CURRENCIES[state.currency_name]
    reduce_motion = bool(state.reduce_motion)
    month = state.view_month
    goal = lg.goal_for_month(state.goal_history, month, float(state.goal_kg))

    st.markdown(home_hero(), unsafe_allow_html=True)
    with st.container(key="home-hero-actions"):
        _, first, second, _ = st.columns([1, 1.5, 1.5, 1])
        first.markdown('<a class="studio-primary-link" href="#purchase-inputs">Log a purchase <span>↗</span></a>', unsafe_allow_html=True)
        second.page_link("views/dashboard.py", label="Explore my dashboard", icon=":material/arrow_forward:")
    render_tools()
    with st.expander("Journal status and getting started"):
        render_state_guidance("Home")
    if not state.guide_dismissed:
        with st.container(key="guided-tour", border=True):
            guide_copy, guide_action = st.columns([5, 1])
            guide_copy.markdown("**New here?** Log a purchase, then test an alternative in Impact Lab.")
            if guide_action.button("Dismiss tour", key="dismiss_guided_tour"):
                state.guide_dismissed = True
                st.rerun()

    st.markdown('<span id="purchase-inputs"></span>', unsafe_allow_html=True)
    st.markdown("## Add a purchase")
    st.caption("Start with a category. The estimate updates as you explore.")
    state.setdefault("entry_mode", "Log a purchase")
    entry_mode = st.radio(
        "Entry type",
        ["Log a purchase", "Plan a purchase"],
        horizontal=True,
        index=["Log a purchase", "Plan a purchase"].index(state.entry_mode),
        key="entry_mode",
    )
    favorites = state.get("favorites", [])
    if favorites:
        favorite_index = st.selectbox(
            "Quick add",
            [-1, *range(len(favorites))],
            format_func=lambda index: (
                "Choose a saved purchase"
                if index < 0
                else f"{favorites[index]['product_type']} · {favorites[index]['brand']}"
            ),
            key="quick_add_selection",
        )
        if st.button(
            "Use quick add",
            key="apply_quick_add",
            disabled=favorite_index < 0,
        ):
            favorite = favorites[favorite_index]
            state.entry_product_type = favorite["product_type"]
            state[f"brand_{favorite['product_type']}"] = favorite["brand"]
            state.price = favorite["price_usd"] * rate
            state.entry_condition = favorite["condition"]
            state.entry_packaging = favorite["low_packaging"]
            state.entry_note = ""
            state.entry_intent = favorite.get("intent", "")
            st.rerun()
    with st.container(key="purchase-entry"):
        product_type = st.radio(
            "Product type",
            list(lg.PRODUCTS),
            horizontal=True,
            index=list(lg.PRODUCTS).index(state.get("entry_product_type", next(iter(lg.PRODUCTS)))),
            key="entry_product_type",
        )
        state.setdefault("entry_condition", "New")
        state.setdefault("entry_packaging", False)
        state.setdefault("price", 25.0 * rate)
        cols = st.columns([1.15, 1, 1, 1])
        with cols[0]:
            brand_options = list(lg.PRODUCTS[product_type]["brands"])
            selected_brand = state.get(f"brand_{product_type}")
            if selected_brand and selected_brand not in brand_options:
                brand_options.append(selected_brand)
            brand = st.selectbox(
                "Brand or shop",
                brand_options,
                index=brand_options.index(selected_brand) if selected_brand else None,
                placeholder="Choose or type a name…",
                key=f"brand_{product_type}",
                accept_new_options=True,
                help="Examples are illustrative only, not endorsements or certifications.",
            ) or ""
        with cols[1]:
            price = st.number_input(
                f"Price ({symbol})",
                min_value=0.0,
                max_value=float(lg.MAX_PRICE_USD * rate),
                step=1.0 if rate <= 2 else 10.0,
                value=float(state.price),
                key="price",
            )
        with cols[2]:
            purchase_date = st.date_input(
                "Purchase date",
                value=today,
                min_value=lg.MIN_PURCHASE_DATE,
                max_value=lg.max_purchase_date(
                    today, is_plan=entry_mode == "Plan a purchase"
                ),
                key="purchase_date",
            )
        with cols[3]:
            condition = st.selectbox(
                "Condition",
                list(lg.CONDITION_FACTORS),
                index=list(lg.CONDITION_FACTORS).index(state.entry_condition),
                key="entry_condition",
            )
        low_packaging = st.checkbox(
            "Minimal packaging",
            value=bool(state.entry_packaging),
            key="entry_packaging",
            help="An illustrative model factor, not a verified packaging assessment.",
        )
        with st.expander("Optional details · notes, intent and repeat purchases"):
            repeat_monthly = st.checkbox(
                "Repeat monthly through the current month",
                key="repeat_monthly",
                disabled=entry_mode != "Log a purchase",
                help="Creates at most 12 labelled entries.",
            )
            note = ""
            intent = ""
            if entry_mode == "Log a purchase":
                state.setdefault("entry_note", "")
                state.setdefault("entry_intent", "")
                note = st.text_input(
                    "Note (optional)",
                    max_chars=lg.MAX_NOTE_LENGTH,
                    key="entry_note",
                )
                intent = st.selectbox(
                    "Was this a need or a want?",
                    ["", *lg.INTENTS],
                    format_func=lambda value: value or "Not set",
                    key="entry_intent",
                )
        price_usd = price / rate
        estimate = lg.calculate_impact(
            product_type, price_usd, condition, brand, low_packaging
        )
        rating = lg.rate_impact(estimate["co2_kg"], price_usd)
        estimate_low, estimate_high = lg.estimate_range(
            estimate["co2_kg"], state.uncertainty_band / 100
        )
        errors = lg.validate_purchase(
            product_type,
            brand,
            price_usd,
            condition,
            purchase_date,
            low_packaging,
            is_plan=entry_mode == "Plan a purchase",
            today=today,
            note=note,
            intent=intent,
        )
        preview, action_col = st.columns([1.6, 1], vertical_alignment="center")
        with preview:
            st.markdown(
                f'<div class="estimate-preview"><span>Estimated footprint</span>'
                f'<strong>{estimate["co2_kg"]:.1f} kg CO₂e</strong>'
                f'<span class="pill {rating}">{rating} impact</span>'
                "<p>Illustrative estimate, not measured product data.</p></div>",
                unsafe_allow_html=True,
            )
            st.caption(
                f"Likely range: between {estimate_low:.1f} and "
                f"{estimate_high:.1f} kilograms CO₂e."
            )
            with st.expander("Why this number?"):
                st.write(
                    f"Likely range: between {estimate_low:.1f} and "
                    f"{estimate_high:.1f} kilograms CO₂e."
                )
                st.write(
                    f"{price_usd:.2f} USD × {estimate['multiplier']} "
                    "(product multiplier) × "
                    f"{estimate['condition_factor']} (condition) × "
                    f"{estimate['brand_factor']} (brand) × "
                    f"{estimate['packaging_factor']} (packaging)"
                )
                st.caption("Illustrative factors, not verified product data.")
                st.caption(
                    "The multipliers are spend-based assumptions, not measurements."
                )
        with action_col:
            st.markdown("**Save this choice**")
            st.caption("Details stay filled in for your next entry.")
            if entry_mode == "Log a purchase":
                if st.button(
                    "Log this purchase",
                    key="log_purchase",
                    type="primary",
                    disabled=bool(errors),
                    use_container_width=True,
                ):
                    actions.log_purchase(
                        product_type,
                        brand,
                        price_usd,
                        condition,
                        low_packaging,
                        purchase_date,
                        repeat_monthly,
                        goal,
                        note=note,
                        intent=intent,
                    )
            else:
                if st.button(
                    "Save this plan",
                    key="save_plan",
                    type="primary",
                    disabled=bool(errors),
                    use_container_width=True,
                ):
                    actions.save_plan(
                        product_type,
                        brand,
                        price_usd,
                        condition,
                        low_packaging,
                        purchase_date,
                    )
        if errors:
            st.caption(" ".join(errors))
        alternatives = lg.suggest_alternatives(
            product_type, brand, price_usd, condition, low_packaging
        )
        with st.expander("Optional swaps to explore"):
            for idea in alternatives["what_if"][:3]:
                st.write(
                    f"{idea['label']} · about {idea['saved_kg']:.1f} kg lower "
                    "in this illustrative estimate"
                )
            st.caption("Suggestions are optional ideas, not product claims.")
        if st.button(
            "Save as quick add",
            key="save_quick_add",
            disabled=not brand.strip(),
        ):
            favorite = {
                "product_type": product_type,
                "brand": brand.strip(),
                "price_usd": price_usd,
                "condition": condition,
                "low_packaging": low_packaging,
                "intent": intent,
            }
            if favorite not in state.favorites:
                state.favorites.append(favorite)
            st.toast("Quick add saved for this browser session.")

    if state.get("last_event") and state.last_event.get("eco"):
        event = state.last_event
        plant = cached_plant_svg(4, mode, not reduce_motion)
        static_plant = cached_plant_svg(4, mode, False)
        plant = plant.replace(
            "</svg>", f"<!-- purchase:{event['purchase_id']} --></svg>"
        )
        static_plant = static_plant.replace(
            "</svg>", f"<!-- purchase:{event['purchase_id']} --></svg>"
        )
        st.markdown(
            '<section class="eco-win" aria-label="A small eco win">'
            "<h3>A small eco win</h3></section>",
            unsafe_allow_html=True,
        )
        for badge_name in event["new_badges"]:
            st.success(f"Badge unlocked: {badge_name}")
        render_svg(
            plant,
            "Animated Turtle-drawn sprout celebrating this low-impact illustrative choice.",
            220,
            static_svg=static_plant,
        )
        st.caption("This is an illustrative estimate, not a measured product claim.")
        if st.button("Dismiss celebration", key="dismiss_purchase_feedback"):
            state.last_event = None

    summary = monthly_summary(state.purchases, month)
    month_index = state.purchase_month_index
    previous = lg.monthly_summary(
        state.purchases, lg.previous_month(month), month_index
    )
    st.markdown("## This month")
    st.caption("Your purchases at a glance.")
    ratio = summary["co2_kg"] / goal if goal else 0
    monthly_low, monthly_high = lg.estimate_range(
        summary["co2_kg"], state.uncertainty_band / 100
    )
    delta = summary["co2_kg"] - previous["co2_kg"]
    rows = lg.monthly_totals(state.purchases, month_index)[-6:]
    chips = st.columns(3)
    stats = (
        ("Spent", money(summary["spend_usd"], rate, symbol), [row["spend_usd"] * rate for row in rows]),
        ("Purchases", str(summary["n"]), [len(month_index.get(row["ym"], [])) for row in rows]),
        ("vs last month", f"{delta:+.1f} kg", [row["co2_kg"] for row in rows]),
    )
    for col, (label, value, trend) in zip(chips, stats):
        with col:
            render_stat_chip(label, value, trend)

    overview, companion = st.columns([1.55, 1], vertical_alignment="top")
    with overview, st.container(key="month-overview", border=True):
        st.markdown(
            f'<div class="home-hero"><div><span>MONTHLY MODEL ESTIMATE</span>'
            f'<strong>{summary["co2_kg"]:.1f}<small> kg CO₂e</small></strong>'
            f'<span>{summary["n"]} purchase(s) · {monthly_low:.0f}–{monthly_high:.0f} kg model range</span></div>'
            f'<div class="goal-ring" style="--goal-angle:{min(ratio, 1.0) * 360:.1f}deg" '
            f'role="img" aria-label="{summary["co2_kg"]:.1f} kilograms CO2e '
            f'against a personal monthly goal of {goal:.0f} kilograms">'
            f'<span>{min(ratio, 1):.0%}</span></div></div>',
            unsafe_allow_html=True,
        )
        st.progress(min(ratio, 1.0), text=f"{summary['co2_kg']:.1f} of {goal:.0f} kg personal monthly goal")
        st.caption("Illustrative model. Your goal is a personal benchmark.")
        with st.expander("Understand this snapshot"):
            st.caption(
                f"Goal ring: {summary['co2_kg']:.1f} kg CO₂e compared with your "
                f"{goal:.0f} kg monthly goal; estimates are illustrative."
            )
            st.caption(
                f"Monthly estimate: about {summary['co2_kg']:.0f} kg, model range between "
                f"{monthly_low:.0f} and {monthly_high:.0f} kilograms."
            )
            st.caption("The model range is an assumption, not a statistical confidence interval.")
    low_count = sum(item["rating"] == "Low" for item in month_index.get(month, []))
    badges = lg.evaluate_badges(state.purchases, month, goal, month_index, goal_history=state.goal_history)
    newest = next((badge for badge in reversed(badges) if badge["earned"]), None)
    with companion, st.container(key="home-companion", border=True):
        mood = "curious" if not summary["n"] else "happy" if ratio <= .8 else "encouraging"
        avatar, introduction = st.columns([1, 1.4], vertical_alignment="center")
        with avatar:
            render_tilly(mood, mode, reduce_motion)
        with introduction:
            st.markdown('<div class="companion-copy"><strong>Meet Tilly</strong>'
                        '<p>A little company for your daily choices.</p></div>', unsafe_allow_html=True)
        st.markdown("**Newest badge**")
        if newest:
            st.caption(f"{newest['name']} · {newest['desc']}")
        else:
            st.caption("Your first entry starts the journey.")
        st.page_link("views/garden_badges.py", label="Visit your garden →")
        st.page_link("views/ask_tilly.py", label="Ask Tilly →")

    with st.container(key="home-progress-row"):
        plant_col, trail_col, idea_col = st.columns([1, 1, 1.25], vertical_alignment="top")
        with plant_col, st.container(key="home-plant", border=True):
            leaves = min(8, max(1, low_count + 3))
            st.markdown("#### Growing plant")
            render_svg(cached_plant_svg(leaves, mode, not reduce_motion),
                       f"Turtle-drawn plant with {leaves} leaves showing monthly progress.", 180,
                       static_svg=cached_plant_svg(leaves, mode, False))
            st.caption(f"{low_count} lower-estimate choices this month.")
        with trail_col, st.container(key="home-trail", border=True):
            prints = max(1, min(8, math.ceil(ratio * 5)))
            st.markdown("#### Footprint trail")
            render_svg(cached_footprint_svg(prints, mode, not reduce_motion, total=8),
                       f"Turtle-drawn footprint trail with {prints} prints.", 180,
                       static_svg=cached_footprint_svg(prints, mode, False, total=8))
            st.caption("A playful view of your personal goal.")
        with idea_col:
            _render_tip()
    if st.button("Try with demo data", key="home_load_demo", type="secondary"):
        actions.load_demo()
        st.rerun()

    whats_next(*PAGE_NEXT)


render()
