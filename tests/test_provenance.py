"""Every decision must say what its numbers rest on."""
from saadhak.broker.provenance import FEED_QUALITY, Provenance, capture


def test_the_free_tier_is_named_honestly():
    assert "not consolidated NBBO" in FEED_QUALITY["iex"]
    assert "OPRA agreement not signed" in FEED_QUALITY["indicative"]


def test_stale_quotes_mark_the_inputs_degraded():
    fresh = Provenance("iex", "indicative", [5.0, 12.0], market_open=True)
    stale = Provenance("iex", "indicative", [5.0, 900.0], market_open=True)
    assert not fresh.degraded
    assert stale.degraded


def test_a_closed_market_is_always_degraded():
    """Quotes after the close are terminal prices, not a live market. AVGO moved
    8% between our last visible print and the truth."""
    p = Provenance("iex", "indicative", [2.0], market_open=False)
    assert p.degraded and "terminal" in p.note


def test_provenance_serialises_for_the_journal():
    d = Provenance("iex", "indicative", [3.0], market_open=True).to_dict()
    assert set(d) >= {"stock_feed", "option_feed", "worst_quote_age_s",
                      "market_open", "degraded", "note"}


def test_capture_works_with_no_contracts():
    p = capture([], market_open=True)
    assert p.worst_quote_age_s == 0.0 and p.stock_feed
