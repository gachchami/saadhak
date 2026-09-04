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
