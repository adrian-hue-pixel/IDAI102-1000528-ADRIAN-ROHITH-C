"""Tests for viewer-local date resolution."""

import datetime as dt
from types import SimpleNamespace

from ui import common


def test_app_today_uses_viewer_timezone_across_utc_midnight(monkeypatch):
    real_datetime = dt.datetime

    class FixedDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            utc_value = real_datetime(2026, 12, 31, 19, 0, tzinfo=dt.timezone.utc)
            return utc_value.astimezone(tz) if tz else utc_value.replace(tzinfo=None)

    monkeypatch.setattr(common.dt, "datetime", FixedDateTime)
    monkeypatch.setattr(
        common.st, "context", SimpleNamespace(timezone="Asia/Kolkata")
    )

    assert common.app_today() == dt.date(2027, 1, 1)


def test_viewer_timezone_falls_back_to_server_local_timezone(monkeypatch):
    monkeypatch.setattr(
        common.st, "context", SimpleNamespace(timezone=None)
    )
    real_datetime = dt.datetime
    server_datetime = real_datetime(2026, 10, 28, tzinfo=dt.timezone.utc)
    expected_timezone = server_datetime.astimezone().tzinfo

    class FixedDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return server_datetime

    monkeypatch.setattr(common.dt, "datetime", FixedDateTime)

    assert common.viewer_timezone() == expected_timezone
