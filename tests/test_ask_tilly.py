import datetime as dt
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest
from streamlit.testing.v1 import AppTest

from ask_tilly import context_for, generate


def test_summary_minimizes_data_and_is_opt_in():
    record = {
        "date": dt.date(2026, 11, 1),
        "product_type": "Clothing",
        "co2e_kg": 12,
        "brand": "PRIVATE",
        "note": "SECRET",
        "price_usd": 100,
    }
    assert context_for([record], (2026, 11))["journal_shared"] is False
    shared = context_for([record], (2026, 11), True)
    assert shared["illustrative_total_kg"] == 12
    assert all(
        word not in json.dumps(shared)
        for word in ["PRIVATE", "SECRET", "price_usd", "2026-11-01"]
    )
    assert context_for([record], (2026, 10), True)["entries"] == 0


def test_transport_uses_header_and_grounded_context_without_disclosing_key():
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return json.dumps(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "hello [invented](https://fake.test)"}
                                ]
                            }
                        }
                    ]
                }
            ).encode()

    def opener(request, timeout):
        assert "test-key" not in request.full_url
        assert request.get_header("X-goog-api-key") == "test-key"
        payload = json.loads(request.data)
        assert "NOT full confidence" in payload["systemInstruction"]["parts"][0]["text"]
        return Response()

    assert (
        generate("Explain uncertainty", [], {}, "test-key", opener=opener)
        == "hello invented"
    )


def test_api_errors_do_not_echo_provider_response_or_credentials():
    def opener(*args, **kwargs):
        raise HTTPError("secret-url", 429, "SECRET KEY", {}, None)

    with pytest.raises(ValueError, match="quota") as result:
        generate("Hi", [], {}, "secret", opener=opener)
    assert "SECRET" not in str(result.value)


def test_chat_renders_without_a_key_and_preserves_original_navigation(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    a = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=15
    )
    a.session_state["browser_storage_loaded"] = True
    a.session_state["storage_available"] = False
    a.run().switch_page("views/ask_tilly.py").run()
    assert not a.exception
    assert a.chat_input[0].disabled
    assert any("configure a Gemini" in i.value for i in a.info)
    a.switch_page("views/home.py").run()
    assert not a.exception
    assert any("Meet Tilly" in w.value for w in a.markdown)
