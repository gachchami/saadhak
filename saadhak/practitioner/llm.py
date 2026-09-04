"""OpenAI-compatible model client. Every call is metered and journaled.

Two things this must never do: block the trading loop, and be trusted. A model
timeout or a malformed answer degrades to "no opinion" and the deterministic
engine carries on unchanged.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

import httpx

from saadhak.config import settings
from saadhak.practitioner.ratelimit import (LIMITER, all_status, limiter_for,
                                             parse_retry_after)
from saadhak.witness import journal


def extract_json(text: str) -> dict | None:
    """GLM wraps JSON in prose or fences often enough to be worth handling. A
    truncated object cannot be repaired, and returns None rather than a guess."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    start = t.find("{")
    if start == -1:
        return None
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(t[start:], start):
        if esc:
            esc = False
            continue
        if ch == "\\" and in_str:
            esc = True
        elif ch == '"':
            in_str = not in_str
        elif not in_str:
            depth += 1 if ch == "{" else (-1 if ch == "}" else 0)
            if depth == 0:
                try:
                    return json.loads(t[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None      # unbalanced: the answer was cut off mid-object


@dataclass
class LLMReply:
    ok: bool
    content: str = ""
    parsed: dict | None = None
    error: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    latency_ms: int = 0
    model: str = ""
    retry_after: float | None = None

    @property
    def usage(self) -> dict:
        return {"prompt": self.prompt_tokens, "completion": self.completion_tokens,
                "reasoning": self.reasoning_tokens}


@dataclass
class Budget:
    """Featherless bills Featherless at zero during its free offer, but a free tier
    can end without notice, so spend is metered as if it were not free."""
    spent_usd: float = 0.0
    calls: int = 0
    prices: dict = field(default_factory=lambda: {"in": 0.075 / 1e6, "out": 0.25 / 1e6})

    def add(self, r: LLMReply) -> None:
        self.calls += 1
        self.spent_usd += (r.prompt_tokens * self.prices["in"]
                           + r.completion_tokens * self.prices["out"])

    @property
    def exhausted(self) -> bool:
        return self.spent_usd >= settings().saadhak_llm_budget_usd


BUDGET = Budget()


RATE_LIMIT_HINTS = ("rate", "limit", "429", "too many", "请求", "频率")


def _is_rate_limited(err: str | None) -> bool:
    e = (err or "").lower()
    return any(h in e for h in RATE_LIMIT_HINTS)


def cooling_down() -> float:
    """Seconds the limiter wants us to wait before asking again."""
    allowed, wait, _ = LIMITER.acquire()
    if allowed:
        # We just consumed a token to ask the question; hand it back.
        LIMITER.bucket.tokens = min(LIMITER.bucket.capacity, LIMITER.bucket.tokens + 1)
        LIMITER.allowed -= 1
        return 0.0
    return wait


def providers() -> list[tuple[str, str, str]]:
    """(model, base_url, api_key) in the order they should be tried.

    All of them are Featherless: open-weight models behind one OpenAI-compatible
    endpoint. Several are listed so a throttle on one model does not stop the
    desk, and each keeps its own learned rate.
    """
    s = settings()
    if not s.featherless_api_key:
        return []
    models = [m.strip() for m in s.featherless_models.split(",") if m.strip()]
    return [(m, s.featherless_base_url, s.featherless_api_key) for m in models]


def model_chain() -> list[str]:
    return [m for m, _, _ in providers()]


def ask_json(system: str, user: str, *, cycle_id: str = "", retries: int = 2) -> LLMReply:
    """Ask for JSON. A failure is 'no opinion', never a guess.

    Three distinct failures show up in practice and each needs different handling:
    a rate limit from the provider, which is worth waiting out; a timeout or
    exhausted token budget, which is worth one plain retry; and a refusal or an
    empty answer, which is not. When the primary provider keeps refusing and a
    fallback is configured, the fallback answers instead.
    """
    s = settings()
    r = LLMReply(False, error="no model attempted")

    for model, base_url, api_key in providers():
        lim = limiter_for(model)
        for attempt in range(retries + 1):
            allowed, wait, reason = lim.acquire()
            if not allowed:
                r = LLMReply(False, error=f"{model}: {reason}; wait {wait:.0f}s")
                break                  # this model is paced out; try the next one

            r = _ask_once(system, user, cycle_id=cycle_id, model=model,
                          base_url=base_url, api_key=api_key)

            if r.ok:
                lim.on_success()
                if model != s.practitioner_model:
                    journal.append("llm_failover", {
                        "cycle_id": cycle_id, "used": model,
                        "primary": s.practitioner_model})
                return r
            if "budget" in (r.error or "") or "disabled" in (r.error or ""):
                return r
            if _is_rate_limited(r.error):
                lim.on_throttled(retry_after=r.retry_after)
                break                  # never answer a throttle with more traffic
            lim.on_error()
            if attempt < retries:
                time.sleep(lim.backoff(attempt))

    return r


def _ask_once(system: str, user: str, *, cycle_id: str = "",
              base_url: str | None = None, api_key: str | None = None,
              model: str | None = None) -> LLMReply:
    s = settings()
    base_url = base_url or s.practitioner_base_url
    api_key = api_key or s.llm_key
    model = model or s.practitioner_model
    if not s.llm_enabled:
        return LLMReply(False, error="llm disabled (no key, or SAADHAK_LLM=mock)")
    if BUDGET.exhausted:
        return LLMReply(False, error=f"budget ${s.saadhak_llm_budget_usd:.2f} exhausted")

    body = {
        "model": model,
        "max_tokens": s.practitioner_max_tokens,
        "reasoning_effort": s.practitioner_reasoning_effort,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    t0 = time.time()
    try:
        r = httpx.post(f"{base_url}/chat/completions",
                       headers={"Authorization": f"Bearer {api_key}"},
                       json=body, timeout=s.practitioner_timeout_s)
        ms = int((time.time() - t0) * 1000)
        d = r.json()
        if "error" in d:
            reply = LLMReply(False, error=str(d["error"])[:300], latency_ms=ms,
                             retry_after=parse_retry_after(r.headers))
        else:
            content = (d["choices"][0]["message"].get("content") or "").strip()
            u = d.get("usage", {})
            reply = LLMReply(
                ok=bool(content), content=content, latency_ms=ms,
                model=d.get("model", model),
                prompt_tokens=u.get("prompt_tokens", 0),
                completion_tokens=u.get("completion_tokens", 0),
                reasoning_tokens=(u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
            )
            if not content:
                reply.error = "empty content (reasoning consumed the token budget)"
            else:
                reply.parsed = extract_json(content)
                if reply.parsed is None:
                    reply.ok = False
                    truncated = reply.completion_tokens >= s.practitioner_max_tokens - 5
                    reply.error = ("answer truncated by max_tokens" if truncated
                                   else "content was not JSON")
    except Exception as e:
        reply = LLMReply(False, error=f"{type(e).__name__}: {e}",
                         latency_ms=int((time.time() - t0) * 1000))

    BUDGET.add(reply)
    journal.append("llm_call", {
        "cycle_id": cycle_id, "model": model, "ok": reply.ok,
        "error": reply.error, "usage": reply.usage, "latency_ms": reply.latency_ms,
        "budget_spent_usd": round(BUDGET.spent_usd, 6), "calls": BUDGET.calls,
        "limiters": all_status()})
    return reply
