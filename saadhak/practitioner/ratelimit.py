"""A client-side rate limiter that paces requests and learns the real limit.

The crude version of this made things worse. A fixed cooldown stops a retry
storm but is blind in both directions: it keeps sending at full speed until the
provider objects, then stops dead for a fixed interval whether or not that was
needed. the provider publishes limits in the thousands per minute and throttles us at
about one, so the documented number is useless and the real one has to be
discovered.

Three parts, each doing one job.

A token bucket paces outgoing requests, so we never burst beyond a known rate and
a caller waits rather than being refused. Additive-increase, multiplicative-
decrease adapts that rate to whatever the provider actually tolerates: every
success nudges it up a little, every throttle halves it at once. That asymmetry
is deliberate and is the same principle TCP congestion control uses, because the
cost of being slightly too slow is a wait, while the cost of being too fast is a
refusal plus a penalty. A circuit breaker sits on top: after repeated failures it
opens and refuses locally for a while, then lets a single probe through to see
whether the provider has recovered, so a sustained outage costs one request per
interval instead of one per call.

Retry-After is honoured when the provider sends it, because a server saying
exactly how long to wait is better information than any heuristic of ours.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum


class Circuit(Enum):
    CLOSED = "closed"        # normal
    OPEN = "open"            # refusing locally, provider is unhappy
    HALF_OPEN = "half_open"  # letting one probe through


@dataclass
class TokenBucket:
    """Classic token bucket. `rate` tokens accrue per second, up to `capacity`."""
    rate: float
    capacity: float
    tokens: float = field(default=0.0)
    # Deliberately not seeded from the wall clock: the first refill adopts
    # whatever clock the caller uses, so tests can drive it from zero and the
    # bucket cannot accrue or drain against a base it never saw.
    updated: float | None = None

    def __post_init__(self) -> None:
        self.tokens = self.capacity

    def _refill(self, now: float) -> None:
        if self.updated is None:
            self.updated = now
            return
        elapsed = max(0.0, now - self.updated)      # never run backwards
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.updated = now

    def take(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        self._refill(now)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def wait_time(self, now: float | None = None) -> float:
        """Seconds until a token is available."""
        now = time.monotonic() if now is None else now
        self._refill(now)
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.rate if self.rate > 0 else float("inf")


@dataclass
class AdaptiveLimiter:
    """Token bucket whose rate is discovered from the provider's behaviour."""
    rate: float = 0.2                 # requests per second to start (12/min)
    min_rate: float = 1 / 120.0       # never slower than one per two minutes
    max_rate: float = 2.0
    burst: float = 2.0
    increase: float = 0.02            # additive, per success
    decrease: float = 0.5             # multiplicative, per throttle
    failure_threshold: int = 4        # consecutive failures before opening
    open_seconds: float = 120.0

    bucket: TokenBucket = field(init=False)
    state: Circuit = Circuit.CLOSED
    consecutive_failures: int = 0
    opened_at: float = 0.0
    retry_after_until: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # observability
    allowed: int = 0
    refused_locally: int = 0
    throttled_by_provider: int = 0

    def __post_init__(self) -> None:
        self.bucket = TokenBucket(rate=self.rate, capacity=self.burst)

    # --- circuit ---------------------------------------------------------
    def _circuit(self, now: float) -> Circuit:
        if self.state is Circuit.OPEN and now - self.opened_at >= self.open_seconds:
            self.state = Circuit.HALF_OPEN
        return self.state

    # --- decision --------------------------------------------------------
    def acquire(self, now: float | None = None) -> tuple[bool, float, str]:
        """May we send? Returns (allowed, seconds_to_wait, reason)."""
        now = time.monotonic() if now is None else now
        with self._lock:
            if now < self.retry_after_until:
                self.refused_locally += 1
                return False, self.retry_after_until - now, "provider asked us to wait"

            state = self._circuit(now)
            if state is Circuit.OPEN:
                self.refused_locally += 1
                return False, self.open_seconds - (now - self.opened_at), "circuit open"

            # A half-open probe is deliberately one request, so it bypasses
            # pacing. Refusing it here would leave the circuit stuck open, since
            # nothing else ever tests whether the provider has recovered.
            if state is Circuit.HALF_OPEN:
                self.bucket.updated = now
                self.allowed += 1
                return True, 0.0, "half-open probe"

            if not self.bucket.take(now):
                wait = self.bucket.wait_time(now)
                self.refused_locally += 1
                return False, wait, f"pacing at {self.rate * 60:.1f}/min"

            self.allowed += 1
            return True, 0.0, "ok"

    # --- feedback --------------------------------------------------------
    def on_success(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            self.consecutive_failures = 0
            self.state = Circuit.CLOSED
            self.rate = min(self.max_rate, self.rate + self.increase)
            self.bucket.rate = self.rate

    def on_throttled(self, retry_after: float | None = None,
                     now: float | None = None) -> None:
        """The provider refused us. Halve the rate at once and respect any hint."""
        now = time.monotonic() if now is None else now
        with self._lock:
            self.throttled_by_provider += 1
            self.consecutive_failures += 1
            self.rate = max(self.min_rate, self.rate * self.decrease)
            self.bucket.rate = self.rate
            self.bucket.tokens = 0.0            # spend the burst, do not pile on
            if retry_after:
                self.retry_after_until = now + retry_after
            if self.consecutive_failures >= self.failure_threshold:
                self.state, self.opened_at = Circuit.OPEN, now

    def on_error(self, now: float | None = None) -> None:
        """A failure that is not a throttle: counts toward the breaker, not the rate."""
        now = time.monotonic() if now is None else now
        with self._lock:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.failure_threshold:
                self.state, self.opened_at = Circuit.OPEN, now

    # --- retry timing ----------------------------------------------------
    @staticmethod
    def backoff(attempt: int, base: float = 1.0, cap: float = 60.0) -> float:
        """Exponential backoff with full jitter.

        Full jitter rather than a fixed delay because several callers backing off
        by the same amount reconverge and retry together, which is the thundering
        herd the backoff was meant to prevent.
        """
        return random.uniform(0.0, min(cap, base * (2 ** attempt)))

    @property
    def status(self) -> dict:
        return {"rate_per_min": round(self.rate * 60, 2), "state": self.state.value,
                "consecutive_failures": self.consecutive_failures,
                "allowed": self.allowed, "refused_locally": self.refused_locally,
                "throttled_by_provider": self.throttled_by_provider}


# One limiter per model: a saturated upstream is a property of the model, not of
# our account, so backing off on one must not throttle the others.
_LIMITERS: dict[str, AdaptiveLimiter] = {}


def limiter_for(model: str) -> AdaptiveLimiter:
    if model not in _LIMITERS:
        _LIMITERS[model] = AdaptiveLimiter()
    return _LIMITERS[model]


def all_status() -> dict[str, dict]:
    return {m: l.status for m, l in _LIMITERS.items()}


LIMITER = limiter_for("default")


def parse_retry_after(headers) -> float | None:
    """Retry-After, in seconds. Accepts the numeric form; ignores HTTP dates."""
    if not headers:
        return None
    v = headers.get("retry-after") or headers.get("Retry-After")
    if not v:
        return None
    try:
        return max(0.0, float(v))
    except (TypeError, ValueError):
        return None
