"""Reliability helpers — rate limiting and retry with exponential backoff."""
from __future__ import annotations

import logging
import os
import time
from typing import Callable, TypeVar

from .providers.base import ProviderError, TransientProviderError

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Simple per-instance rate limiter.

    Ensures at least ``min_delay`` seconds elapse between calls to
    :meth:`wait`.  Thread-safe is NOT required (jobs are single-threaded).
    """

    def __init__(self, min_delay: float | None = None):
        env_val = os.environ.get("OHLCV_TV_MIN_DELAY_SECONDS")
        if min_delay is not None:
            self._delay = min_delay
        elif env_val is not None:
            self._delay = float(env_val)
        else:
            self._delay = 0.8
        self._last_call: float = 0.0

    def wait(self) -> None:
        """Block until at least ``min_delay`` seconds since the last call."""
        if self._delay <= 0:
            return
        elapsed = time.monotonic() - self._last_call
        remaining = self._delay - elapsed
        if remaining > 0:
            logger.debug("rate-limit: sleeping %.2fs", remaining)
            time.sleep(remaining)
        self._last_call = time.monotonic()


# ---------------------------------------------------------------------------
# Retry with exponential backoff
# ---------------------------------------------------------------------------

def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_retries: int | None = None,
    backoff_seconds: float | None = None,
    label: str = "",
) -> T:
    """Call ``fn()`` with bounded retries on :class:`TransientProviderError`.

    Parameters
    ----------
    fn : callable
        Zero-arg callable to invoke.
    max_retries : int | None
        Override for ``OHLCV_PROVIDER_MAX_RETRIES`` env var (default 3).
    backoff_seconds : float | None
        Override for ``OHLCV_PROVIDER_BACKOFF_SECONDS`` env var (default 1.0).
    label : str
        Human-readable label for log messages.

    Returns
    -------
    T
        The return value of ``fn()``.

    Raises
    ------
    TransientProviderError
        If all retries are exhausted.
    ProviderError / ProviderEmptyError / PermanentProviderError
        Re-raised immediately (not retried).
    """
    if max_retries is None:
        max_retries = int(os.environ.get("OHLCV_PROVIDER_MAX_RETRIES", "3"))
    if backoff_seconds is None:
        backoff_seconds = float(os.environ.get("OHLCV_PROVIDER_BACKOFF_SECONDS", "1.0"))

    last_err: TransientProviderError | None = None
    attempts: list[str] = []

    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except TransientProviderError as exc:
            last_err = exc
            delay = backoff_seconds * (2 ** (attempt - 1))
            attempts.append(f"attempt {attempt}: {exc}")
            logger.warning(
                "%s transient error (attempt %d/%d), retrying in %.1fs: %s",
                label, attempt, max_retries, delay, exc,
            )
            time.sleep(delay)

    # All retries exhausted
    summary = "; ".join(attempts)
    raise TransientProviderError(
        f"{label} failed after {max_retries} retries: {summary}"
    ) from last_err
