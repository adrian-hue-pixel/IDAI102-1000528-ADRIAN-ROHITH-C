"""App preferences, data controls, privacy, and model transparency."""

import json

import streamlit as st

import browser_persistence as bp
import browser_storage as bs
import data_io as dio
import logic as lg
from styles import DISPLAY_MODES
from ui.actions import load_demo
from ui.common import (
    app_today,
    page_header,
    refresh_purchase_month_index,
    update_goal,
    update_preference,
    whats_next,
)
from ui.undo import capture_state, record_change

NEXT = ("views/home.py", "Home", "Return to your monthly workspace.")
MAX_BACKUP_BYTES = 2 * 1024 * 1024
SETTING_WIDGET_KEYS = {
    "display_mode": "settings_display_mode",
    "currency_name": "settings_currency",
    "goal_kg": "settings_goal",
    "uncertainty_band": "settings_uncertainty_band",
    "text_size": "settings_text_size",
    "dyslexia_font": "settings_dyslexia_font",
    "sound_enabled": "settings_sound_enabled",
    "reduce_motion": "settings_reduce_motion",
}


def _set_goal(value: int) -> None:
    update_goal(value)


def render() -> None:
    state = st.session_state
    pending_widget_settings = state.pop("restore_settings_widget_values", None)
    if pending_widget_settings:
        for widget_key, value in pending_widget_settings.items():
            state[widget_key] = value
    # Duplicate controls share canonical preferences; keyed widgets ignore index
    # after their first render, so synchronize them before they are constructed.
    for preference, widget_key in SETTING_WIDGET_KEYS.items():
        if state.get(widget_key) != state[preference]:
            state[widget_key] = state[preference]
    restore_message = state.pop("full_backup_restore_message", None)
    if restore_message:
        st.success(restore_message)
    model_notice = state.pop("full_backup_model_notice", None)
    if model_notice:
        st.info(model_notice)

    page_header(
        "Settings and about",
        "Choose how ShopImpact looks and review its data, privacy, and estimate limits.",
        action_label="Return Home",
        action_page=NEXT[0],
    )
    st.markdown("## Appearance and access")
    st.markdown(
        '<div class="mode-gallery" aria-label="Available display modes">'
        '<div class="mode-sample mode-day"><i></i><strong>Light</strong><span>A bright everyday workspace</span></div>'
        '<div class="mode-sample mode-night"><i></i><strong>Dark</strong><span>A softer after-dark view</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.caption("Choose a display mode below. Reduce motion pauses decorative animation; your operating system’s motion preference is respected too.")
    left, right = st.columns(2)
    with left:
        st.radio(
            "Display mode",
            list(DISPLAY_MODES),
            index=list(DISPLAY_MODES).index(state.display_mode),
            key="settings_display_mode",
            on_change=update_preference,
            args=("display_mode", "settings_display_mode"),
        )
        st.selectbox(
            "Currency",
            list(lg.CURRENCIES),
            index=list(lg.CURRENCIES).index(state.currency_name),
            key="settings_currency",
            on_change=update_preference,
            args=("currency_name", "settings_currency"),
        )
    with right:
        st.slider(
            "Monthly CO₂ goal (kg)",
            20,
            300,
            value=int(state.goal_kg),
            step=5,
            key="settings_goal",
            on_change=update_preference,
            args=("goal_kg", "settings_goal"),
        )
        st.slider(
            "Estimate range",
            0,
            50,
            value=int(state.uncertainty_band),
            step=5,
            format="%d%%",
            key="settings_uncertainty_band",
            on_change=update_preference,
            args=("uncertainty_band", "settings_uncertainty_band"),
            help="A broader range shows more uncertainty around each illustrative estimate.",
        )
        st.select_slider(
            "Text size",
            options=["S", "M", "L", "XL"],
            value=state.text_size,
            key="settings_text_size",
            on_change=update_preference,
            args=("text_size", "settings_text_size"),
        )
        st.checkbox(
            "Dyslexia-friendly font",
            value=state.dyslexia_font,
            key="settings_dyslexia_font",
            on_change=update_preference,
            args=("dyslexia_font", "settings_dyslexia_font"),
        )
        st.checkbox(
            "Badge unlock sound",
            value=state.sound_enabled,
            key="settings_sound_enabled",
            on_change=update_preference,
            args=("sound_enabled", "settings_sound_enabled"),
        )
        st.checkbox(
            "Reduce motion",
            value=state.reduce_motion,
            key="settings_reduce_motion",
            on_change=update_preference,
            args=("reduce_motion", "settings_reduce_motion"),
        )
    st.markdown("## Goal presets")
    suggestions = lg.suggested_goal_presets(
        state.purchases, state.get("purchase_month_index")
    )
    if suggestions is not None:
        average, presets = suggestions
        st.caption(
            f"These suggestions use the average of your last "
            f"{min(3, len(lg.monthly_totals(state.purchases)))} logged months "
            f"({average:.1f} kg CO₂e/month); each is rounded to the nearest 5 kg "
            "and kept between 20 and 300 kg."
        )
        preset_cols = st.columns(3)
        for col, (label, value) in zip(preset_cols, presets.items()):
            col.caption(f"{value} kg")
            col.button(
                label,
                key=f"settings_goal_suggestion_{value}",
                on_click=_set_goal,
                args=(value,),
            )
    else:
        preset_cols = st.columns(3)
        for col, label, value in zip(
            preset_cols,
            ("Light · 120 kg", "Balanced · 80 kg", "Ambitious · 40 kg"),
            (120, 80, 40),
        ):
            col.button(
                label,
                key=f"settings_goal_preset_{value}",
                on_click=_set_goal,
                args=(value,),
            )

    st.markdown("## First-run guide")
    if st.button("Replay the Home → Dashboard tour", key="replay_tour"):
        state.guide_dismissed = False
        st.switch_page("views/home.py")

    st.markdown("## Your data")
    st.markdown("### Recent journal actions")
    undo_items = list(reversed(state.get("undo_stack", [])))
    if undo_items:
        for item in undo_items[:10]:
            st.caption(f"• {item['description']}")
    else:
        st.caption("No recent undoable actions.")
    if state.storage_error:
        st.warning(state.storage_error)
    elif state.storage_available:
        st.success(
            f"Browser save available · {len(state.purchases)} purchase(s), "
            f"{len(state.plans)} plan(s)."
        )
    else:
        st.info("Browser storage is unavailable. Your current session remains usable.")
    st.caption(
        "Data is saved in this browser profile when storage is available. "
        "No account, analytics service, or external emissions API is used."
    )
    backup_col, export_col, demo_col = st.columns(3)
    backup_settings = {
        "text_size": state.text_size,
        "dyslexia_font": bool(state.dyslexia_font),
        "sound_enabled": bool(state.sound_enabled),
        "display_mode": state.display_mode,
        "accent_palette": state.accent_palette,
        "currency_name": state.currency_name,
        "goal_kg": int(state.goal_kg),
        "goal_history": state.goal_history,
        "uncertainty_band": int(state.uncertainty_band),
        "month_review_last_visit": state.month_review_last_visit,
        "xp_scoring_notice_dismissed": state.xp_scoring_notice_dismissed,
        "reduce_motion": bool(state.reduce_motion),
        "view_month": state.view_month,
    }
    backup_json = bp.encode_saved_state(
        state.purchases,
        state.guide_dismissed,
        state.achievement_inbox,
        state.plans,
        backup_settings,
    )
    backup_col.download_button(
        "Download full backup (JSON)",
        backup_json,
        file_name=f"shopimpact_backup_{app_today().isoformat()}.json",
        mime="application/json",
        key="download_full_backup",
    )
    export_col.download_button(
        "Export purchase CSV",
        dio.export_purchases(state.purchases),
        "shopimpact_purchases.csv",
        "text/csv",
        disabled=not state.purchases,
    )
    st.caption(
        "The downloaded backup file contains everything saved in this browser "
        "and is not uploaded anywhere."
    )
    upload = st.file_uploader(
        "Restore full backup",
        type=["json"],
        max_upload_size=2,
        key="restore_full_backup_upload",
        help="Choose a ShopImpact JSON backup (maximum 2 MB).",
    )
    if upload is not None:
        backup_bytes = upload.getvalue()
        if len(backup_bytes) > MAX_BACKUP_BYTES:
            st.error("This backup is larger than the 2 MB upload limit.")
        else:
            try:
                (
                    restored_purchases,
                    restored_guide_dismissed,
                    skipped_rows,
                    restored_achievements,
                    restored_plans,
                    restored_settings,
                ) = bp.decode_saved_state(
                    backup_bytes.decode("utf-8"),
                    today=app_today(),
                )
            except (UnicodeDecodeError, TypeError, ValueError) as exc:
                st.error(f"This backup could not be restored. ({exc})")
            else:
                backup_payload = json.loads(backup_bytes.decode("utf-8"))
                old_model_version = backup_payload.get("model_version")
                if not isinstance(old_model_version, str) or not old_model_version:
                    old_model_version = "unknown"
                st.markdown("#### Backup preview")
                st.caption(
                    f"{len(restored_purchases)} purchase(s) · "
                    f"{len(restored_plans)} plan(s) · "
                    f"{len(restored_achievements)} achievement(s)"
                )
                restored_dates = [
                    item["date"]
                    for item in [*restored_purchases, *restored_plans]
                ]
                if restored_dates:
                    date_range = (
                        f"{min(restored_dates).isoformat()} to "
                        f"{max(restored_dates).isoformat()}"
                    )
                else:
                    date_range = "No purchase or plan dates"
                st.caption(f"Date range: {date_range}")
                if skipped_rows:
                    st.warning(
                        f"{len(skipped_rows)} purchase row(s) will be skipped:"
                    )
                    for row_number, reason in skipped_rows:
                        st.caption(f"Row {row_number}: {reason}")
                else:
                    st.caption("Skipped rows: none.")
                st.info(
                    "This will replace the current purchases, plans, achievement "
                    "inbox, guide preference, and saved preferences. "
                    f"Current → backup: {len(state.purchases)} → "
                    f"{len(restored_purchases)} purchases, {len(state.plans)} → "
                    f"{len(restored_plans)} plans, "
                    f"{len(state.achievement_inbox)} → "
                    f"{len(restored_achievements)} achievements."
                )
                empty_restore_blocked = (
                    not restored_purchases
                    and not restored_plans
                    and bool(state.purchases)
                )
                if empty_restore_blocked:
                    st.warning(
                        "This backup has no purchases or plans, so it cannot replace "
                        "a non-empty purchase journal."
                    )
                confirmed = st.checkbox(
                    "I understand this will replace the listed data.",
                    key="confirm_full_backup_restore",
                )
                if st.button(
                    "Restore full backup",
                    key="confirm_full_backup_restore_action",
                    type="primary",
                    disabled=not confirmed or empty_restore_blocked,
                ):
                    before = capture_state(state)
                    record_change(before, "Restore full backup", state)
                    state.purchases = restored_purchases
                    state.next_id = (
                        max((item["id"] for item in restored_purchases), default=0)
                        + 1
                    )
                    state.plans = restored_plans
                    state.achievement_inbox = restored_achievements
                    state.guide_dismissed = restored_guide_dismissed
                    state.settings = {**state.settings, **restored_settings}
                    state.goal_history = restored_settings.get(
                        "goal_history", state.goal_history
                    )
                    if "goal_kg" in restored_settings:
                        state.goal_kg = restored_settings["goal_kg"]
                    state.month_review_last_visit = restored_settings.get(
                        "month_review_last_visit", state.month_review_last_visit
                    )
                    state.xp_scoring_notice_dismissed = restored_settings.get(
                        "xp_scoring_notice_dismissed",
                        state.xp_scoring_notice_dismissed,
                    )
                    for setting, widget_key in SETTING_WIDGET_KEYS.items():
                        if setting in restored_settings:
                            state[setting] = restored_settings[setting]
                    state.restore_settings_widget_values = {
                        SETTING_WIDGET_KEYS[setting]: value
                        for setting, value in restored_settings.items()
                        if setting in SETTING_WIDGET_KEYS
                    }
                    state.last_event = None
                    state.plan_feedback = None
                    refresh_purchase_month_index(state)
                    state.raw_saved_state = None
                    state.browser_storage_signature = None
                    state.persistence_locked = False
                    state.storage_error = None
                    state.full_backup_restore_message = (
                        "Full backup restored. You can undo this change."
                    )
                    if old_model_version != lg.MODEL_VERSION:
                        state.full_backup_model_notice = (
                            f"Estimates were recalculated with model "
                            f"{lg.MODEL_VERSION} (file was {old_model_version})."
                        )
                    st.rerun()
    if demo_col.button("Load labelled synthetic demo data", key="settings_load_demo"):
        load_demo()
        st.rerun()
    if st.button("Clear all purchases in this session", key="settings_clear_purchases"):
        state.confirm_clear_purchases = True
    if state.get("confirm_clear_purchases"):
        st.warning("This removes the purchase journal and plans from the current session.")
        confirm, cancel = st.columns(2)
        if confirm.button("Confirm clear", key="settings_confirm_clear"):
            before = capture_state(state)
            removed_count = len(state.purchases)
            state.purchases = []
            state.plans = []
            state.next_id = 1
            state.last_event = None
            refresh_purchase_month_index(state)
            record_change(
                before,
                f"Cleared {removed_count} purchases and plans.",
                state,
            )
            state.confirm_clear_purchases = False
            st.rerun()
        if cancel.button("Cancel", key="settings_cancel_clear"):
            state.confirm_clear_purchases = False
    if st.button(
        "Clear saved browser data",
        key="settings_clear_saved",
        disabled=not state.storage_available,
    ):
        state.confirm_clear_saved = True
    if state.get("confirm_clear_saved"):
        st.warning("This clears ShopImpact data saved for this app in this browser.")
        confirm_saved, cancel_saved = st.columns(2)
        if confirm_saved.button("Confirm clear saved data", key="settings_confirm_saved"):
            before = capture_state(state)
            try:
                ready, error = bs.remove_saved_value()
            except (TypeError, ValueError, RuntimeError) as exc:
                ready, error = True, str(exc)
            if not ready:
                state.storage_pending = True
                state.clear_saved_data_pending = True
            elif error:
                state.storage_error = f"Saved data could not be cleared. ({error})"
            else:
                state.purchases = []
                state.plans = []
                refresh_purchase_month_index(state)
                state.achievement_inbox = []
                state.browser_storage_signature = None
                state.guide_dismissed = False
                record_change(
                    before,
                    f"Cleared saved browser data ({len(before['purchases'])} purchases).",
                    state,
                )
            state.confirm_clear_saved = False
            st.rerun()
        if cancel_saved.button("Cancel", key="settings_cancel_saved"):
            state.confirm_clear_saved = False

    with st.expander("About the numbers"):
        st.markdown(
            "Impact is calculated from price and illustrative category, condition, "
            "brand-name, and packaging factors. This is a teaching model, not a "
            "product life-cycle assessment. Results are estimates, not measurements, "
            "rankings, offsets, or verified product data."
        )
        st.caption(
            "Brand-name matches are not certification or endorsement. Currency "
            "conversion rates are approximate and fixed for this demonstration."
        )
        st.caption(
            f"Estimate model {lg.MODEL_VERSION} · current range ±"
            f"{state.uncertainty_band}%."
        )
    with st.expander("Privacy and your data"):
        st.markdown(
            "When browser storage is available, purchases, plans, the guide preference, "
            "achievement inbox, and selected preferences are saved in localStorage "
            "for this app origin. While the app is open, Streamlit processes active "
            "session data to calculate estimates and render pages. Avoid entering "
            "sensitive personal information."
        )
        st.caption(
            "Purchase notes are stored only in this browser and exported only in "
            "your own CSV or backup."
        )
    with st.expander("How it was built"):
        st.markdown(
            "The on-screen Eco Garden, footprint trail, and growing plant are "
            "animated SVGs generated by `SvgTurtle` in `turtle_svg.py`; Tilly is a "
            "theme-aware vector SVG from `tilly_svg.py`. The original Pillow-backed "
            "TurtleCanvas remains for badges and PNG exports. `logic.py` contains "
            "the illustrative calculations and is unchanged by the interface."
        )
    st.caption(
        f"Current currency: {state.currency_name} · Current month: "
        f"{lg.month_label(state.view_month)} · Rate is approximate."
    )
    whats_next(*NEXT)


render()
