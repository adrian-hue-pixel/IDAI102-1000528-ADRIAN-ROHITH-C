"""Monthly story and portable share-card downloads."""

from io import BytesIO

import streamlit as st
from PIL import Image

import logic as lg
import summary_image
from ui.common import app_today, money, monthly_summary, page_header, whats_next

NEXT = ("views/settings_about.py", "Settings and about", "Review preferences and data controls.")


def render() -> None:
    page_header(
        "Month in review",
        "Close the month with a useful reflection and a snapshot you can keep.",
        action_label="Open settings",
        action_page=NEXT[0],
    )
    state = st.session_state
    state.month_review_last_visit = app_today().isoformat()
    state.setdefault("settings", {})[
        "month_review_last_visit"
    ] = state.month_review_last_visit
    month = state.view_month
    summary = monthly_summary(state.purchases, month)
    swap_result = lg.swap_savings(state.purchases, month)
    goal = lg.goal_for_month(state.goal_history, month, float(state.goal_kg))
    mode = state.display_mode
    earned = [
        badge["name"]
        for badge in lg.evaluate_badges(
            state.purchases,
            month,
            goal,
            state.purchase_month_index,
            goal_history=state.goal_history,
        )
        if badge["earned"]
    ]
    st.markdown(f"## {lg.month_label(month)}")
    if summary["n"] == 0:
        st.markdown(
            '<div class="studio-empty"><span class="section-label">A MOMENT TO REFLECT</span>'
            '<h3>This chapter is still unwritten.</h3><p>Your monthly story will appear '
            'when this month has a purchase. Pick another month above, or add your '
            'first entry to start this one.</p></div>',
            unsafe_allow_html=True,
        )
        st.page_link("views/home.py", label="Add a purchase →")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Purchases", summary["n"])
        col2.metric("Estimated CO₂e", f"{summary['co2_kg']:.1f} kg")
        col3.metric("Spent", money(summary["spend_usd"], lg.CURRENCIES[state.currency_name][1], lg.CURRENCIES[state.currency_name][0]))
        ratio = summary["co2_kg"] / goal if goal else 0
        swap_story = (
            f'<p>Through {swap_result["count"]} swap(s), the illustrative estimate '
            f'is {swap_result["saved_kg"]:.1f} kg CO₂e lower '
            f'({swap_result["saved_equivalents"]["car_km"]:.1f} car-km equivalent); '
            "this is not a verified saving.</p>"
            if swap_result["saved_kg"] > 0
            else ""
        )
        st.markdown(
            f'<div class="review-story"><strong>Your month, in brief</strong>'
            f'<p>You logged {summary["n"]} purchase(s), with an illustrative estimate '
            f'of {summary["co2_kg"]:.1f} kg CO₂e. That is {ratio:.0%} of your personal '
            f'{goal:.0f} kg goal. Estimates are not measurements or product comparisons.</p>'
            f'{swap_story}'
            f'<p>Badges earned this month: {", ".join(earned) if earned else "none yet"}.</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("### What shaped the estimate?")
        top_categories = sorted(
            summary["by_category"].items(),
            key=lambda pair: pair[1]["co2_kg"],
            reverse=True,
        )[:3]
        cards = st.columns(max(1, len(top_categories)))
        for card, (category, data) in zip(cards, top_categories):
            with card, st.container(border=True):
                st.markdown(f"#### {category}")
                st.metric("Estimated CO₂e", f"{data['co2_kg']:.1f} kg")
                st.caption(f"{data['count']} purchase(s) · illustrative estimate")
        if earned:
            st.markdown("### A moment worth celebrating")
            st.write(f"You earned {', '.join(earned)}.")
        else:
            st.markdown("### No badge this month")
            st.write("The journal is yours to use at your own pace.")

        png_data = summary_image.render_monthly_summary(
            lg.month_label(month),
            summary,
            goal,
            earned,
            mode,
            goal_history=state.goal_history,
            month=month,
            swap_savings=swap_result,
        )
        st.markdown("## Keep a reflection")
        st.caption("What surprised you? What would you like to repeat or change? Notes stay in this session; download them to keep a copy.")
        reflection = st.text_area(
            "Your monthly reflection",
            key=f"review_reflection_{month[0]}_{month[1]}",
            max_chars=4000,
            placeholder="One pattern I noticed… One choice I want to try…",
        )
        if reflection.strip():
            reflection_text = (
                f"# ShopImpact reflection for {lg.month_label(month)}\n\n"
                f"Purchases: {summary['n']}\n"
                f"Illustrative estimate: {summary['co2_kg']:.1f} kg CO2e\n\n"
                f"{reflection.strip()}\n\n"
                "Estimates use a learning model and are not measured product data.\n"
            )
            st.download_button(
                "Download reflection",
                reflection_text,
                f"shopimpact_{month[0]}-{month[1]:02d}_reflection.md",
                "text/markdown",
            )
        st.markdown("## Share your snapshot")
        png_col, pdf_col = st.columns(2)
        with png_col:
            st.download_button(
                "Download share image",
                png_data,
                f"shopimpact_{month[0]}-{month[1]:02d}_summary.png",
                "image/png",
                type="primary",
            )
        with pdf_col:
            poster = BytesIO()
            Image.open(BytesIO(png_data)).convert("RGB").save(poster, format="PDF")
            st.download_button(
                "Download poster PDF",
                poster.getvalue(),
                f"shopimpact_{month[0]}-{month[1]:02d}_poster.pdf",
                "application/pdf",
            )
        st.image(
            png_data,
            caption="Illustrative monthly summary",
            alt="Illustrative monthly summary of estimated impact and spending.",
        )
    whats_next(*NEXT)


render()
