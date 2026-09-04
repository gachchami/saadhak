"""The practitioner may only ever reduce what the desk does."""
from saadhak.practitioner.review import Verdict


def test_a_veto_without_a_reason_is_not_a_veto():
    """Enforced in review(); a bare 'veto' string cannot stop a gated trade."""
    v = Verdict(consulted=True, veto=True, veto_reason="")
    if v.veto and not v.veto_reason.strip():
        v.veto = False
    assert not v.veto


def test_verdict_carries_no_sizing_or_strike_authority():
    """The dataclass has no field through which a model could alter the trade."""
    fields = set(Verdict.__dataclass_fields__)
    forbidden = {"qty", "size", "strike", "strikes", "width", "limit_price",
                 "symbol", "legs", "contracts", "multiplier"}
    assert not (fields & forbidden), fields & forbidden


def test_an_unconsulted_practitioner_does_not_block_trading():
    v = Verdict(consulted=False, error="llm disabled")
    assert not v.veto
    assert "not consulted" in v.summary


def test_a_failed_consultation_is_not_agreement(monkeypatch):
    """Two of three live calls failed on token exhaustion or timeout. A silent
    'agree' would let an unreviewed trade look reviewed."""
    from saadhak.practitioner import review as R

    monkeypatch.setattr(R, "_research", lambda s: ("", []))
    monkeypatch.setattr(R.settings(), "__class__", R.settings().__class__)
    recorded = {}
    monkeypatch.setattr(R.journal, "append", lambda t, d: recorded.update(d))
    monkeypatch.setattr(R, "ask_json", lambda *a, **k: type(
        "R", (), {"ok": False, "parsed": None, "error": "timeout",
                  "model": "m", "usage": {}, "latency_ms": 1})())

    class Structure:
        underlying = "SPY"
        def describe(self): return "SPY condor"
        legs = []
        short_strikes = []
        net_credit = 0.15
        max_loss_per_unit = 85
        max_loss = 850
        expiry = "2026-09-04"

    v = R.review(Structure(), 760.0, 100_000, 0.85, cycle_id="t")
    assert not v.consulted and not v.veto
    assert recorded.get("verdict") == "unavailable"


def test_the_review_no_longer_asks_for_a_self_chosen_range():
    """That forecast duplicated the study loop and was the gameable kind."""
    from saadhak.practitioner.review import SYSTEM
    assert "micro_forecast" not in SYSTEM
    assert "p_success" in SYSTEM
