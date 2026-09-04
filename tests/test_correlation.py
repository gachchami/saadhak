"""SPY and QQQ correlate at 0.91. Held together they are one position, not two."""
from saadhak.engine import correlation as C


def test_correlated_names_are_treated_as_one_position(monkeypatch):
    monkeypatch.setattr(C, "correlation", lambda a, b: 0.91)
    c = C.check("QQQ", ["SPY"])
    assert c.blocked and "same position" in c.reason
    assert "SPY (0.91)" in c.correlated_with[0]


def test_an_uncorrelated_name_is_allowed(monkeypatch):
    monkeypatch.setattr(C, "correlation", lambda a, b: 0.12)
    assert not C.check("GLD", ["SPY"]).blocked


def test_an_empty_book_never_blocks(monkeypatch):
    assert not C.check("SPY", []).blocked


def test_unmeasurable_correlation_does_not_block(monkeypatch):
    """Absence of data is not evidence of correlation."""
    monkeypatch.setattr(C, "correlation", lambda a, b: None)
    assert not C.check("SPY", ["XYZ"]).blocked


def test_a_symbol_is_perfectly_correlated_with_itself():
    assert C.correlation("SPY", "SPY") == 1.0


def test_correlation_is_measured_not_listed(monkeypatch):
    """A pair that decouples stops being penalised without anyone editing a list."""
    seen = {}
    monkeypatch.setattr(C, "_closes", lambda s, sessions=60: seen.setdefault(s, [
        100 + i + (3 if s == "B" else 0) * (i % 2) for i in range(40)]))
    C._CACHE.clear()
    r = C.correlation("A", "B")
    assert r is not None and "A" in seen and "B" in seen
    C._CACHE.clear()
