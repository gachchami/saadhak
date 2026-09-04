"""Black-Scholes greeks. Alpaca omits greeks on illiquid far-OTM contracts, so we
compute our own from the quoted mid and an implied vol solved from the chain."""
from __future__ import annotations

import math

SQRT2PI = math.sqrt(2.0 * math.pi)


def _n_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT2PI


def _n_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def d1_d2(s: float, k: float, t: float, r: float, sigma: float) -> tuple[float, float]:
    if t <= 0 or sigma <= 0 or s <= 0 or k <= 0:
        raise ValueError("bad inputs for d1/d2")
    v = sigma * math.sqrt(t)
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / v
    return d1, d1 - v


def price(s: float, k: float, t: float, r: float, sigma: float, kind: str) -> float:
    """European price. Close enough for American index options with no dividend."""
    if t <= 0:
        return max(0.0, (s - k) if kind == "call" else (k - s))
    d1, d2 = d1_d2(s, k, t, r, sigma)
    disc = math.exp(-r * t)
    if kind == "call":
        return s * _n_cdf(d1) - k * disc * _n_cdf(d2)
    return k * disc * _n_cdf(-d2) - s * _n_cdf(-d1)


def greeks(s: float, k: float, t: float, r: float, sigma: float, kind: str) -> dict[str, float]:
    if t <= 0 or sigma <= 0:
        intrinsic_side = (s > k) if kind == "call" else (k > s)
        return {
            "delta": (1.0 if kind == "call" else -1.0) if intrinsic_side else 0.0,
            "gamma": 0.0, "theta": 0.0, "vega": 0.0,
        }
    d1, d2 = d1_d2(s, k, t, r, sigma)
    disc = math.exp(-r * t)
    gamma = _n_pdf(d1) / (s * sigma * math.sqrt(t))
    vega = s * _n_pdf(d1) * math.sqrt(t) / 100.0
    if kind == "call":
        delta = _n_cdf(d1)
        theta = (-s * _n_pdf(d1) * sigma / (2 * math.sqrt(t))
                 - r * k * disc * _n_cdf(d2)) / 365.0
    else:
        delta = _n_cdf(d1) - 1.0
        theta = (-s * _n_pdf(d1) * sigma / (2 * math.sqrt(t))
                 + r * k * disc * _n_cdf(-d2)) / 365.0
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}


def implied_vol(target: float, s: float, k: float, t: float, r: float, kind: str) -> float | None:
    """Bisection on sigma. Robust where Newton diverges on far-OTM contracts."""
    if target <= 0 or t <= 0:
        return None
    lo, hi = 1e-4, 5.0
    if price(s, k, t, r, hi, kind) < target:
        return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if price(s, k, t, r, mid, kind) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-6:
            break
    return 0.5 * (lo + hi)
