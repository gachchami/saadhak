"""The practitioner failed two calls in three against the live provider."""
from saadhak.practitioner import llm as L


def test_rate_limits_are_recognised_including_the_providers_own_wording():
    assert L._is_rate_limited("429 Too Many Requests")
    assert L._is_rate_limited("rate limit exceeded")
    assert L._is_rate_limited("您已达到总请求数限制：1分钟内最多请求5000次")
    assert not L._is_rate_limited("empty content (reasoning consumed the token budget)")


def _fresh_limiter(monkeypatch, rate=100.0):
    """Every model shares one generous limiter, so tests exercise the retry and
    failover logic rather than the pacing. The real ones carry live state."""
    from saadhak.practitioner import ratelimit as RL
    RL._LIMITERS.clear()
    lim = RL.AdaptiveLimiter(rate=rate, burst=rate)
    monkeypatch.setattr(L, "limiter_for", lambda model: lim)
    return lim


def _single_model(monkeypatch):
    """Collapse the chain, for tests about one model's behaviour."""
    monkeypatch.setattr(L, "providers", lambda: [("only", "u", "k")])


def test_a_disabled_model_does_not_burn_retries(monkeypatch):
    _fresh_limiter(monkeypatch); _single_model(monkeypatch)
    calls = []

    def once(*a, **k):
        calls.append(1)
        return L.LLMReply(False, error="llm disabled (no key)")

    monkeypatch.setattr(L, "_ask_once", once)
    monkeypatch.setattr(L.settings(), "featherless_api_key", "", raising=False)
    L.ask_json("s", "u")
    assert len(calls) == 1


def test_a_transient_failure_is_retried(monkeypatch):
    _fresh_limiter(monkeypatch); _single_model(monkeypatch)
    monkeypatch.setattr(L.time, "sleep", lambda *_: None)
    seq = [L.LLMReply(False, error="ReadTimeout"),
           L.LLMReply(True, content="{}", parsed={})]
    monkeypatch.setattr(L, "_ask_once", lambda *a, **k: seq.pop(0))
    assert L.ask_json("s", "u").ok


def test_failure_is_never_turned_into_a_guess(monkeypatch):
    _fresh_limiter(monkeypatch); _single_model(monkeypatch)
    monkeypatch.setattr(L.time, "sleep", lambda *_: None)
    monkeypatch.setattr(L, "_ask_once", lambda *a, **k: L.LLMReply(False, error="boom"))
    monkeypatch.setattr(L.settings(), "featherless_api_key", "", raising=False)
    r = L.ask_json("s", "u")
    assert not r.ok and r.parsed is None


def test_a_rate_limit_does_not_trigger_a_retry_storm(monkeypatch):
    """Measured on the live provider: a 2s backoff turned a 20% failure rate into
    64%, because each refusal became three refusals seconds apart."""
    lim = _fresh_limiter(monkeypatch); _single_model(monkeypatch)
    calls = []

    def once(*a, **k):
        calls.append(1)
        return L.LLMReply(False, error="您的账户已达到速率限制，请您控制请求频率")

    monkeypatch.setattr(L, "_ask_once", once)
    monkeypatch.setattr(L.settings(), "featherless_api_key", "", raising=False)
    L.ask_json("s", "u")
    assert len(calls) == 1, "a throttle must not be answered with more traffic"
    assert lim.throttled_by_provider == 1
    assert lim.rate < 100, "the throttle must slow us down"


def test_a_timeout_still_gets_one_more_try(monkeypatch):
    _fresh_limiter(monkeypatch); _single_model(monkeypatch)
    monkeypatch.setattr(L.time, "sleep", lambda *_: None)
    seq = [L.LLMReply(False, error="ReadTimeout"), L.LLMReply(True, parsed={})]
    monkeypatch.setattr(L, "_ask_once", lambda *a, **k: seq.pop(0))
    assert L.ask_json("s", "u").ok


def test_calls_are_refused_locally_while_the_circuit_is_open(monkeypatch):
    """An open circuit costs one probe per interval, not one request per call."""
    lim = _fresh_limiter(monkeypatch); _single_model(monkeypatch)
    for _ in range(lim.failure_threshold):
        lim.on_throttled()
    sent = []
    monkeypatch.setattr(L, "_ask_once", lambda *a, **k: sent.append(1))
    r = L.ask_json("s", "u")
    assert not sent, "nothing should reach the provider while the circuit is open"
    assert not r.ok and "circuit open" in r.error


def test_a_throttled_model_falls_through_to_the_next(monkeypatch):
    """Every model is on Featherless; a throttle on one must not stop the desk."""
    from saadhak.practitioner import ratelimit as RL
    RL._LIMITERS.clear()
    seen = []

    def once(system, user, *, cycle_id="", base_url=None, api_key=None, model=None):
        seen.append(model)
        if len(seen) == 1:
            return L.LLMReply(False, error="rate limit exceeded")
        return L.LLMReply(True, parsed={"ok": True}, model=model)

    monkeypatch.setattr(L, "providers", lambda: [("a", "u", "k"), ("b", "u", "k")])
    monkeypatch.setattr(L, "_ask_once", once)
    monkeypatch.setattr(L.journal, "append", lambda *a, **k: None)
    assert L.ask_json("s", "u").ok
    assert len(seen) > 1
    RL._LIMITERS.clear()
