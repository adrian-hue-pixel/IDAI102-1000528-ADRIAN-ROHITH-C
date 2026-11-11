"""Small, guarded localStorage operations through a local Streamlit component."""

import hashlib
import json
from typing import Any

try:
    from streamlit_js_eval import streamlit_js_eval
except ModuleNotFoundError:

    def streamlit_js_eval(*_args, **_kwargs):
        raise RuntimeError(
            "streamlit-js-eval is not installed in the active Python environment. "
            "Use the project venv or run: python -m pip install -r requirements.txt"
        )


from browser_persistence import STORAGE_KEY

BACKUP_STORAGE_KEY = "shopimpact_saved_state_backup"


def _call(expression: str, key: str) -> Any:
    return streamlit_js_eval(
        js_expressions=expression,
        key=key,
        default=None,
    )


def build_read_expression() -> str:
    """Build a fixed read expression that reports blocked storage explicitly."""
    key = json.dumps(STORAGE_KEY)
    return (
        "(function(){try{return JSON.stringify({ok:true,value:localStorage.getItem("
        + key
        + ")});}catch(error){return JSON.stringify({ok:false,error:String(error)});}})()"
    )


def build_write_expression(value: str) -> str:
    """Build a guarded write that backs up the old value before a shrink."""
    key = json.dumps(STORAGE_KEY)
    backup_key = json.dumps(BACKUP_STORAGE_KEY)
    encoded_value = json.dumps(value, ensure_ascii=True)
    return (
        "(function(){try{"
        "var previous=localStorage.getItem("
        + key
        + ");var next="
        + encoded_value
        + ";"
        "function count(raw){try{var data=JSON.parse(raw);"
        "if(Number.isInteger(data.purchase_count)&&data.purchase_count>=0)"
        "return data.purchase_count;"
        "if(typeof data.purchases_csv==='string')"
        "return Math.max(0,data.purchases_csv.split(/\\r?\\n/).filter(Boolean).length-1);"
        "}catch(error){}return null;}"
        "if(previous!==null){var oldCount=count(previous);var newCount=count(next);"
        "if(oldCount===null||newCount===null||newCount<oldCount)"
        "localStorage.setItem("
        + backup_key
        + ",previous);}"
        "localStorage.setItem("
        + key
        + ",next);return JSON.stringify({ok:true});}"
        "catch(error){return JSON.stringify({ok:false,error:String(error)});}})()"
    )


def build_remove_expression() -> str:
    """Build a removal expression scoped to ShopImpact's saved and backup keys."""
    key = json.dumps(STORAGE_KEY)
    backup_key = json.dumps(BACKUP_STORAGE_KEY)
    return (
        "(function(){try{localStorage.removeItem("
        + key
        + ");localStorage.removeItem("
        + backup_key
        + ");return JSON.stringify({ok:true});}"
        "catch(error){return JSON.stringify({ok:false,error:String(error)});}})()"
    )


def _parse_result(result: Any) -> tuple[bool, dict[str, Any] | None]:
    if result is None:
        return False, None
    if isinstance(result, dict):
        return True, result
    if not isinstance(result, str):
        raise TypeError("The browser storage component returned an invalid response.")
    try:
        decoded = json.loads(result)
    except json.JSONDecodeError as error:
        raise ValueError(
            "The browser storage component returned unreadable data."
        ) from error
    if not isinstance(decoded, dict):
        raise TypeError("The browser storage component returned an invalid response.")
    return True, decoded


def read_saved_value() -> tuple[bool, str | None, str | None]:
    """Read the app's local record, returning ready, value, and error."""
    ready, result = _parse_result(
        _call(build_read_expression(), "shopimpact_local_storage_read_v1")
    )
    if not ready or result is None:
        return False, None, None
    if result.get("ok") is not True:
        return True, None, str(result.get("error", "Browser storage is unavailable."))
    value = result.get("value")
    if value is not None and not isinstance(value, str):
        return True, None, "Saved browser data is not text."
    return True, value, None


def write_saved_value(value: str) -> tuple[bool, str | None]:
    """Write one encoded value in the browser without interpolating raw code."""
    signature = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    ready, result = _parse_result(
        _call(
            build_write_expression(value),
            f"shopimpact_local_storage_write_{signature}",
        )
    )
    if not ready or result is None:
        return False, None
    if result.get("ok") is not True:
        return True, str(result.get("error", "Browser storage is unavailable."))
    return True, None


def remove_saved_value() -> tuple[bool, str | None]:
    """Remove the app's single localStorage key without clearing unrelated data."""
    ready, result = _parse_result(
        _call(build_remove_expression(), "shopimpact_local_storage_remove_v1")
    )
    if not ready or result is None:
        return False, None
    if result.get("ok") is not True:
        return True, str(result.get("error", "Browser storage is unavailable."))
    return True, None
