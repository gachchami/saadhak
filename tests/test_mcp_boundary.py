"""The practitioner must not be able to trade. This is enforced by which tools
are loaded into its MCP session, not by instructions in a prompt."""
import pytest

from saadhak.practitioner import mcp_client as M


def test_trading_toolset_is_not_requested():
    assert "trading" not in M.RESEARCH_TOOLSETS
    assert "account" not in M.RESEARCH_TOOLSETS   # carries update_account_config


def test_server_is_pinned_to_paper():
    env = M.server_params().env
    assert env["ALPACA_PAPER_TRADE"] == "true"
    assert env["ALPACA_TOOLSETS"] == M.RESEARCH_TOOLSETS


@pytest.mark.parametrize("name", [
    "place_option_order", "place_stock_order", "cancel_all_orders",
    "close_position", "close_all_positions", "replace_order_by_id",
    "exercise_options_position", "update_account_config",
])
def test_mutating_tool_names_are_refused_by_the_client(name):
    """Belt and braces: even if a future toolset exposed one, the client refuses."""
    assert any(name.startswith(p) for p in M.FORBIDDEN), name


@pytest.mark.slow
def test_live_server_exposes_no_mutating_tools():
    """Starts the real MCP server. Skipped unless run with --runslow."""
    v = M.verify_no_trading_tools()
    assert v["safe"], v["trading_tools_exposed"]
    assert v["tool_count"] > 20
