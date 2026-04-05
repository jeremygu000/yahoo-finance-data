from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from market_data.rate_limiter import (
    YFinanceEmptyDownloadError,
    acquire,
    get_limiter,
    notify_rate_limit,
    notify_success,
    reset_limiter,
    reset_throttle,
    yfinance_retry,
)
from yfinance.exceptions import YFRateLimitError


class TestLimiterSingleton:
    def setup_method(self) -> None:
        reset_limiter()

    def teardown_method(self) -> None:
        reset_limiter()

    def test_get_limiter_returns_same_instance(self) -> None:
        a = get_limiter()
        b = get_limiter()
        assert a is b

    def test_reset_creates_new_instance(self) -> None:
        a = get_limiter()
        reset_limiter()
        b = get_limiter()
        assert a is not b


class TestAcquire:
    def setup_method(self) -> None:
        reset_limiter()

    def teardown_method(self) -> None:
        reset_limiter()

    def test_acquire_does_not_raise(self) -> None:
        acquire()

    def test_acquire_weight(self) -> None:
        acquire(weight=2)


class TestYfinanceRetry:
    @patch("tenacity.nap.time.sleep")
    def test_retries_on_exception(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @yfinance_retry
        def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient")
            return "ok"

        assert flaky() == "ok"
        assert call_count == 3

    @patch("tenacity.nap.time.sleep")
    def test_reraises_after_exhaustion(self, mock_sleep: MagicMock) -> None:
        @yfinance_retry
        def always_fail() -> str:
            raise RuntimeError("permanent")

        with pytest.raises(RuntimeError, match="permanent"):
            always_fail()

    def test_no_retry_on_success(self) -> None:
        call_count = 0

        @yfinance_retry
        def ok() -> str:
            nonlocal call_count
            call_count += 1
            return "done"

        assert ok() == "done"
        assert call_count == 1

    @patch("tenacity.nap.time.sleep")
    def test_retries_on_rate_limit(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @yfinance_retry
        def rate_limited() -> str:
            nonlocal call_count
            call_count += 1
            raise YFRateLimitError()

        with pytest.raises(YFRateLimitError):
            rate_limited()
        assert call_count == 4  # 1 initial + 3 retries (MAX_RETRIES=3)

    @patch("tenacity.nap.time.sleep")
    def test_retries_on_empty_download(self, mock_sleep: MagicMock) -> None:
        call_count = 0

        @yfinance_retry
        def empty_dl() -> str:
            nonlocal call_count
            call_count += 1
            raise YFinanceEmptyDownloadError("no data")

        with pytest.raises(YFinanceEmptyDownloadError):
            empty_dl()
        assert call_count == 4  # 1 initial + 3 retries


class TestAdaptiveThrottle:
    def setup_method(self) -> None:
        reset_throttle()

    def teardown_method(self) -> None:
        reset_throttle()

    def test_notify_rate_limit_increases_delay(self) -> None:
        d1 = notify_rate_limit()
        assert d1 == 5.0
        d2 = notify_rate_limit()
        assert d2 == 10.0
        d3 = notify_rate_limit()
        assert d3 == 20.0

    def test_notify_success_decays_delay(self) -> None:
        notify_rate_limit()
        notify_rate_limit()
        notify_success()
        d = notify_rate_limit()
        assert d == 10.0

    def test_throttle_caps_at_max(self) -> None:
        for _ in range(20):
            notify_rate_limit()
        from market_data.rate_limiter import get_extra_delay

        assert get_extra_delay() <= 120.0
