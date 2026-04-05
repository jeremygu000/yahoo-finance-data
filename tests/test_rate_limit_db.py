from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from market_data import rate_limit_db as db


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path: Path) -> None:
    db_path = tmp_path / "test_rate_limits.db"
    db.close_connection()
    db.ensure_quota("test_src", "minute", 10, db_path=db_path)
    yield  # type: ignore[misc]
    db.close_connection()


def _db(tmp_path: Path) -> Path:
    return tmp_path / "test_rate_limits.db"


class TestQuota:
    def test_ensure_and_consume(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        db.ensure_quota("src_a", "minute", 5, db_path=p)
        assert db.try_consume("src_a", "minute", db_path=p)

    def test_exhaust_quota(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        db.ensure_quota("src_b", "minute", 2, db_path=p)
        assert db.try_consume("src_b", "minute", db_path=p)
        assert db.try_consume("src_b", "minute", db_path=p)
        assert not db.try_consume("src_b", "minute", db_path=p)

    def test_unregistered_source_allows(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        assert db.try_consume("unknown", "minute", db_path=p)

    def test_get_quota_usage(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        db.ensure_quota("src_c", "daily", 100, db_path=p)
        db.try_consume("src_c", "daily", 3, db_path=p)
        usage = db.get_quota_usage("src_c", "daily", db_path=p)
        assert usage["used"] == 3
        assert usage["remaining"] == 97

    def test_unregistered_usage_zeros(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        usage = db.get_quota_usage("nope", "minute", db_path=p)
        assert usage["used"] == 0
        assert usage["remaining"] == 0


class TestThrottle:
    def test_record_rate_limit_increments(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        delay1 = db.record_rate_limit("src_t", db_path=p)
        assert delay1 == pytest.approx(5.0)
        delay2 = db.record_rate_limit("src_t", db_path=p)
        assert delay2 == pytest.approx(10.0)

    def test_record_success_decays(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        db.record_rate_limit("src_t2", db_path=p)
        db.record_rate_limit("src_t2", db_path=p)
        db.record_success("src_t2", db_path=p)
        t = db.get_throttle("src_t2", db_path=p)
        assert t["consecutive_429"] == 1

    def test_reset_throttle(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        db.record_rate_limit("src_t3", db_path=p)
        db.reset_throttle("src_t3", db_path=p)
        t = db.get_throttle("src_t3", db_path=p)
        assert t["consecutive_429"] == 0

    def test_success_on_clean_state_noop(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        db.record_success("fresh", db_path=p)
        t = db.get_throttle("fresh", db_path=p)
        assert t["consecutive_429"] == 0

    def test_delay_capped_at_max(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        for _ in range(20):
            delay = db.record_rate_limit("src_cap", db_path=p)
        assert delay <= 120.0


class TestCallLog:
    def test_log_and_count(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        db.log_call("src_l", ticker="AAPL", endpoint="time_series", status="ok", db_path=p)
        db.log_call("src_l", ticker="MSFT", endpoint="time_series", status="ok", db_path=p)
        assert db.get_call_count("src_l", db_path=p) == 2

    def test_count_with_status_filter(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        db.log_call("src_f", status="ok", db_path=p)
        db.log_call("src_f", status="rate_limited", db_path=p)
        assert db.get_call_count("src_f", status="ok", db_path=p) == 1
        assert db.get_call_count("src_f", status="rate_limited", db_path=p) == 1


class TestResetAll:
    def test_clears_everything(self, tmp_path: Path) -> None:
        p = _db(tmp_path)
        db.ensure_quota("x", "minute", 10, db_path=p)
        db.try_consume("x", "minute", db_path=p)
        db.record_rate_limit("x", db_path=p)
        db.log_call("x", db_path=p)
        db.reset_all(db_path=p)
        assert db.get_quota_usage("x", "minute", db_path=p)["used"] == 0
        assert db.get_throttle("x", db_path=p)["consecutive_429"] == 0
        assert db.get_call_count("x", db_path=p) == 0
