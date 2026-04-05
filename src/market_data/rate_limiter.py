"""Centralized rate-limiting and retry logic for Yahoo Finance API calls.

Uses pyrate-limiter for proactive request throttling (leaky bucket) and
tenacity for reactive retry with exponential backoff on failures.

Configuration is driven by ``market_data.config`` constants.  Every yfinance
call—OHLCV downloads, fundamentals fetches, etc.—should go through the
helpers exposed here so that the *single* shared bucket is respected across
all callers.
"""

from __future__ import annotations

import logging
import threading

from pyrate_limiter import Duration, Limiter, Rate
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)
from yfinance.exceptions import YFRateLimitError

from market_data.config import MAX_RETRIES, RETRY_DELAY_RANGE

logger = logging.getLogger(__name__)


class YFinanceEmptyDownloadError(Exception):
    """``yf.download`` returned 0 rows — likely a silent rate-limit."""


# Yahoo Finance is empirically comfortable with ~2 req/s sustained.
# We add a longer-window cap to stay well under the per-minute threshold.
_RATE_PER_SECOND = Rate(2, Duration.SECOND)
_RATE_PER_MINUTE = Rate(60, Duration.MINUTE)

_limiter_lock = threading.Lock()
_limiter: Limiter | None = None


def get_limiter() -> Limiter:
    """Return the module-level singleton ``Limiter``.

    Lazily constructed so tests can monkey-patch *before* first use.
    """
    global _limiter  # noqa: PLW0603
    if _limiter is None:
        with _limiter_lock:
            if _limiter is None:
                _limiter = Limiter([_RATE_PER_SECOND, _RATE_PER_MINUTE])
    return _limiter


def reset_limiter() -> None:
    """Reset the singleton limiter (useful in tests)."""
    global _limiter  # noqa: PLW0603
    with _limiter_lock:
        _limiter = None


def acquire(weight: int = 1) -> None:
    """Block until the leaky-bucket allows ``weight`` requests."""
    limiter = get_limiter()
    for _ in range(weight):
        limiter.try_acquire("yfinance")


def _before_sleep_log(retry_state: RetryCallState) -> None:
    """Log each retry attempt (used as *before_sleep* callback)."""
    outcome = retry_state.outcome
    exc = outcome.exception() if outcome else None
    wait = retry_state.next_action.sleep if retry_state.next_action else 0
    logger.warning(
        "Retry %d/%d after %s — sleeping %.1fs",
        retry_state.attempt_number,
        MAX_RETRIES,
        type(exc).__name__ if exc else "unknown",
        wait,
    )


_NO_RETRY_EXCEPTIONS = (YFRateLimitError, YFinanceEmptyDownloadError)

yfinance_retry = retry(
    retry=(retry_if_exception_type((Exception,)) & retry_if_not_exception_type(_NO_RETRY_EXCEPTIONS)),
    stop=stop_after_attempt(MAX_RETRIES + 1),
    wait=wait_exponential_jitter(
        initial=RETRY_DELAY_RANGE[0],
        max=30,
        jitter=RETRY_DELAY_RANGE[1] - RETRY_DELAY_RANGE[0],
    ),
    before_sleep=_before_sleep_log,
    reraise=True,
)
