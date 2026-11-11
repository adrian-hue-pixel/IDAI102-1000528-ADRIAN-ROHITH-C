"""Session-only undo support for journal and plan mutations."""

from copy import deepcopy

import streamlit as st

MAX_UNDO_ITEMS = 10
SNAPSHOT_KEYS = (
    "purchases",
    "plans",
    "next_id",
    "achievement_inbox",
    "last_event",
    "plan_feedback",
    "guide_dismissed",
    "settings",
    "display_mode",
    "accent_palette",
    "currency_name",
    "goal_kg",
    "goal_history",
    "uncertainty_band",
    "text_size",
    "dyslexia_font",
    "sound_enabled",
    "reduce_motion",
    "view_month",
    "settings_display_mode",
    "settings_accent_palette",
    "settings_currency",
    "settings_goal",
    "settings_uncertainty_band",
    "settings_text_size",
    "settings_dyslexia_font",
    "settings_sound_enabled",
    "settings_reduce_motion",
    "persistence_locked",
    "raw_saved_state",
    "storage_error",
    "browser_storage_signature",
)


def capture_state(state=None) -> dict:
    """Capture the mutable session data affected by journal actions."""
    state = state or st.session_state
    return {
        key: deepcopy(state[key])
        for key in SNAPSHOT_KEYS
        if key in state
    }


def record_change(before: dict, description: str, state=None) -> None:
    """Record a reversible change and announce its undo action."""
    state = state or st.session_state
    stack = list(state.get("undo_stack", []))
    stack.append(
        {
            "description": description,
            "before": before,
        }
    )
    state.undo_stack = stack[-MAX_UNDO_ITEMS:]
    st.toast(f"Undo: {description}")


def undo_latest(state=None) -> bool:
    """Restore the previous snapshot and remove it from the undo stack."""
    state = state or st.session_state
    stack = list(state.get("undo_stack", []))
    if not stack:
        return False
    action = stack.pop()
    for key, value in action["before"].items():
        state[key] = deepcopy(value)
    state.undo_stack = stack
    from ui.common import refresh_purchase_month_index

    refresh_purchase_month_index(state)
    return True
