"""The limiter is driven by an injected clock, so its behaviour is exact."""
import pytest

from saadhak.practitioner.ratelimit import (AdaptiveLimiter, Circuit, TokenBucket,
                                            parse_retry_after)


# --- token bucket -----------------------------------------------------------

def test_bucket_allows_a_burst_then_paces():
    b = TokenBucket(rate=1.0, capacity=3.0)
    assert [b.take(now=0) for _ in range(3)] == [True, True, True]
    assert not b.take(now=0)


def test_bucket_refills_over_time():
    b = TokenBucket(rate=1.0, capacity=3.0)
    for _ in range(3):
        b.take(now=0)
    assert not b.take(now=0.5)
    assert b.take(now=1.0)


def test_wait_time_is_what_it_takes_to_earn_a_token():
    b = TokenBucket(rate=0.5, capacity=1.0)
    b.take(now=0)
    assert b.wait_time(now=0) == pytest.approx(2.0)


# --- adaptive rate ----------------------------------------------------------

def test_success_raises_the_rate_gently():
    lim = AdaptiveLimiter(rate=0.2, increase=0.02)
    for _ in range(5):
        lim.on_success(now=0)
    assert lim.rate == pytest.approx(0.30)


def test_a_throttle_halves_the_rate_immediately():
    """Asymmetric on purpose: too slow costs a wait, too fast costs a refusal."""
    lim = AdaptiveLimiter(rate=0.4)
    lim.on_throttled(now=0)
    assert lim.rate == pytest.approx(0.2)
    lim.on_throttled(now=0)
    assert lim.rate == pytest.approx(0.1)


def test_the_rate_never_falls_below_the_floor():
    lim = AdaptiveLimiter(rate=0.4, min_rate=0.05)
    for _ in range(20):
        lim.on_throttled(now=0)
    assert lim.rate == pytest.approx(0.05)


def test_a_throttle_spends_the_burst_so_we_do_not_pile_on():
    lim = AdaptiveLimiter(rate=1.0, burst=5.0)
    lim.on_throttled(now=0)
    allowed, wait, _ = lim.acquire(now=0)
    assert not allowed and wait > 0


# --- circuit breaker --------------------------------------------------------

def test_the_circuit_opens_after_repeated_failures():
    lim = AdaptiveLimiter(failure_threshold=3)
    for _ in range(3):
        lim.on_throttled(now=0)
    assert lim.state is Circuit.OPEN
    allowed, _, reason = lim.acquire(now=1)
    assert not allowed and reason == "circuit open"


def test_an_open_circuit_costs_one_probe_per_interval_not_one_per_call():
    lim = AdaptiveLimiter(failure_threshold=2, open_seconds=60, rate=10, burst=10)
    for _ in range(2):
        lim.on_throttled(now=0)
    assert all(not lim.acquire(now=t)[0] for t in (1, 10, 30, 59))
    allowed, _, reason = lim.acquire(now=61)
    assert allowed and reason == "half-open probe"


def test_a_successful_probe_closes_the_circuit():
    lim = AdaptiveLimiter(failure_threshold=2, open_seconds=10, rate=10, burst=10)
    for _ in range(2):
        lim.on_throttled(now=0)
    lim.acquire(now=11)
    lim.on_success(now=11)
    assert lim.state is Circuit.CLOSED and lim.consecutive_failures == 0


# --- provider hints ---------------------------------------------------------

def test_retry_after_is_obeyed_over_our_own_pacing():
    lim = AdaptiveLimiter(rate=10, burst=10)
    lim.on_throttled(retry_after=30, now=0)
    allowed, wait, reason = lim.acquire(now=5)
    assert not allowed and reason == "provider asked us to wait"
    assert wait == pytest.approx(25)


def test_retry_after_parsing():
    assert parse_retry_after({"retry-after": "12"}) == 12.0
    assert parse_retry_after({"Retry-After": "0"}) == 0.0
    assert parse_retry_after({"retry-after": "Wed, 03 Sep 2026 12:00:00 GMT"}) is None
    assert parse_retry_after({}) is None
    assert parse_retry_after(None) is None


# --- backoff ----------------------------------------------------------------

def test_backoff_grows_and_is_capped():
    assert all(AdaptiveLimiter.backoff(a, base=1, cap=30) <= 30 for a in range(10))
    assert max(AdaptiveLimiter.backoff(0, base=1, cap=30) for _ in range(200)) <= 1.0


def test_backoff_is_jittered_so_callers_do_not_reconverge():
    draws = {AdaptiveLimiter.backoff(4, base=1, cap=60) for _ in range(50)}
    assert len(draws) > 40, "identical delays recreate the herd they prevent"


# --- one limiter per model --------------------------------------------------

def test_each_model_gets_its_own_limiter():
    """A saturated upstream belongs to the model, not to our account. Backing off
    on one must not throttle the others."""
    from saadhak.practitioner.ratelimit import limiter_for
    a, b = limiter_for("model-a"), limiter_for("model-b")
    assert a is not b
    assert limiter_for("model-a") is a
    a.on_throttled(now=0)
    assert a.rate < b.rate
