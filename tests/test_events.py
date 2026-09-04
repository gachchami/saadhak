from datetime import UTC, date, datetime

from saadhak.engine import events


def test_index_etfs_are_exempt():
    for sym in ("SPY", "QQQ", "IWM"):
        assert not events.earnings_soon(sym, date.today()).has_event


def test_earnings_headlines_are_detected(monkeypatch):
    today = datetime.now(UTC).date().isoformat()
    monkeypatch.setattr(events, "news", lambda *a, **k: [
        {"headline": "Top Wall Street Forecasters Revamp Broadcom Expectations Ahead Of Q3 Earnings",
         "created_at": today}])
    e = events.earnings_soon("AVGO", date.today())
    assert e.has_event and e.kind == "earnings"
    assert "expectancy model" in e.reason


def test_unrelated_headlines_do_not_trigger(monkeypatch):
    today = datetime.now(UTC).date().isoformat()
    monkeypatch.setattr(events, "news", lambda *a, **k: [
        {"headline": "Broadcom Is Top Pick For AI's Next Big Shift: Analyst", "created_at": today}])
    assert not events.earnings_soon("AVGO", date.today()).has_event


def test_stale_headlines_are_ignored(monkeypatch):
    monkeypatch.setattr(events, "news", lambda *a, **k: [
        {"headline": "Broadcom reports earnings", "created_at": "2026-08-01"}])
    assert not events.earnings_soon("AVGO", date.today()).has_event


def test_news_failure_does_not_block_trading(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("data down")
    monkeypatch.setattr(events, "news", boom)
    e = events.earnings_soon("AVGO", date.today())
    assert not e.has_event and "unavailable" in e.reason


# --- pending vs already reported -------------------------------------------

def _news(monkeypatch, *headlines):
    today = datetime.now(UTC).date().isoformat()
    monkeypatch.setattr(events, "news", lambda *a, **k: [
        {"headline": h, "created_at": today} for h in headlines])


def test_a_pending_release_still_blocks(monkeypatch):
    _news(monkeypatch, "Top Wall Street Forecasters Revamp Broadcom Expectations Ahead Of Q3 Earnings")
    e = events.earnings_soon("AVGO", date.today())
    assert e.has_event and not e.reported
    assert "within the holding window" in e.reason


def test_published_numbers_clear_the_guard(monkeypatch):
    """The gap is the risk. Once results are out it has happened, and refusing
    afterwards blocks a risk that no longer exists."""
    _news(monkeypatch, "Broadcom Q3 Adj. EPS $3.32 Beats $3.24 Estimate, Sales $29.591B Beat Estimate")
    e = events.earnings_soon("AVGO", date.today())
    assert not e.has_event and e.reported
    assert "behind us" in e.reason


def test_guidance_changes_count_as_reported(monkeypatch):
    _news(monkeypatch, "Hewlett Packard Raises FY2026 Adj EPS Guidance from $3.35-$3.45 to $3.75-$3.85")
    e = events.earnings_soon("HPE", date.today())
    assert not e.has_event and e.reported


def test_results_win_over_a_preview_from_the_same_window(monkeypatch):
    """Both appear on the day: the preview in the morning, the numbers at night."""
    _news(monkeypatch,
          "HPE Earnings Prediction Market Preview: Will Antonio Neri Say 'Self Driving' Again?",
          "Hewlett Packard Enterprise Shares Slide Lower Despite Strong Q3, Raised Guidance")
    e = events.earnings_soon("HPE", date.today())
    assert not e.has_event and e.reported


def test_an_ambiguous_mention_fails_closed(monkeypatch):
    """Unsure means refuse: headlines cannot prove an event is absent."""
    _news(monkeypatch, "Broadcom set to report earnings")
    e = events.earnings_soon("AVGO", date.today())
    assert e.has_event and not e.reported
