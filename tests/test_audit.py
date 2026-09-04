"""A standing check for the failure that recurred three times.

A hand-picked threshold that duplicates a measured mechanism will refuse things
the measurement approves. Each instance so far was found by a person asking a
question. This makes the detection automatic.
"""
import pytest

from saadhak.engine import audit as A
from saadhak.engine.audit import Audit, GateStat


def test_gate_kinds_are_classified():
    """Every gate must be knowingly environmental, risk appetite, measured, or a
    threshold. An unclassified gate is one nobody has thought about."""
    all_gates = set(range(1, 18))
    classified = A.ENVIRONMENTAL | A.RISK_APPETITE | {A.MEASURED}
    thresholds = all_gates - classified
    assert thresholds, "there must be thresholds to audit"
    assert not (A.ENVIRONMENTAL & A.RISK_APPETITE), "a gate cannot be both"
    assert A.MEASURED not in A.ENVIRONMENTAL | A.RISK_APPETITE


def test_a_threshold_overruling_the_measurement_is_flagged():
    st = GateStat(7, "liquidity", refusals=5, refused_while_measured_passed=5,
                  best_score_refused=0.0152)
    assert "OVERRULES" in st.verdict
    au = Audit(considered=36, stats={7: st})
    assert au.suspects == [st]


def test_a_threshold_that_never_fires_is_flagged_as_untested():
    st = GateStat(14, "limit_only", refusals=0)
    assert "untested" in st.verdict
    assert Audit(stats={14: st}).untested == [st]


def test_risk_appetite_gates_are_not_suspects():
    """Refusing is their job; they are chosen, not measured."""
    st = GateStat(4, "max_loss", refusals=10, refused_while_measured_passed=10)
    assert st.kind == "risk appetite"
    assert Audit(stats={4: st}).suspects == []


@pytest.mark.slow
def test_no_threshold_overrules_the_measurement_on_the_live_surface():
    """The regression test for the whole class of bug. Runs against live data."""
    au = A.run(["SPY", "QQQ", "IWM"], per_symbol=8)
    assert au.considered > 0, "audit found no structures to evaluate"
    assert not au.suspects, "\n".join(
        f"gate {s.n:02d} {s.name} refused {s.refused_while_measured_passed} "
        f"structures gate 08 approved; e.g. {s.examples[:1]}" for s in au.suspects)
