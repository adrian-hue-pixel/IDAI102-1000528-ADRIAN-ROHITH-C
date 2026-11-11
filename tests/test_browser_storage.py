"""Browser localStorage expressions are scoped and escape serialized user data."""

import json

import pytest

from browser_persistence import STORAGE_KEY
from browser_storage import (
    BACKUP_STORAGE_KEY,
    _parse_result,
    build_read_expression,
    build_remove_expression,
    build_write_expression,
)


def test_storage_expressions_only_access_the_shopimpact_key():
    for expression in (
        build_read_expression(),
        build_write_expression("data"),
        build_remove_expression(),
    ):
        assert json.dumps(STORAGE_KEY) in expression
        assert "localStorage.clear" not in expression


def test_write_expression_escapes_payload_as_a_javascript_string():
    payload = "'; alert('not code'); \\ newline\n 🌿"
    expression = build_write_expression(payload)

    assert json.dumps(payload, ensure_ascii=True) in expression


def test_write_expression_backs_up_before_replacing_a_smaller_journal():
    expression = build_write_expression('{"purchase_count":1,"purchases_csv":"header\\nrow\\n"}')

    backup = expression.index(f"localStorage.setItem({json.dumps(BACKUP_STORAGE_KEY)},previous)")
    replace = expression.index(f"localStorage.setItem({json.dumps(STORAGE_KEY)},next)")

    assert "newCount<oldCount" in expression
    assert backup < replace


def test_component_response_parser_distinguishes_pending_and_failure():
    assert _parse_result(None) == (False, None)
    assert _parse_result('{"ok":true,"value":null}') == (
        True,
        {"ok": True, "value": None},
    )
    with pytest.raises(ValueError, match="unreadable"):
        _parse_result("not-json")
