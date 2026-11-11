"""Research-edition UI flows, separate from retained legacy tests."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def app():
    a = AppTest.from_file(str(APP), default_timeout=15)
    a.session_state["browser_storage_loaded"] = True
    a.session_state["storage_available"] = False
    a.session_state["research_loaded"] = True
    a.session_state["research_session_only"] = True
    a.run()
    a.switch_page("views/research.py").run()
    next(w for w in a.selectbox if w.label == "Explore research tools").select(
        "Cited estimates"
    ).run()
    return a


def test_embedded_research_uses_cited_factors_and_saves_metadata():
    a = app()
    assert not a.exception
    assert any("EPA SC-GHG" in x.value for x in a.caption)
    next(w for w in a.button if w.label == "Save purchase").click().run()
    rows = a.session_state["research_records"]
    assert len(rows) == 1
    assert rows[0]["dataset_version"] == "2026.11.2" and rows[0]["currency"] == "USD"
    assert a.session_state["research_mode"] == a.session_state["display_mode"]
    assert a.session_state["purchases"] == []


def test_native_region_gap_is_visible_and_no_us_fallback_is_logged():
    a = app()
    next(w for w in a.selectbox if w.label == "Purchase region").select("IN").run()
    assert any("validated native factor" in x.value for x in a.error)
    assert not any(w.label == "Save purchase" for w in a.button)


@pytest.mark.parametrize(
    "page",
    [
        "journal_page",
        "dashboard_page",
        "method_page",
        "lab_page",
        "classifier_page",
        "lifecycle_page",
        "feedback_page",
        "settings_page",
        "garden_page",
    ],
)
@pytest.mark.parametrize("mode", ["Light", "Dark"])
def test_research_views_render_without_exceptions(page, mode):
    script = f"""import streamlit as st
import research_app as r
st.session_state.research_records=[]
st.session_state.research_corrections=[]
st.session_state.research_feedback=[]
st.session_state.research_mode={mode!r}
st.session_state.research_motion=True
st.session_state.research_locked=False
st.session_state.research_month="2026-11"
r.{page}()
"""
    a = AppTest.from_string(script, default_timeout=15).run()
    assert not a.exception


def test_invalid_research_backup_never_silently_accepts_a_wrong_estimate():
    from research_app import validate_store

    with pytest.raises(ValueError):
        validate_store({"schema": 2})
    with pytest.raises(ValueError):
        validate_store(
            {
                "schema": 1,
                "records": [
                    {
                        "id": "x",
                        "date": "2026-11-11",
                        "category": "Clothing",
                        "amount": 100,
                        "currency": "USD",
                        "region": "US",
                        "price_year": 2022,
                        "dataset_version": "2026.11.2",
                        "estimate_kg": 999,
                    }
                ],
            }
        )


@pytest.mark.parametrize("mode", ["Light", "Dark"])
def test_research_is_part_of_full_app_with_shared_preferences(mode):
    a = app()
    a.session_state["display_mode"] = mode
    for tool in [
        "Start here",
        "Validation",
        "Budget planner",
        "Product text",
        "Lifespan",
        "Replay",
        "Monthly analysis",
        "Research journal",
        "Method",
        "Feedback",
        "Data & export",
    ]:
        next(w for w in a.selectbox if w.label == "Explore research tools").select(
            tool
        ).run()
        assert not a.exception
        assert a.session_state["research_mode"] == mode
    a.switch_page("views/home.py").run()
    assert not a.exception
    assert any(w.label == "Product type" for w in a.radio)
    assert any("Footprint trail" in w.value for w in a.markdown)
    assert any("Meet Tilly" in w.value for w in a.markdown)
