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
import time

from pyrate_limiter import Duration, Limiter, Rate
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)
from yfinance.exceptions import YFRateLimitError

from market_data.config import MAX_RETRIES, RETRY_DELAY_RANGE

logger = logging.getLogger(__name__)


class YFinanceEmptyDownloadError(Exception):
    """``yf.download`` returned 0 rows — likely a silent rate-limit."""


_RATE_PER_SECOND = Rate(2, Duration.SECOND)
_RATE_PER_MINUTE = Rate(60, Duration.MINUTE)

_limiter_lock = threading.Lock()
_limiter: Limiter | None = None

# ---------------------------------------------------------------------------
# Adaptive throttle state — when Yahoo returns 429, we inject extra delay
# between acquire() calls so the *entire process* backs off, not just the
# single caller that hit the wall.
# ---------------------------------------------------------------------------
_throttle_lock = threading.Lock()
_extra_delay: float = 0.0
_consecutive_429: int = 0

_THROTTLE_BASE: float = 5.0
_THROTTLE_MAX: float = 120.0
_THROTTLE_DECAY_AFTER: int = 5


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


def notify_rate_limit() -> float:
    """Record a 429 hit and increase the global extra delay.

    Returns the new extra delay so callers can log it.
    """
    global _extra_delay, _consecutive_429  # noqa: PLW0603
    with _throttle_lock:
        _consecutive_429 += 1
        _extra_delay = min(_THROTTLE_BASE * (2 ** (_consecutive_429 - 1)), _THROTTLE_MAX)
        logger.warning(
            "Rate-limit hit #%d — global extra delay now %.1fs",
            _consecutive_429,
            _extra_delay,
        )
        return _extra_delay


def notify_success() -> None:
    """Record a successful request; gradually decay the extra delay."""
    global _extra_delay, _consecutive_429  # noqa: PLW0603
    with _throttle_lock:
        if _consecutive_429 > 0:
            _consecutive_429 = max(0, _consecutive_429 - 1)
            if _consecutive_429 == 0:
                _extra_delay = 0.0
            else:
                _extra_delay = min(_THROTTLE_BASE * (2 ** (_consecutive_429 - 1)), _THROTTLE_MAX)


def get_extra_delay() -> float:
    with _throttle_lock:
        return _extra_delay


def reset_throttle() -> None:
    """Reset adaptive throttle state (useful in tests)."""
    global _extra_delay, _consecutive_429  # noqa: PLW0603
    with _throttle_lock:
        _extra_delay = 0.0
        _consecutive_429 = 0


def acquire(weight: int = 1) -> None:
    """Block until the leaky-bucket allows ``weight`` requests.

    Also respects the adaptive extra delay injected by :func:`notify_rate_limit`.
    """
    extra = get_extra_delay()
    if extra > 0:
        time.sleep(extra)

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


def _before_sleep_rate_limit(retry_state: RetryCallState) -> None:
    """Log rate-limit retry and bump adaptive throttle."""
    outcome = retry_state.outcome
    exc = outcome.exception() if outcome else None
    if isinstance(exc, (YFRateLimitError, YFinanceEmptyDownloadError)):
        notify_rate_limit()
    wait = retry_state.next_action.sleep if retry_state.next_action else 0
    logger.warning(
        "Rate-limit retry %d/%d — sleeping %.1fs (extra_delay=%.1fs)",
        retry_state.attempt_number,
        MAX_RETRIES,
        wait,
        get_extra_delay(),
    )


yfinance_retry = retry(
    retry=retry_if_exception_type((Exception,)),
    stop=stop_after_attempt(MAX_RETRIES + 1),
    wait=wait_exponential_jitter(
        initial=RETRY_DELAY_RANGE[0],
        max=30,
        jitter=RETRY_DELAY_RANGE[1] - RETRY_DELAY_RANGE[0],
    ),
    before_sleep=_before_sleep_log,
    reraise=True,
)

RATE_LIMIT_MAX_RETRIES = 5

yfinance_rate_limit_retry = retry(
    retry=retry_if_exception_type((YFRateLimitError, YFinanceEmptyDownloadError)),
    stop=stop_after_attempt(RATE_LIMIT_MAX_RETRIES + 1),
    wait=wait_exponential_jitter(
        initial=30,
        max=_THROTTLE_MAX,
        jitter=5,
    ),
    before_sleep=_before_sleep_rate_limit,
    reraise=True,
)
