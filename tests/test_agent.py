from saadhak.agent import AgentState, due_window


def test_entry_windows_are_recognised_with_tolerance():
    assert due_window(35) == 35        # 10:05 ET
    assert due_window(44) == 35        # still inside the window
    assert due_window(50) is None      # between windows
    assert due_window(120) == 120      # 11:30 ET
    assert due_window(240) == 240      # 13:30 ET
    assert due_window(None) is None    # market closed


def test_each_window_is_attempted_once_per_symbol_per_day():
    s = AgentState()
    k = s.key("SPY", 35)
    assert k not in s.entries_attempted
    s.entries_attempted.add(k)
    assert s.key("SPY", 35) in s.entries_attempted     # same window, blocked
    assert s.key("SPY", 120) not in s.entries_attempted  # later window, allowed
    assert s.key("QQQ", 35) not in s.entries_attempted   # other symbol, allowed


"""Every live entry must be walked toward a fill.

The walk existed as a function for a week and was never called from anywhere,
so five orders in one session were posted at the mid and cancelled unfilled.
A test on `walk_limit` alone would not have caught that: the defect was the
wiring. This asserts the entry path uses it.
"""
import saadhak.agent as agent_mod
from saadhak.engine.structures import Structure


class _Decision:
    accepted = True
    reason = ""
    cycle_id = "c1"

    def __init__(self, structure: Structure):
        self.structure = structure


def _wire(monkeypatch, condor, *, dry_run_result):
    calls = {"submit": 0, "walk": 0}

    def fake_submit(structure, *, dry_run, cycle_id="", **kw):
        calls["submit"] += 1
        return dry_run_result

    def fake_walk(structure, result, **kw):
        calls["walk"] += 1
        return result

    monkeypatch.setattr(agent_mod, "decide", lambda symbol: _Decision(condor))
    monkeypatch.setattr(agent_mod, "submit", fake_submit)
    monkeypatch.setattr(agent_mod, "walk_limit", fake_walk)
    monkeypatch.setattr(agent_mod.journal, "append", lambda *a, **k: None)
    return calls


def test_a_live_entry_is_walked_toward_a_fill(monkeypatch, condor):
    from saadhak.broker.orders import OrderResult
    live = OrderResult(True, False, {}, {"id": "o1", "status": "new"})
    calls = _wire(monkeypatch, condor, dry_run_result=live)
    agent_mod.try_entry("SPY", 0, AgentState(), dry_run=False)
    assert calls["submit"] == 1
    assert calls["walk"] == 1, "the entry was posted and never walked"


def test_a_dry_run_entry_is_not_walked(monkeypatch, condor):
    from saadhak.broker.orders import OrderResult
    dry = OrderResult(False, True, {})
    calls = _wire(monkeypatch, condor, dry_run_result=dry)
    agent_mod.try_entry("SPY", 0, AgentState(), dry_run=True)
    assert calls["submit"] == 1
    assert calls["walk"] == 0, "a dry run must not touch the broker"
